#!/bin/bash
# Place & route khoi bang Encounter, Assura DRC / LVS / RCX tren GDS cua khoi.
#   bash pnr/run_pnr.sh drc lvs ALU_TOPK              # kiem tra GDS co san (ALU_*/layout/gds)
#   bash pnr/run_pnr.sh pnr drc lvs ALU_CORE          # chay lai P&R roi kiem tra GDS moi (out/pnr)
#   PINL=4 RETRY=3 bash pnr/run_pnr.sh pnr drc lvs MUL32
#   bash pnr/run_pnr.sh rcx ALU_TOPK                  # trich ky sinh -> out/assura/ALU_TOPK/rcx/ALU_TOPK_rcx.sp
# Buoc: pnr | drc | lvs | rcx. Khoi: ALU_CORE MUL8 DIV8K ALU_TOPK (8 bit), CORE32 MUL32 DIV32 ALU32 (32 bit).
# Bien: UTIL (mat do loi, mac dinh 0.7), TOPL (lop di day cao nhat, mac dinh 6), PINL (lop cao nhat cho chan IO),
#   RETRY (so luot detailRoute them), PAD (cell duoc chua 2 site), EXT (rcx: cap | both, mac dinh cap).
# Ra: out/pnr/<KHOI>/{<KHOI>.gds,<KHOI>.def,rpt_*,pnr.out}, out/assura/<KHOI>/{drc,lvs,rcx}/
cd "$(dirname "$0")/.." || exit 1
W=$PWD; export W
STEPS=""; BLKS=""
for a in "$@"; do case $a in pnr|drc|lvs|rcx) STEPS="$STEPS $a";; *) BLKS="$BLKS $a";; esac; done
if [ -z "$STEPS" ] || [ -z "$BLKS" ]; then sed -n '2,10p' "$0"; exit 1; fi
fail=0
for b in $BLKS; do
  des=$(ls -d ALU_*/layout/verilog/$b.v 2>/dev/null | head -1 | cut -d/ -f1)
  [ -z "$des" ] && { echo "khong co khoi $b"; fail=1; continue; }
  cdl=$W/$des/layout/cdl/${b}_flat.cdl
  d=$W/out/pnr/$b
  for s in $STEPS; do
  g=$d/$b.gds; [ $s != pnr ] && [ ! -f "$g" ] && g=$W/$des/layout/gds/$b.gds   # chua chay pnr: dung GDS co san
  case $s in
  pnr)
    rm -rf "$d"; mkdir -p "$d"
    (cd "$d" && BLK=$b VLOG=$W/$des/layout/verilog/$b.v timeout ${TMO:-7200} encounter -nowin -init "$W/pnr/pnr.tcl" -log pnr < /dev/null > pnr.out 2>&1)
    echo "pnr $b rc=$?"
    grep -E 'PNR_BOX|PNR_DONE|Verification Complete' "$d/pnr.out" | sort | uniq -c | head -20
    [ -f "$d/$b.gds" ] || fail=1 ;;
  drc|lvs)
    r=$W/out/assura/$b/$s; rm -rf "$r"; mkdir -p "$r"
    sed -e "s|@GDS@|$g|g" -e "s|@CELL@|$b|g" -e "s|@RUN@|$r|g" -e "s|@CDL@|$cdl|g" "$W/pnr/$s.rsf" > "$r/run.rsf"
    (cd "$r" && timeout ${TMO:-7200} assura run.rsf > assura.log 2>&1)
    if [ $s = drc ]; then
      if [ -f "$r/$b.err" ]; then
        n=$(grep -c 'Rule No\.' "$r/$b.err")
        echo "DRC $b: $n luat vi pham"; [ "$n" -ne 0 ] && fail=1
        grep -E '^Rule No|Real Error Count' "$r/$b.err" | paste - - | head -30
      else
        echo "DRC $b: Assura khong chay xong, xem $r/assura.log"; fail=1
      fi
    else
      m=$(grep -h -i -E 'Schematic and Layout' "$r/assura.log" "$r/$b.csm" 2>/dev/null | tail -1)
      echo "LVS $b: ${m:-khong co ket qua, xem $r/assura.log}"
      echo "$m" | grep -q 'Layout Match' || fail=1
    fi
    rm -rf "$r"/*.dir "$r"/*.ldb 2>/dev/null ;;   # giu bao cao, bo co so du lieu lon
  rcx)   # LVS lai (RCX can co so du lieu LVS) roi trich ky sinh
    r=$W/out/assura/$b/rcx; rm -rf "$r"; mkdir -p "$r"
    for f in lvs rcx; do
      sed -e "s|@GDS@|$g|g" -e "s|@CELL@|$b|g" -e "s|@RUN@|$r|g" -e "s|@EXT@|${EXT:-cap}|g" \
          -e "s|@CDL@|$cdl|g" "$W/pnr/$f.rsf" > "$r/$f.rsf"
      (cd "$r" && timeout ${TMO:-7200} assura $f.rsf > $f.log 2>&1); echo "rcx/$f $b rc=$?"
    done
    ls -l "$r"/${b}_rcx.sp 2>/dev/null; grep -i -E 'error|fatal' "$r/rcx.log" | head -10
    [ -s "$r/${b}_rcx.sp" ] || fail=1
    rm -rf "$r"/*.dir "$r"/*.ldb 2>/dev/null ;;
  esac
  done
done
exit $fail
