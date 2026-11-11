#!/bin/bash
# Trong VM: place & route khoi bang Encounter, roi Assura DRC/LVS tren GDS gop.
#   python layout/pnr/prep.py                     (Windows: Verilog, CDL phang, LEF)
#   python tools/vmjob.py --label pnr -c "bash layout/pnr/run_pnr.sh pnr drc lvs DIV8"
# Bien: UTIL (mat do loi, mac dinh 0.7), TOPL (lop route cao nhat, mac dinh 6 = Metal6),
#   PAD (cell duoc chua 2 site, vd "BOOTH_SEL BOOTH_ENC").
# Ra: out/pnr/<BLK>/{<BLK>.gds,<BLK>.def,rpt_*,pnr.log}, out/assura/<BLK>/{drc,lvs}/
cd "$(dirname "$0")/../.." || exit 1
W=$PWD; export W
PDK=/home/buet/cadence/gpdk090_v4.6
STEPS=""; BLKS=""
for a in "$@"; do case $a in pnr|drc|lvs) STEPS="$STEPS $a";; *) BLKS="$BLKS $a";; esac; done
[ -z "$STEPS" ] && STEPS="pnr drc lvs"
[ -z "$BLKS" ] && BLKS="ALU_CORE MUL8 DIV8 ALU_TOP"
fail=0
for b in $BLKS; do
  d=$W/out/pnr/$b; g=$d/$b.gds
  for s in $STEPS; do
  case $s in
  pnr)
    rm -rf "$d"; mkdir -p "$d"
    (cd "$d" && BLK=$b timeout 3000 encounter -nowin -init "$W/layout/pnr/pnr.tcl" -log pnr < /dev/null > pnr.out 2>&1)
    echo "pnr $b rc=$?"
    grep -E 'PNR_|^\*\*ERROR|Total number of DRC violations|Verification Complete|Viols|Found [0-9]+ (problem|violation)' \
      "$d/pnr.out" | sort | uniq -c | head -20
    [ -f "$g" ] || fail=1 ;;
  drc|lvs)
    r=$W/out/assura/$b/$s; rm -rf "$r"; mkdir -p "$r"
    sed -e "s|@GDS@|$g|g" -e "s|@CELL@|$b|g" -e "s|@RUN@|$r|g" -e "s|@CDL@|$W/layout/assura/cdl/${b}_flat.cdl|g" \
        "$W/layout/pnr/$s.rsf" > "$r/run.rsf"
    (cd "$r" && timeout 2400 assura run.rsf > assura.log 2>&1)
    if [ $s = drc ]; then
      echo "DRC $b: $(grep -c 'Rule No\.' "$r/$b.err" 2>/dev/null) luat vi pham"
      grep -E '^Rule No|Real Error Count' "$r/$b.err" 2>/dev/null | paste - - | head -30
    else
      echo "LVS $b: $(grep -i -E 'match|differ' "$r/assura.log" | tail -3 | tr '\n' ' ')"
    fi
    rm -rf "$r"/*.dir "$r"/*.ldb 2>/dev/null ;;   # giu bao cao, bo co so du lieu lon
  esac
  done
done
exit $fail
