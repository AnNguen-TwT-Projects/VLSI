#!/bin/bash
# Tang 1: mo phong 18 cell bang Spectre roi kiem tra bang chan tri, do tre (tai FO4).
#   bash scripts/run_cells.sh                       # corner NN SS FF
#   bash scripts/run_cells.sh NN                    # mot corner
#   ONLY="INV_X1 FA_X1" bash scripts/run_cells.sh NN
# Ket qua: out/cells/<corner>/<CELL>/tr.tran (psfascii) + spectre.log. Ma thoat 0 khi moi cell PASS.
cd "$(dirname "$0")/.." || exit 1
ROOT=$PWD
CORNERS=${*:-NN SS FF}
fail=0
for c in $CORNERS; do
  for tb in tang1_cell/*/tb_*.scs; do
    cell=$(basename "$(dirname "$tb")")
    [ -n "$ONLY" ] && [[ " $ONLY " != *" $cell "* ]] && continue
    out=$ROOT/out/cells/$c/$cell
    rm -rf "$out"; mkdir -p "$out"
    # ban sao theo corner: doi section cua model, doi include tuong doi thanh tuyet doi
    sed -e "s/section=NN/section=$c/" -e "s#^include \"\.\./#include \"$ROOT/tang1_cell/#" "$tb" > "$out/tb.scs"
    if timeout 900 spectre -format psfascii -raw "$out" +log "$out/spectre.log" "$out/tb.scs" < /dev/null > /dev/null 2>&1; then
      r=$(awk -f scripts/check.awk "${tb%.scs}.exp" "$out/tr.tran") || fail=1
      printf '%-2s %-10s %s\n' "$c" "$cell" "$(echo "$r" | sed -e 's/^ *//' -e 's/ *(vector.*//' | tr '\n' ';')"
    else
      echo "$c $cell: Spectre loi, xem $out/spectre.log"; grep -i -A4 "error" "$out/spectre.log" | head -20; fail=1
    fi
  done
done
[ $fail -eq 0 ] && echo "TAT CA CELL: PASS" || echo "CO CELL FAIL"
exit $fail
