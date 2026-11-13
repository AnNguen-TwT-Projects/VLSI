#!/bin/bash
# Layout cac cell tang 1 trong Virtuoso -> Assura DRC + LVS tung cell -> xuat GDS tung thu vien.
#   bash virtuoso/run_layout_cell.sh                     # moi buoc, 18 cell
#   bash virtuoso/run_layout_cell.sh drc lvs INV_X1 FA_X1    # chi vai buoc / vai cell
# Buoc: gen (ve layout tu layout_cells_A/BCD/P.il) | drc | lvs | gds. Thu muc du an: ~/ALU_PROJ (bien ALU_PROJ).
# Ket qua: out/layout/*.log, out/assura/<CELL>/{drc,lvs}/, out/gds/<THU VIEN>.gds
# (muon P&R dung GDS moi: chep out/gds/*.gds vao pnr/gds_cell/).
cd "$(dirname "$0")/.." || exit 1
W=$PWD
P=${ALU_PROJ:-$HOME/ALU_PROJ}
R=$P/assura_run
ALL="INV_X1 NAND2_X1 NOR2_X1 AOI21_X1 OAI21_X1 BLK_P BLK_N GRY_P GRY_N XOR2_X1 XNOR2_X1 BOOTH_ENC BOOTH_SEL CMP42 FA_X1 HA_X1 INV_X4 CAS_X1"
LIBS="ALU_CELLS_A ALU_CELLS_X ALU_CELLS_B ALU_CELLS_C ALU_CELLS_D ALU_CELLS_P"
lib_of() {
  case $1 in
    XOR2_X1|XNOR2_X1) echo ALU_CELLS_X;; BOOTH_ENC|BOOTH_SEL|CMP42) echo ALU_CELLS_B;;
    FA_X1|HA_X1|INV_X4) echo ALU_CELLS_C;; CAS_X1) echo ALU_CELLS_D;; *) echo ALU_CELLS_A;;
  esac
}
STEPS=""; CELLS=""
for a in "$@"; do
  case $a in gen|drc|lvs|gds) STEPS="$STEPS $a";; *) CELLS="$CELLS $a";; esac
done
[ -z "$STEPS" ] && STEPS="gen drc lvs gds"
[ -z "$CELLS" ] && CELLS=$ALL
mkdir -p "$W/out/layout" "$W/out/gds"
bash virtuoso/setup_alu_proj.sh > "$W/out/layout/setup.log" 2>&1 || { cat "$W/out/layout/setup.log"; exit 1; }
cd "$P" || exit 1
fail=0
for s in $STEPS; do
case $s in
gen)
  for g in layout_cells_A layout_cells_BCD layout_cells_P; do
    timeout 900 virtuoso -nograph -restore "$W/virtuoso/$g.il" < /dev/null > "$W/out/layout/$g.log" 2>&1
    rc=$?
    grep -E 'LA_ERROR|LA_SUMMARY|\*Error\*' "$W/out/layout/$g.log"
    echo "gen $g rc=$rc"; [ $rc -ne 0 ] && fail=1
  done ;;
drc)
  for c in $CELLS; do
    lib=$(lib_of $c); d=$R/$c/drc; o=$W/out/assura/$c/drc
    rm -rf "$d" "$o"; mkdir -p "$d" "$o"
    sed -e "s|@LIB@|$lib|g" -e "s|@CELL@|$c|g" -e "s|@RUN@|$d|g" "$W/virtuoso/drc_cell.rsf" > "$d/run.rsf"
    (cd "$d" && echo "INCLUDE $P/cds.lib" > cds.lib && timeout 600 assura run.rsf > assura.log 2>&1)
    cp "$d"/run.rsf "$d"/assura.log "$d"/*.err "$d"/*.sum "$o"/ 2>/dev/null
    if [ -f "$d/$c.err" ]; then
      n=$(grep -c 'Rule No\.' "$d/$c.err")
      echo "DRC $c: $n luat vi pham"; [ "$n" -ne 0 ] && { grep -E '^Rule No' "$d/$c.err" | head -10; fail=1; }
    else
      echo "DRC $c: Assura khong chay xong, xem $o/assura.log"; fail=1
    fi
    [ -z "$KEEP" ] && rm -rf "$d"     # giu bao cao trong out/assura, bo co so du lieu lon
  done ;;
lvs)
  for c in $CELLS; do
    lib=$(lib_of $c); d=$R/$c/lvs; o=$W/out/assura/$c/lvs
    rm -rf "$d" "$o"; mkdir -p "$d" "$o"
    sed -e "s|@LIB@|$lib|g" -e "s|@CELL@|$c|g" -e "s|@RUN@|$d|g" -e "s|@CDL@|$W/virtuoso/cdl/$c.cdl|g" \
        "$W/virtuoso/lvs_cell.rsf" > "$d/run.rsf"
    (cd "$d" && echo "INCLUDE $P/cds.lib" > cds.lib && timeout 600 assura run.rsf > assura.log 2>&1)
    cp "$d"/run.rsf "$d"/assura.log "$d"/*.cls "$d"/*.csm "$d"/*.sum "$o"/ 2>/dev/null
    m=$(grep -h -i -E 'Schematic and Layout' "$d/assura.log" "$d/$c.csm" 2>/dev/null | tail -1)
    echo "LVS $c: ${m:-khong co ket qua, xem $o/assura.log}"
    echo "$m" | grep -q 'Layout Match' || fail=1
    [ -z "$KEEP" ] && rm -rf "$d"
  done ;;
gds)
  for lib in $LIBS; do
    rm -f "$W/out/gds/$lib.gds"
    timeout 600 strmout -library $lib -strmFile "$W/out/gds/$lib.gds" -view layout \
        -logFile "$W/out/gds/strmout_$lib.log" > /dev/null 2>&1
    echo "strmout $lib rc=$?"
    ls -l "$W/out/gds/$lib.gds" || fail=1
  done ;;
esac
done
exit $fail
