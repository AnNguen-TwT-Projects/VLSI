#!/bin/bash
# In the VM: draw schematics + symbols (ALU_CELLS_A, ALU_STUB_B) in ~/ALU_PROJ from a generated
# SKILL file, then export the libraries as tgz.
#   python tools/scs2skill.py -o skill/gen_cells_A.il ALU_CELLS_A=cells/A ALU_STUB_B=cells/_stub_B
#   python tools/vmjob.py --label gen_cells -c "bash skill/run_cells_A.sh"   [gen file, default gen_cells_A.il]
#   python cells/A/check_cells.py netcmp      (Windows: SB_NET dump in out/sch/gen.log vs cells/*.scs)
# No si netlisting here: `si -batch` hangs in this VM. Connectivity is checked from the SB_NET
# lines (schCheck-extracted nets + CDF w/fw/l of every instance) that sch_build.il prints.
cd "$(dirname "$0")/.." || exit 1
W=$PWD
GEN=$W/skill/${1:-gen_cells_A.il}
OUTD=${OUTD:-$W/out}
OUT=$OUTD/sch
rm -rf "$OUT"; mkdir -p "$OUT" "$OUTD/libs"
bash skill/setup_alu_proj.sh > "$OUT/setup.log" 2>&1 || { cat "$OUT/setup.log"; exit 1; }
P=${ALU_PROJ:-$HOME/ALU_PROJ}
cd "$P" || exit 1
SB_DIR=$W/skill timeout 300 virtuoso -nograph -restore "$GEN" < /dev/null > "$OUT/gen.log" 2>&1
rc=$?
grep -E '^SB_(LIB|CELL|SYMBOL|ERROR|SUMMARY)|^\*Error\*' "$OUT/gen.log" | head -100
echo "virtuoso rc=$rc"
for lib in ALU_CELLS_A ALU_STUB_B; do
  [ -d "$P/$lib" ] && tar czf "$OUTD/libs/$lib.tgz" -C "$P" "$lib"
done
ls -l "$OUTD/libs"
exit $rc
