#!/bin/bash
# Ve schematic + symbol trong Virtuoso (thu muc du an ~/ALU_PROJ) tu cac file SKILL sch_*.il.
#   bash virtuoso/run_schematic.sh                         # tang 1 (18 cell) roi ALU 8 bit (tang 2..4)
#   bash virtuoso/run_schematic.sh sch_ALU_32bit.il        # ALU 32 bit (can da ve tang 1 va ALU 8 bit truoc)
# Thu vien tao ra: ALU_CELLS_A/B/C/D/X (cell); ALU_ADD, ALU_CORE, ALU_MUL, ALU_DIV, ALU_TOP (8 bit);
# ALU_32BIT (32 bit). Log: out/sch/<ten>.log; dong SB_SUMMARY errors=0 la thanh cong.
cd "$(dirname "$0")/.." || exit 1
W=$PWD
P=${ALU_PROJ:-$HOME/ALU_PROJ}
mkdir -p "$W/out/sch"
bash virtuoso/setup_alu_proj.sh > "$W/out/sch/setup.log" 2>&1 || { cat "$W/out/sch/setup.log"; exit 1; }
cd "$P" || exit 1
fail=0
for g in ${@:-sch_tang1_cell.il sch_ALU_8bit.il}; do
  log=$W/out/sch/${g%.il}.log
  SB_DIR=$W/virtuoso timeout ${TMO:-3600} virtuoso -nograph -restore "$W/virtuoso/$g" < /dev/null > "$log" 2>&1
  echo "$g: virtuoso rc=$?  $(grep -c '^SB_CELL' "$log") cell  $(grep '^SB_SUMMARY' "$log")"
  grep -E '^SB_ERROR|^\*Error\*' "$log" | head -20
  grep -q '^SB_SUMMARY.*errors=0' "$log" || fail=1
done
exit $fail
