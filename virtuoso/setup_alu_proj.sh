#!/bin/bash
# Tao thu muc du an Virtuoso ~/ALU_PROJ (tren dia cua may ao, khong dat tren thu muc chia se) cung cds.lib.
# Chay lai an toan: chi them nhung dong con thieu. Doi thu muc: ALU_PROJ=<duong dan> bash virtuoso/setup_alu_proj.sh
P=${ALU_PROJ:-$HOME/ALU_PROJ}
mkdir -p "$P" && cd "$P" || exit 1
touch cds.lib
add() { grep -q "^$1 $2\( \|$\)" cds.lib || echo "$*" >> cds.lib; }
[ -f "$HOME/cds.lib" ] && add SOFTINCLUDE '$HOME/cds.lib'
add DEFINE gpdk090 /home/buet/cadence/gpdk090_v4.6/libs.oa22/gpdk090
add DEFINE basic '$CDSHOME/tools/dfII/etc/cdslib/basic'
add DEFINE analogLib '$CDSHOME/tools/dfII/etc/cdslib/artist/analogLib'
echo "project $P, cds.lib:"; cat cds.lib
