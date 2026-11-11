#!/bin/bash
# Run every cell testbench (cells/A and cells/_stub_B) at the given corners. Runs in the VM.
#   python tools/vmjob.py --label cells -c "bash cells/A/run_cells.sh NN FF SS"
# Results: out/cells/<corner>/<CELL>/tr.tran (psfascii), checked on Windows by check_cells.py.
cd "$(dirname "$0")/../.." || exit 1
ROOT=$PWD
CORNERS=${*:-NN FF SS}
fail=0
for c in $CORNERS; do
  for tb in cells/A/*/tb_*.scs cells/B/*/tb_*.scs cells/C/*/tb_*.scs cells/D/*/tb_*.scs cells/_stub_B/*/tb_*.scs; do
    d=$ROOT/$(dirname "$tb"); cell=$(basename "$d")
    [ -n "$ONLY" ] && [[ " $ONLY " != *" $cell "* ]] && continue   # ONLY="INV_X4 FA_X1": chi cac cell nay
    out=${OUTD:-$ROOT/out}/cells/$c/$cell
    rm -rf "$out"; mkdir -p "$out"
    # corner copy: switch model section, make the tb's own includes absolute
    sed -e "s/section=NN/section=$c/" -e "s#^include \"\([^/][^\"]*\)\"#include \"$d/\1\"#" "$tb" > "$out/tb.scs"
    if (cd "$d" && timeout 900 spectre -format psfascii -raw "$out" +log "$out/spectre.log" "$out/tb.scs" > /dev/null 2>&1); then
      echo "OK   $c $cell"
    else
      echo "FAIL $c $cell"; grep -i -B2 -A4 "error" "$out/spectre.log" | head -30; fail=1
    fi
  done
done
exit $fail
