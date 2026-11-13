#!/bin/bash
# Tang 2..4: mo phong mot hay nhieu testbench bang Spectre roi kiem tra ket qua (dung/sai, tre, nang luong).
#   bash scripts/run_sim.sh ALU_8bit/tb/tb_ALU_TOPK_NN.scs
#   bash scripts/run_sim.sh ALU_8bit/tb/tb_*_NN.scs
#   APS=1 bash scripts/run_sim.sh ALU_32bit/tb/tb_MUL32_p*_NN.scs     # Spectre APS (nhieu luong) cho khoi 32 bit
#   bash scripts/run_sim.sh ALU_8bit/layout/rcx/tb_ALU_TOPK_post_NN.scs   # sau layout
# Ket qua: out/<ten testbench>/tran.tran (psfascii), out/<ten testbench>.log. Ma thoat 0 khi moi testbench PASS.
cd "$(dirname "$0")/.." || exit 1
mkdir -p out
rc=0
for tb in "$@"; do
  n=$(basename "$tb" .scs)
  echo "== $n"
  [ -f "$tb" ] || { echo "khong co file $tb"; rc=1; continue; }
  timeout ${TMO:-7200} spectre ${APS:+ +aps} "$tb" -format psfascii -raw "out/$n" +log "out/$n.log" < /dev/null > /dev/null 2>&1
  r=$?
  grep "completes with" "out/$n.log" | sed 's/^ *//'
  if [ $r -ne 0 ]; then
    echo "Spectre loi (ma $r), xem out/$n.log"; grep -i -A3 "^ *error" "out/$n.log" | head -12; rc=1; continue
  fi
  # bang gia tri mong doi nam canh than testbench (dong include cuoi cung), duoi .exp
  body=$(grep '^include "' "$tb" | tail -1 | cut -d'"' -f2)
  exp=$(dirname "$tb")/${body%.scs}.exp
  if [ -f "$exp" ]; then
    awk -f scripts/check.awk "$exp" "out/$n/tran.tran" || rc=1
  else
    awk -f scripts/final_value.awk "out/$n/tran.tran"
  fi
done
exit $rc
