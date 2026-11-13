# check.awk -- so ket qua Spectre (psfascii) voi bang gia tri mong doi (.exp), do tre va nang luong.
#   awk -f scripts/check.awk <tb>.exp <thu muc ket qua>/tran.tran
# File .exp:  T <chu ky, s> | MARGIN <s> | STRICT <0|1> | OUT <ten ngo ra ...>
#             V <k> <do tre 0|1> <bit mong doi theo thu tu OUT, x = bo qua> ; <mo ta vector>
# Lay mau moi ngo ra tai (k+1)T - MARGIN, nguong VDD/2 (STRICT 1: phai cach ray <= 10% VDD).
# Tre vector k = lan cat VDD/2 cuoi cung cua moi ngo ra trong [kT, (k+1)T] - (kT + 10 ps).
# Nang luong / phep = VDD * |I(VVDD) trung binh| * T (can "save VVDD:p" trong testbench).
# Ma thoat 0 khi moi vector dung.
BEGIN { VDD = 1.2; VTH = VDD / 2; EDGE = 20e-12; nv = 0; ks = 0; havep = 0 }
FNR == NR {
    if ($1 == "T") T = $2 + 0
    else if ($1 == "MARGIN") MARGIN = $2 + 0
    else if ($1 == "STRICT") STRICT = $2 + 0
    else if ($1 == "OUT") { no = NF - 1; for (i = 2; i <= NF; i++) { out[i - 1] = $i; isout[$i] = 1 } }
    else if ($1 == "V") {
        meas[nv] = $3; want[nv] = $4
        d = $0; sub(/^[^;]*; ?/, "", d); desc[nv] = d; nv++
    }
    next
}
$1 == "VALUE" { sec = 1; next }
$1 == "END" { sec = 0; next }
!sec { next }
{
    name = $1; gsub(/"/, "", name); v = $2 + 0
    if (name == "time") { point(); tprev = t; t = v; have = 1; next }
    cur[name] = v
}
function point(    i, o, a, b, tc, k, ts) {
    if (!have) return
    if (seen) {
        for (i = 1; i <= no; i++) {
            o = out[i]; a = prev[o] - VTH; b = cur[o] - VTH
            if ((a < 0) != (b < 0)) {
                tc = tprev + (t - tprev) * a / (a - b); k = int(tc / T)
                if (!(k in last) || tc > last[k]) { last[k] = tc; lastn[k] = o }
            }
        }
        while (ks < nv && (ts = (ks + 1) * T - MARGIN) <= t) {
            for (i = 1; i <= no; i++) {
                o = out[i]
                got[ks, i] = prev[o] + (cur[o] - prev[o]) * (ts - tprev) / (t - tprev)
            }
            ks++
        }
        if ("VVDD:p" in cur) { havep = 1; q += (prev["VVDD:p"] + cur["VVDD:p"]) / 2 * (t - tprev) }
    }
    for (o in cur) prev[o] = cur[o]
    seen = 1
}
END {
    point()
    if (nv == 0 || no == 0 || T <= 0) { print "LOI: file .exp khong hop le"; exit 2 }
    if (ks < nv) { printf "LOI: mo phong dung o %.3g s, thieu %d vector\n", t, nv - ks; exit 2 }
    ok = 0; bad = 0; worst = -1
    for (k = 0; k < nv; k++) {
        e = ""
        for (i = 1; i <= no; i++) {
            w = substr(want[k], i, 1); if (w == "x") continue
            g = got[k, i]
            if (STRICT) good = (w == "1") ? (g > 0.9 * VDD) : (g < 0.1 * VDD)
            else good = ((g > VTH) == (w == "1"))
            if (!good) e = e sprintf(" %s=%.3fV(can %s)", out[i], g, w)
        }
        if (e != "") { bad++; if (bad <= 20) printf "SAI vector %d [%s]:%s\n", k, desc[k], e }
        else ok++
        if (meas[k] == 1 && (k in last)) {
            dl = last[k] - k * T - EDGE / 2
            if (dl > worst) { worst = dl; wk = k; wn = lastn[k] }
        }
    }
    printf "%s: %d/%d vector dung, %d sai\n", (bad ? "FAIL" : "PASS"), ok, nv, bad
    if (worst >= 0) printf "  tre lon nhat  %.1f ps  (vector %d [%s], truoc do [%s], ngo ra %s)\n", worst * 1e12, wk, desc[wk], desc[wk - 1], wn
    if (havep && t > 0) {
        p = VDD * (q < 0 ? -q : q) / t
        printf "  cong suat TB  %.1f uW   nang luong/phep  %.3f pJ\n", p * 1e6, p * T * 1e12
    }
    exit (bad ? 1 : 0)
}
