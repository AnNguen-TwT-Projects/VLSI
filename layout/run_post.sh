#!/bin/bash
# Trong VM: Spectre sau layout (netlist RCX tu layout/rcx2scs.py). Moi job 1 testbench (runner cat job > 30 phut).
#   python tools/vmjob.py --label post -c "bash layout/run_post.sh ALU_TOPK_post_NN"
# Bien: SPOPT="+aps" (khoi 32 bit). Ra: out/<TEN>/tran.tran (psfascii), out/<TEN>.log   (TEN = ALU_TOPK_post_NN, DIV8K_p0_post_NN, ...)
cd "$(dirname "$0")/.." || exit 1
mkdir -p out
rc=0
for t in "$@"; do
  timeout 1700 spectre $SPOPT layout/rcx/tb_$t.scs -format psfascii -raw out/$t +log out/$t.log < /dev/null > /dev/null 2>&1
  r=$?; echo "== $t spectre exit=$r"
  grep -iE "^\s*error|completes with" out/$t.log | sort | uniq -c | head
  [ $r -ne 0 ] && rc=1
done
exit $rc
