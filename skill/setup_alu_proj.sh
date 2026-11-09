#!/bin/bash
# Create the Virtuoso project dir ~/ALU_PROJ (on the VM disk, not hgfs) with a cds.lib.
# Safe to re-run: only appends the lines that are missing.
P=${ALU_PROJ:-$HOME/ALU_PROJ}
mkdir -p "$P" && cd "$P" || exit 1
touch cds.lib
add() { grep -q "^$1 $2\( \|$\)" cds.lib || echo "$*" >> cds.lib; }
[ -f "$HOME/cds.lib" ] && add SOFTINCLUDE '$HOME/cds.lib'
add DEFINE gpdk090 /home/buet/cadence/gpdk090_v4.6/libs.oa22/gpdk090
add DEFINE basic '$CDSHOME/tools/dfII/etc/cdslib/basic'
add DEFINE analogLib '$CDSHOME/tools/dfII/etc/cdslib/artist/analogLib'
echo "project $P, cds.lib:"; cat cds.lib
