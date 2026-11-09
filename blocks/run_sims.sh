#!/bin/bash
# Chay trong VM tu thu muc repo (qua tools/vmjob.py). Mo phong KSA8 va ALU_CORE.
#   python tools/vmjob.py --label A_sims -c "CORNERS='NN SS FF' bash blocks/run_sims.sh"
# Ket qua: out/<TOP>_<CORNER>/tran.tran (psfascii), log out/<TOP>_<CORNER>.log
CORNERS=${CORNERS:-NN}
TOPS=${TOPS:-"KSA8:ALU_ADD ALU_CORE:ALU_CORE"}
mkdir -p out
rc=0
for c in $CORNERS; do
  for tb in $TOPS; do
    top=${tb%%:*}; dir=${tb##*:}
    timeout 1700 spectre blocks/$dir/tb/tb_${top}_$c.scs -format psfascii -raw out/${top}_$c \
      +log out/${top}_$c.log < /dev/null > /dev/null 2>&1
    r=$?
    echo "== ${top}_$c spectre exit=$r"
    grep -iE "^\s*(error|warning)|completes with" out/${top}_$c.log | sort | uniq -c | head -20
    [ $r -ne 0 ] && rc=1
  done
done
exit $rc
