#!/usr/bin/env python3
"""
Generate a scaled NuSMV data-driven pipeline model with n pipes,
where n is an input from the user
"""

import math


def get_config(i):
    #base config values scaled by the pipeline's index group
    group_multiplier=((i-1)//3)+1

    #periods scale up (20, 30, 60 -> 40, 60, 120 -> 60, 90, 180...)
    periods_pool=[20*group_multiplier, 30*group_multiplier, 60*group_multiplier]
    period=periods_pool[(i-1)%3]

    if(i-1)%3==0:
        execs =[2,1,2]
    elif(i-1)%3==1:
        execs=[1,2,1]
    else:
        execs=[1,1,1]

    return period, execs


def gen_stage_module(pipeline_idx,stage_idx,exec_time):
    name=f"pipe_{pipeline_idx}_{stage_idx}"
    sym=f"p_{pipeline_idx}_{stage_idx}"
    mod_size=exec_time
    mod_val=mod_size+1

    smv=[
        f"-- Pipeline {pipeline_idx}, stage {stage_idx}. Bound: 0..{mod_size}",
        f"MODULE {name}(timeout, processor_granted)",
        f"VAR",
        f"  state: 0..{mod_size};",
        f"DEFINE",
        f"  start  := state = 0 & timeout;",
        f"  finish := state = {mod_size};",
        f"  request := case",
        f"               state = 0: FALSE;",
        f"               TRUE:      TRUE;",
        f"             esac;",
        f"ASSIGN",
        f"  init(state) := 0;",
        f"  next(state) := case",
        f"                   start:  1;",
        f"                   finish: 0;",
        f"                   !(processor_granted = {sym}): state;",
        f"                   state = 0: 0;",
        f"                   TRUE: (state + 1) mod {mod_val};",
        f"                 esac;",
        ""
    ]
    return "\n".join(smv)


def gen_main(n, configs):
    smv=[]

    #global clock timer
    periods=[configs[i][0] for i in range(1, n+ 1)]
    timer_max=periods[0]
    for p in periods[1:]:
        timer_max=timer_max*p // math.gcd(timer_max,p)

    smv.append("MODULE main")
    smv.append("")
    smv.append(f"VAR")
    smv.append(f"  timer: 0..{timer_max};")
    smv.append("")
    smv.append("ASSIGN")
    smv.append("  init(timer) := 0;")
    smv.append(f"  next(timer) := (timer + 1) mod {timer_max};")
    smv.append("")

    # for timeout
    smv.append("DEFINE")
    unique_periods=sorted(set(periods))
    for p in unique_periods:
        smv.append(f"  timeout{p} := timer mod {p} = 0;")
    smv.append("")

    #decl of pipeline instance
    smv.append("VAR")
    smv.append("-- Instantiated data-driven pipesmv:")
    for i in range(1, n+1):
        period, _ = configs[i]
        smv.append(f"  P_{i}_1: pipe_{i}_1(timeout{period}, processor_granted);")
        smv.append(f"  P_{i}_2: pipe_{i}_2(P_{i}_1.finish, processor_granted);")
        smv.append(f"  P_{i}_3: pipe_{i}_3(P_{i}_2.finish, processor_granted);")
    smv.append("")

    #symbol table mapping
    sym_list = ", ".join(
        f"p_{i}_{s}" for i in range(1, n+1) for s in [1,2,3]
    )
    smv.append(f"  aux: {{idle, {sym_list}}};")
    smv.append("")

    #scheduler for rate monotonic
    sorted_pipesmv = sorted(range(1, n + 1), key=lambda idx: configs[idx][0])

    smv.append("DEFINE")
    smv.append("  processor_granted := case")
    for i in sorted_pipesmv:
        smv.append(f"                         P_{i}_{1}.request: p_{i}_{1}; P_{i}_{2}.request: p_{i}_{2}; P_{i}_{3}.request: p_{i}_{3};")
    smv.append("                         TRUE: idle;")
    smv.append("                       esac;")
    smv.append("")

    #error condition block
    error_terms = []
    for i in range(1, n + 1):
        period, _ = configs[i]
        for s in [1, 2, 3]:
            error_terms.append(f"timeout{period} & !(P_{i}_{s}.state = 0)")
    smv.append("  error := " + " |\n           ".join(error_terms) + ";")
    smv.append("")

    #error spec
    smv.append("SPEC AG !error")
    smv.append("")

    return "\n".join(smv)


def generate(n, outfile=None):
    configs = {i: get_config(i) for i in range(1, n+1)}

    parts = [
        f"--Auto-Generated Data-Driven Pipeline Benchmark.\n-- Scale factor: {n} pipesmv.\n--\n"
    ]

    for i in range(1, n+1):
        period, execs = configs[i]
        parts.append(
            f"--Pipeline {i}. Period {period}ms, stages: {execs[0]}ms, {execs[1]}ms, {execs[2]}ms\n")
        for s, exec_time in enumerate(execs, start=1):
            parts.append(gen_stage_module(i, s, exec_time))

    parts.append(gen_main(n, configs))
    output = "\n".join(parts)

    if outfile:
        with open(outfile, "w") as f:
            f.write(output)
        print(f"Successfully wrote heavy-utilization benchmark model into {outfile} ({n} pipesmv).")
    else:
        print(output)


if __name__ == "__main__":

    n = int(input("Number of pipesmv to scale: "))
    outfile = f"{n}"
    generate(n, outfile)
