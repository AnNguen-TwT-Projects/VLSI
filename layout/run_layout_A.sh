#!/bin/bash
# In the VM: layout of ALU_CELLS_A -> Assura DRC + LVS per cell -> GDS.
#   python layout/scs2cdl.py                                   (Windows, LVS netlists)
#   python tools/vmjob.py --label layA -c "bash layout/run_layout_A.sh"          (all steps)
#   python tools/vmjob.py --label layA -c "bash layout/run_layout_A.sh drc INV_X1"
# Steps: gen drc lvs gds (default: all). Cells: default all 9.
# Results: out/layout/gen.log, out/assura/<CELL>/{drc,lvs}/..., out/gds/<LIB>.gds
# Cell B/C/D (layout/gen_layout_cells.py), cell viet LIB/CELL:
#   GEN=layout/gen_layout_BCD.il GDSLIBS="ALU_STUB_B ALU_CELLS_B ALU_CELLS_C ALU_CELLS_D" \
#     bash layout/run_layout_A.sh gen drc lvs gds ALU_CELLS_C/FA_X1 ...
cd "$(dirname "$0")/.." || exit 1
W=$PWD
P=${ALU_PROJ:-$HOME/ALU_PROJ}
R=$P/assura_run
STEPS=""; CELLS=""
for a in "$@"; do
  case $a in gen|drc|lvs|gds|rcx) STEPS="$STEPS $a";; *) CELLS="$CELLS $a";; esac
done
[ -z "$STEPS" ] && STEPS="gen drc lvs gds"
GEN=${GEN:-layout/gen_layout_A.il}
GDSLIBS=${GDSLIBS:-ALU_CELLS_A}
[ -z "$CELLS" ] && CELLS="INV_X1 NAND2_X1 NOR2_X1 AOI21_X1 OAI21_X1 BLK_P BLK_N GRY_P GRY_N"
mkdir -p "$W/out/layout" "$W/out/gds"
bash skill/setup_alu_proj.sh > "$W/out/layout/setup.log" 2>&1 || { cat "$W/out/layout/setup.log"; exit 1; }
cd "$P" || exit 1
fail=0

for s in $STEPS; do
case $s in
gen)
  timeout 900 virtuoso -nograph -restore "$W/$GEN" < /dev/null > "$W/out/layout/gen.log" 2>&1
  rc=$?
  grep -E 'LA_|\*Error\*|\*WARNING\*' "$W/out/layout/gen.log" | grep -v extractVerifySubstrate
  echo "gen rc=$rc"; [ $rc -ne 0 ] && fail=1 ;;
drc)
  for lc in $CELLS; do
    c=${lc##*/}; lib=ALU_CELLS_A; [ "$c" != "$lc" ] && lib=${lc%%/*}
    d=$R/$c/drc; o=$W/out/assura/$c/drc
    rm -rf "$d" "$o"; mkdir -p "$d" "$o"
    sed -e "s|@LIB@|$lib|g" -e "s|@CELL@|$c|g" -e "s|@RUN@|$d|g" "$W/layout/assura/drc.rsf" > "$d/run.rsf"
    (cd "$d" && echo "INCLUDE $P/cds.lib" > cds.lib && timeout 600 assura run.rsf > assura.log 2>&1)
    cp "$d"/run.rsf "$d"/assura.log "$d"/*.err "$d"/*.sum "$d"/*.csm "$o"/ 2>/dev/null
    # one line per violated rule in <cell>.err; none = clean
    n=$(grep -c 'Rule No\.' "$d/$c.err" 2>/dev/null)
    if [ -f "$d/$c.err" ] && grep -q -i 'error' "$d/$c.err"; then
      echo "DRC $c: errors in $c.err:"; grep -E '^ *Rule|Error|error' "$d/$c.err" | head -20; fail=1
    else
      echo "DRC $c: $(grep -i -E 'total|error|violation|No DRC' "$d/assura.log" | tail -3 | tr '\n' ' ')"
    fi
    [ -z "$KEEP" ] && rm -rf "$d"   # o VM gan day (Cadence 29/33 GB); bao cao da chep sang out/assura
  done ;;
lvs)
  for lc in $CELLS; do
    c=${lc##*/}; lib=ALU_CELLS_A; [ "$c" != "$lc" ] && lib=${lc%%/*}
    d=$R/$c/lvs; o=$W/out/assura/$c/lvs
    rm -rf "$d" "$o"; mkdir -p "$d" "$o"
    sed -e "s|@LIB@|$lib|g" -e "s|@CELL@|$c|g" -e "s|@RUN@|$d|g" -e "s|@CDL@|$W/layout/assura/cdl/$c.cdl|g" \
        "$W/layout/assura/lvs.rsf" > "$d/run.rsf"
    (cd "$d" && echo "INCLUDE $P/cds.lib" > cds.lib && timeout 600 assura run.rsf > assura.log 2>&1)
    cp "$d"/run.rsf "$d"/assura.log "$d"/*.cls "$d"/*.csm "$d"/*.sum "$o"/ 2>/dev/null
    echo "LVS $c: $(grep -i -E 'match|differ|error' "$d/assura.log" | tail -4 | tr '\n' ' ')"
    [ -z "$KEEP" ] && rm -rf "$d"
  done ;;
gds)
  for lib in $GDSLIBS; do
    rm -f "$W/out/gds/$lib.gds"
    timeout 600 strmout -library $lib -strmFile "$W/out/gds/$lib.gds" -view layout       -logFile "$W/out/gds/strmout_$lib.log" > /dev/null 2>&1
    echo "strmout $lib rc=$?"; grep -i -E 'error|warn|summary|cells' "$W/out/gds/strmout_$lib.log" | head
    ls -l "$W/out/gds/$lib.gds" || fail=1
  done ;;
esac
done
exit $fail
