# Scaled-models-for-NuSMV
This repository contains the Python code used to scale the models of the following 3 problems:
1. Pipelines protocol
2. Cache coherence protocol
3. Master bus protocol

Original version of the problems sources from: <https://nusmv.fbk.eu/examples.html>

In order to run the problems with `NuSMV` and to measure walltime, peak memory, and size of data strcuture (BDD nodes or SAT clauses) we used the following commands:

<h4>CTL/LTL BDD:</h4>

Run with:

``NuSMV -source bdd_cmds.txt <file_name>.smv``

where `bdd_cmds.txt` contains:

```
go
check_ctlspec | check_ltlspec | check_pslspec
print_bdd_stats
quit
```

<h4>LTL BMC:</h4>

Run with:

`NuSMV -bmc -bmc_length 20 -v 2 <file_name>.smv`

<h4>PSL BMC:</h4>

Run with:

`NuSMV -v 2 -source bmc_cmds.txt <file_name>.smv`

where `bmc_cmds.txt` contains:

```
go bmc
check_pslspec_bmc -k 20
quit
```

Wallclock runtime is measured with `Measure-Command {...}`.<br>
For BDD specs, node count is taken from `Peak number of nodes:` from the NuSMV output; memory usage is taken frmo `Memory in use:`;<br>
For BMC specs, clause count is taken from `Length of lst of clauses=`; memory usage is reported by monitoring a process via start-process;
