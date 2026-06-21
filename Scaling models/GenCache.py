
#!/usr/bin/env python3
"""
Generate a scaled NuSMV cache protocol model with n pipes,
where n is an input from the user
"""

def gen_cache_device():
    smv= ["MODULE cache-device\n\n"
          "VAR \n state : {invalid, shared, owned}; \n\n"
          "DEFINE \n  readable := ((state = shared) | (state = owned)) & !waiting; \n"
          "  writable := (state = owned) & !waiting; \n\n"
          "ASSIGN \n"
          "  init(state) := invalid; \n"
          "  next(state) :=\n"
          "    case \n"
          "      abort : state;\n"
          "      master :\n"
          "        case \n"
          "          CMD = read-shared        : shared;\n"
          "          CMD = read-owned         : owned;\n"
          "          CMD = write-invalid      : invalid;\n"
          "          CMD = write-resp-invalid : invalid;\n"
          "          CMD = write-shared       : shared;\n"
          "          CMD = write-resp-shared  : shared;\n"
          "          TRUE : state;\n"
          "        esac;\n"
          "      !master & state = shared & (CMD = read-owned | CMD = invalidate) : invalid;\n"
          "      state = shared : {shared, invalid};\n"
          "      TRUE : state;\n"
          "    esac;\n\n"
          "DEFINE \n  reply-owned := !master & state = owned;\n\n"
          "VAR \n  snoop : {invalid,owned,shared};\n\n"
          "ASSIGN \n"
          "  init(snoop) := invalid;\n"
          "  next(snoop) :=\n"
          "    case\n"
          "      abort : snoop;\n"
          "      !master & state = owned & CMD = read-shared : shared;\n"
          "      !master & state = owned & CMD = read-shared : owned;\n"
          "      master & CMD = write-resp-invalid : invalid;\n"
          "      master & CMD = write-resp-shared : invalid;\n"
          "      TRUE : snoop;\n"
          "    esac;\n\n"]
    return smv

def gen_bus_device():
    smv= ["MODULE bus-device \n\n"
          "VAR \n"
          "  master : boolean;\n"
          "  cmd: {idle, read-shared, read-owned, write-invalid, write-shared, write-resp-invalid, write-resp-shared, invalidate, response};\n"
          "  waiting : boolean;\n"
          "  reply-stall : boolean;\n\n"
          "ASSIGN\n"
          "  init(waiting) := FALSE;\n"
          "  next(waiting) :=\n"
          "    case\n"
          "      abort : waiting;\n"
          "      master & CMD = read-shared         :  TRUE;\n"
          "      master & CMD = read-owned          :  TRUE;\n"
          "      !master & CMD = response           : FALSE;\n"
          "      !master & CMD = write-resp-invalid : FALSE;\n"
          "      !master & CMD = write-resp-shared  : FALSE;\n"
          "      TRUE : waiting;\n"
          "    esac;\n\n"
          "DEFINE \n"
          "  reply-waiting := !master & waiting;\n"
          "  abort := REPLY-STALL | ((CMD = read-shared | CMD =read-owned) & REPLY-WAITING);\n\n"]
    return smv

def gen_processor():
    smv= ["MODULE processor(CMD, REPLY-OWNED, REPLY-WAITING, REPLY-STALL) \n"
          "ISA bus-device\n"
          "ISA cache-device\n\n"
          "ASSIGN\n"
          "  cmd :=\n"
          "    case\n"
          "      master & state = invalid : {read-shared, read-owned};\n"
          "      master & state = shared : read-owned;\n"
          "      master & state = owned & snoop = owned : write-resp-invalid;\n"
          "      master & state = owned & snoop = shared : write-resp-shared;\n"
          "      master & state = owned & snoop = invalid : write-invalid;\n"
          "      TRUE : idle\n;"
          "  esac;\n\n"]
    return smv

def gen_memory():
    smv=["MODULE memory(CMD, REPLY-OWNED, REPLY-WAITING, REPLY-STALL)\n"
         "VAR\n"
         "  master : boolean;\n"
         "  cmd : {idle, read-shared, read-owned, write-invalid, write-shared, write-resp-invalid, write-resp-shared, invalidate, response};\n"
         "  busy : boolean;\n"
         "  reply-stall : boolean;\n\n"
         "DEFINE\n"
         "  reply-owned := FALSE;\n"
         "  reply-waiting := FALSE;\n"
         "  abort := REPLY-STALL | (CMD = read-shared | CMD = read-owned) & REPLY-WAITING |"
         "                         (CMD = read-shared | CMD = read-owned) & REPLY-OWNED;\n\n"
         "ASSIGN\n"
         "  init(busy) := FALSE;\n"
         "  next(busy) :=\n"
         "    case\n"
         "      abort : busy;\n"
         "      master & CMD = response : FALSE;\n"
         "      !master & (CMD = read-owned | CMD = read-shared) : TRUE;\n"
         "      TRUE : busy;\n"
         "    esac;\n"
         "  cmd :=\n"
         "    case\n"
         "      master & busy : {response, idle};"
         "      TRUE : idle;\n"
         "    esac;\n"
         "  reply-stall :=\n"
         "    case\n"
         "      busy & (CMD = read-shared | CMD = read-owned "
         "| CMD = write-invalid | CMD = write-shared | CMD = write-resp-invalid | CMD = write-resp-shared) : TRUE;\n"
         "      TRUE : {FALSE, TRUE};\n"
         "     esac;\n"]
    return smv

def gen_main(n):
    smv = ["MODULE main\n"
           "VAR\n"
           "  CMD : {idle, read-shared, read-owned, write-invalid, write-shared, write-resp-invalid, write-resp-shared, invalidate, response};\n"]
    for i in range (0, n):
        smv.append(f"p{i} : processor(CMD, REPLY-OWNED, REPLY-WAITING, REPLY-STALL);\n")
    smv.append("m : memory(CMD,REPLY-OWNED, REPLY-WAITING, REPLY-STALL);\n\n")

    smv.append("DEFINE \n"
               "REPLY-OWNED := ")
    for i in range (0, n-1):
        smv.append(f"p{i}.reply-owned | ")
    smv.append(f"p{n-1}.reply-owned;\n")

    smv.append("REPLY-WAITING := ")
    for i in range (0,n-1):
        smv.append(f"p{i}.reply-waiting | ")
    smv.append(f"p{n-1}.reply-waiting;\n")

    smv.append("REPLY-STALL := ")
    for i in range(0, n):
        smv.append(f"p{i}.reply-stall | ")
    smv.append("m.reply-stall;\n\n")

    smv.append("ASSIGN\n"
               "  CMD := \n"
               "    case\n");
    for i in range (0, n):
        for j in range (0, n):
            if i!=j:
                smv.append(f"      p{j}.cmd = idle &")
        smv.append( f"      m.cmd = idle : p{i}.cmd;\n")
    for i in range (0, n-1):
        smv.append(f"      p{i}.cmd = idle &")
    smv.append(f"      p{n-1}.cmd = idle : m.cmd;\n")

    smv.append("      TRUE : {idle, read-shared, read-owned, write-invalid, write-shared, write-resp-invalid, write-resp-shared, invalidate, response};\n")
    smv.append("    esac;\n\n")

    smv.append("ASSIGN\n")
    smv.append("  p0.master := {FALSE, TRUE};\n")
    for i in range (1, n):
        smv.append(f"  p{i}.master :=\n"
                   "    case \n")
        for j in range(0, i-1):
            smv.append(f"      p{j}.master |")
        smv.append(f"    p{i-1}.master : FALSE;\n")
        smv.append("      TRUE : {FALSE, TRUE};\n"
                   "    esac;\n")
    smv.append("  m.master := \n"
               "    case \n")
    for i in range (0,n-1):
        smv.append(f"       p{i}.master | ")
    smv.append(f"p{n-1}.master : FALSE;\n")
    smv.append("      TRUE : {FALSE, TRUE};\n"
               "    esac;\n\n")

    return smv

    #output = "\n".join(parts)
def gen_spec():
    smv=["PSLSPEC always !(p0.writable & p1.writable);"]
    return smv

if __name__ == "__main__":

    n = int(input("Number of processes to scale: "))
    outfile = f"{n}"
    smv= [gen_cache_device(), gen_bus_device(), gen_processor(), gen_memory(), gen_main(n), gen_spec()]
    if outfile:
        with open(outfile, "w") as f:
            f.write("".join("".join(part) for part in smv))
        print(f"Successfully wrote heavy-utilization benchmark model into {outfile} ({n} cache).")
    else:
        print(smv)
