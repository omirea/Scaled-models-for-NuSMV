"""
Generate a scaled NuSMV bus arbiter model with n masters,
where n is an input from the user
"""


#hierarchy
def plan_groups(n):
    #Split n masters into consecutive pairs
    groups=[]
    i=0
    while i<n:
        if i+1<n:
            groups.append([i, i+1])
        else:
            groups.append([i])
        i+=2
    return groups


#modules
def gen_header():
    return (
        "-- PCI Bus protocol model -- from Sergio Campos (02/95)\n"
        "-- Auto-generated\n\n")


def gen_arb_bank(k, label=None):
    inputs=", ".join([f"req{i}" for i in range(k)])
    last_range=f"0..{k - 1}" if k>1 else "{0}"

    fp_cases="".join([f"                 req{i}: {i};\n" for i in range(k)])

    rr_cases=""
    for last_val in range(k):
        inner="".join(
            [f"                     req{(last_val + o) % k}: {(last_val + o) % k};\n" for o in range(1, k + 1)])
        rr_cases += f"                 last={last_val}:\n                   case\n{inner}                     TRUE : idle;\n                   esac;\n"

    grant_cases="".join([f"                  grant={i}: {i};\n" for i in range(k)])

    smv=[
        f"MODULE arb_bank_{k}in({inputs}, policy, granted, change_now)\n\n"
        f"VAR last: {last_range};\n\n"
        "DEFINE\n"
        "  grant := case\n"
        "             policy=FP:\n"
        "               case\n"
        f"{fp_cases}"
        "                 TRUE : idle;\n"
        "               esac;\n"
        "             policy=RR:\n"
        "               case\n"
        f"{rr_cases}"
        "               esac;\n"
        "           esac;\n\n"
        "ASSIGN\n"
        "  init(last) := 0;\n"
        "  next(last) := case\n"
        "                  !granted | !change_now: last;\n"
        f"{grant_cases}"
        "                  TRUE : last;\n"
        "                esac;\n\n"
    ]
    return "".join(smv)

def gen_arbiter(n, groups):
    num_banks=len(groups)
    req_params=", ".join([f"req{i}" for i in range(n)])
    grant_vals=", ".join([str(i) for i in range(n)]) + ", idle"

    policy_vars="".join([f"    policy{b}: {{FP, RR}};\n" for b in range(num_banks)])
    leaf_banks="".join([
        f"    bank{b}: arb_bank_{len(group)}in("
        f"{', '.join(f'req{i}' for i in group)}, policy{b}, "
        f"(bank_central.grant={b}), change_now);\n"
        for b, group in enumerate(groups)
    ])
    central_reqs=", ".join([f"reqbank{b}" for b in range(num_banks)])
    reqbank_defs="".join([f"  reqbank{b} := !(bank{b}.grant=idle);\n" for b in range(num_banks)])
    central_grants="".join([
        f"                   bank_central.grant={b}:\n"
        "                     case\n"
        + "".join([f"                       bank{b}.grant={li}: {mi};\n"
                   for li, mi in enumerate(group)])
        + f"                       TRUE: {group[0]};\n"
          "                     esac;\n"
        for b, group in enumerate(groups)
    ])
    policy_nexts="".join([f"  next(policy{b}) := policy{b};\n" for b in range(num_banks)])

    smv=[
        f"MODULE arbiter({req_params}, b_frame_switch)\n"
        "VAR\n"
        f"{policy_vars}"
        "    policy_central: {FP, RR};\n\n"
        f"{leaf_banks}"
        f"    bank_central: arb_bank_{num_banks}in({central_reqs}, "
        f"policy_central, TRUE, change_now);\n\n"
        f"    grant: {{{grant_vals}}};\n\n"
        "DEFINE\n"
        f"{reqbank_defs}\n"
        "  change_now := !(!b_frame_switch & grant != idle);\n\n"
        "ASSIGN\n"
        "  init(grant) := idle;\n"
        "  next(grant) := case\n"
        "                   !b_frame_switch & grant != idle: grant;\n"
        "                              -- only change grant when b_frame goes up\n"
        "                              -- except when the bus is idle.\n"
        "                   bank_central.grant=idle: idle;\n"
        f"{central_grants}"
        "                 esac;\n\n"
        f"{policy_nexts}"
        "  next(policy_central) := policy_central;\n\n"
    ]
    return "".join(smv)


def gen_bus_master():
    return """\
MODULE bus_master(id, b_frame_switch, abort, abort_count,
                  b_gnt, b_c_bd, b_frame, b_irdy, b_trdy)
VAR
  req: boolean;
  state: {idle, address, data};
  _count: 0..3;
  c_bd: {IDLE, MEM_READ, MEM_WRITE};
  irdy: boolean;
  trdy: boolean;
  issue_next: boolean;
DEFINE
  ad    := 0;
  bus_idle := !b_frame & !b_irdy;
  start_transaction := b_gnt & bus_idle;
  end_transaction   := (state=data) & (_count=0);
  frame := (state=address) | ((state=data) & (_count > 0));
ASSIGN
  init(req) := FALSE;
  next(req) := case
                 frame & abort: TRUE;
                 !req: case
                         issue_next: TRUE;
                        !issue_next: FALSE;
                       esac;
                 req: case
                        b_gnt:  FALSE;
                        TRUE :      TRUE;
                      esac;
               esac;
  init(state) := idle;
  next(state) := case
                   abort: idle;
                   state=idle:
                     case
                       !start_transaction: idle;
                       TRUE : address;
                     esac;
                   state=address: data;
                   state=data:
                     case
                       _count=0: idle;
                       TRUE :         data;
                     esac;
                 esac;
  init(_count) := 0;
  next(_count) := case
                   abort: 0;
                   start_transaction: { 1,  2,  3};
                   end_transaction: 0;
                   !(state=data): _count;
                   !b_trdy: _count;
                   _count > 0: _count - 1;
                   TRUE : _count;
                 esac;
  init(c_bd) := IDLE;
  next(c_bd) := case
                  abort: IDLE;
                  start_transaction: {MEM_READ, MEM_WRITE};
                  end_transaction: IDLE;
                  TRUE : c_bd;
                esac;
  init(irdy) := FALSE;
  next(irdy) := case
                  abort: FALSE;
                  state=address: TRUE;
                  end_transaction: FALSE;
                  TRUE : irdy;
                esac;
  init(trdy) := FALSE;
  next(trdy) := case
                  abort: FALSE;
                  state != idle: FALSE;
                  !trdy: case
                           b_c_bd=MEM_READ & b_irdy: TRUE;
                           b_c_bd=MEM_WRITE & b_frame: TRUE;
                           TRUE : FALSE;
                         esac;
                  trdy: case
                           b_frame: TRUE;
                           TRUE :     FALSE;
                         esac;
                esac; """


def gen_bus_master_null():
    smv="""\
MODULE bus_master_null(id, b_frame_switch, abort, abort_count,
                       b_gnt, b_c_bd, b_frame, b_irdy, b_trdy)
DEFINE
  c_bd  := IDLE;
  ad    := 0;
  frame := FALSE;
  irdy  := FALSE;
  trdy  := FALSE;
  req   := FALSE;

"""
    return smv;


def gen_main(n, null_masters=None):
    null_masters=set(null_masters or [])

    req_args=", ".join([f"master{i}.req" for i in range(n)])
    masters="".join([
        f"    master{i}: {'bus_master_null' if i in null_masters else 'bus_master'}"
        f"({i}, b_frame_switch, abort, abort_count,\n"
        f"               (arb.grant={i}), b_c_bd, b_frame, b_irdy, b_trdy);\n"
        for i in range(n)
    ])
    b_frame=" | ".join([f"master{i}.frame" for i in range(n)])
    b_irdy=" | ".join([f"master{i}.irdy"  for i in range(n)])
    b_trdy=" | ".join([f"master{i}.trdy"  for i in range(n)])
    c_bd_cases="".join([f"               master{i}.frame: master{i}.c_bd;\n" for i in range(n)])

    smv=[
        "MODULE main\n\nVAR\n"
        f"    arb: arbiter({req_args}, b_frame_switch);\n\n"
        f"{masters}\n"
        "--\n-- Bus signals\n--\n"
        "DEFINE\n"
        f"  b_frame := {b_frame};\n"
        f"  b_irdy  := {b_irdy};\n"
        f"  b_trdy  := {b_trdy};\n"
        "  b_c_bd  := case\n"
        f"{c_bd_cases}"
        "               TRUE :      IDLE;\n"
        "             esac;\n\n"
        "  bus_idle := !b_frame & !b_irdy;\n\n"
        "VAR\n  b_frame_old: boolean;\n"
        "ASSIGN\n"
        "  init(b_frame_old) := FALSE;\n"
        "  next(b_frame_old) := b_frame;\n"
        "DEFINE\n"
        "  b_frame_switch := b_frame & !b_frame_old;\n\n"
        "VAR\n"
        "  abort_count: 0..3;\n"
        "  abort_random: boolean;\n"
        "ASSIGN\n"
        "  init(abort_count) := 0;\n"
        "  next(abort_count) := case\n"
        "                         abort:\n"
        "                           case\n"
        "                             abort_count=3: 3;\n"
        "                             TRUE : abort_count + 1;\n"
        "                           esac;\n"
        "                         TRUE : abort_count;\n"
        "                       esac;\n\n"
        "DEFINE\n"
        "  abort := abort_random & b_frame;\n\n"
        "TRANS (abort_count=0 | abort_count=1)\n"
    ]
    return "".join(smv)

if __name__== "__main__":
    n=int(input("Number of bus masters to scale: "))

    # Mark indices that should be passive (bus_master_null).
    # For n=6 replicating the original: null_masters=[3, 5]
    null_masters_input=input(
        "Null (passive) master indices, comma-separated (or blank for none): "
    ).strip()
    null_masters=(
        [int(x.strip()) for x in null_masters_input.split(",") if x.strip()]
        if null_masters_input else []
    )

    groups=plan_groups(n)
    num_banks=len(groups)

    print(f"\nHierarchy plan:")
    for b, g in enumerate(groups):
        print(f"  bank{b} ({len(g)}-input): masters {g}")
    print(f"  bank_central ({num_banks}-input): leaf banks 0..{num_banks-1}")
    print(f"  Null masters: {null_masters}\n")

    #leaf banks
    leaf_sizes=sorted(set(len(g) for g in groups))

    outfile=f"pci_model_{n}.smv"

    parts=[gen_header()]

    #emit one arb_bank module per unique leaf size
    for k in leaf_sizes:
        parts.append(gen_arb_bank(k))

    #central bank
    if num_banks not in leaf_sizes:
        parts.append(gen_arb_bank(num_banks))

    parts.append(gen_arbiter(n, groups))
    parts.append(gen_bus_master())
    parts.append(gen_bus_master_null())
    parts.append(gen_main(n, null_masters))

    output="".join(parts)

    with open(outfile, "w") as f:
        f.write(output)

    print(f"Wrote {outfile} ({n} masters, {num_banks} leaf banks + 1 central bank).")
