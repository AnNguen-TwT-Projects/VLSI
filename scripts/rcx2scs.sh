#!/bin/bash
# Doi netlist Assura RCX (HSPICE, phang) sang Spectre de mo phong sau layout.
#   bash scripts/rcx2scs.sh ALU_TOPK            # out/assura/ALU_TOPK/rcx/ALU_TOPK_rcx.sp -> ALU_8bit/layout/rcx/ALU_TOPK_rcx.scs
# Subckt ra co cung ten va cung thu tu chan voi netlist truoc layout (lay tu dong XDUT cua testbench),
# nen dung lai duoc testbench cu (cac file tb_*_post_NN/SS/FF.scs trong layout/rcx).
cd "$(dirname "$0")/.." || exit 1
rc=0
for b in "$@"; do
  sp=out/assura/$b/rcx/${b}_rcx.sp
  des=$(ls -d ALU_*/layout/verilog/$b.v 2>/dev/null | head -1 | cut -d/ -f1)
  ports=$(cat "$des"/tb/tb_${b}.scs "$des"/tb/tb_${b}_p0.scs 2>/dev/null | sed -n "s/^XDUT (\(.*\)) $b\$/\1/p" | head -1)
  if [ ! -s "$sp" ] || [ -z "$ports" ]; then echo "$b: thieu $sp hoac khong tim thay dong XDUT trong testbench"; rc=1; continue; fi
  awk -v blk="$b" -v ports="$ports" '
    function nm(s,   t) {            # ten Spectre: chi chu, so, "_"; hai ten khac nhau khong duoc trung sau khi doi
        t = s; gsub(/[^A-Za-z0-9_]/, "_", t)
        if ((t in seen) && seen[t] != s) { print "trung ten sau khi doi: " s " / " seen[t] > "/dev/stderr"; bad = 1 }
        seen[t] = s; return t
    }
    function card(c,   f, n, i, k, kv, p, par) {
        n = split(c, f, " "); if (n == 0) return
        k = toupper(substr(f[1], 1, 1))
        if (toupper(f[1]) == ".SUBCKT") { for (i = 3; i <= n; i++) pin[f[i]] = 1 }
        else if (k == "M") {
            kv = ""
            for (i = 7; i <= n; i++) { split(tolower(f[i]), p, "="); par[p[1]] = p[2] }
            for (i = 1; i <= 6; i++) if (keep[i] in par) kv = kv (kv == "" ? "" : " ") keep[i] "=" par[keep[i]]
            if (!(f[6] in dev)) { print "model la: " f[6] > "/dev/stderr"; bad = 1 }
            print "    " nm("I_" f[1]) " (" nm(f[2]) " " nm(f[3]) " " nm(f[4]) " " nm(f[5]) ") " dev[f[6]] " " kv
            nmos++
        }
        else if (k == "C") { print "    " nm("I_" f[1]) " (" nm(f[2]) " " nm(f[3]) ") capacitor c=" f[4]; ncap++ }
        else if (k == "R") print "    " nm("I_" f[1]) " (" nm(f[2]) " " nm(f[3]) ") resistor r=" f[4]
        else if (k != ".") { print "dong la: " substr(c, 1, 80) > "/dev/stderr"; bad = 1 }
    }
    BEGIN {
        dev["nmos1v"] = "gpdk090_nmos1v"; dev["pmos1v"] = "gpdk090_pmos1v"
        split("w l ad as pd ps", keep, " ")          # simW / fw la tham so rieng cua Assura
        print "// " blk " sau layout: Assura RCX"; print "simulator lang=spectre"; print "subckt " blk " " ports
    }
    { sub(/\r$/, "") }
    /^\+/ { cur = cur " " substr($0, 2); next }
    /^\*/ || /^[ \t]*$/ { next }
    { card(cur); cur = $0 }
    END {
        card(cur); print "ends " blk
        n = split(ports, pp, " ")
        for (i = 1; i <= n; i++) { inports[pp[i]] = 1; if (!(pp[i] in pin) && pp[i] != "VDD" && pp[i] != "VSS") { print "chan thieu trong RCX: " pp[i] > "/dev/stderr"; bad = 1 } }
        for (p in pin) if (!(p in inports)) { print "chan thua trong RCX: " p > "/dev/stderr"; bad = 1 }
        print blk ": " nmos " transistor, " ncap " tu" > "/dev/stderr"
        exit bad
    }' "$sp" > "$des/layout/rcx/${b}_rcx.scs" || rc=1
done
exit $rc
