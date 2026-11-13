# final_value.awk -- in gia tri logic cuoi mo phong cua moi tin hieu da luu (dung cho testbench demo, khong co .exp).
#   awk -f scripts/final_value.awk out/tb_demo_ALU_TOPK/tran.tran
# Bus <TEN>_<i> duoc gop lai va in dang hex (bit cao ben trai).
$1 == "VALUE" { sec = 1; next }
$1 == "END" { sec = 0; next }
sec { n = $1; gsub(/"/, "", n); if (n != "time" && n !~ /:/) { if (!(n in v)) order[++cnt] = n; v[n] = ($2 > 0.6) } }
END {
    for (k = 1; k <= cnt; k++) {
        n = order[k]
        if (n ~ /_[0-9]+$/) {
            b = n; sub(/_[0-9]+$/, "", b); i = n; sub(/^.*_/, "", i); i += 0
            if (!(b in hi)) { bus[++nb] = b; hi[b] = i }
            if (i > hi[b]) hi[b] = i
            have[b, i] = 1
        } else printf "%s = %d\n", n, v[n]
    }
    for (k = 1; k <= nb; k++) {
        b = bus[k]; full = 1
        for (i = 0; i <= hi[b]; i++) if (!((b, i) in have)) full = 0
        if (!full) { for (i = hi[b]; i >= 0; i--) if ((b, i) in have) printf "%s_%d = %d\n", b, i, v[b "_" i]; continue }
        s = ""; top = int(hi[b] / 4) * 4
        for (i = top; i >= 0; i -= 4) {
            d = 0
            for (j = 3; j >= 0; j--) if (i + j <= hi[b]) d = d * 2 + v[b "_" (i + j)]
            s = s sprintf("%X", d)
        }
        printf "%s[%d:0] = 0x%s\n", b, hi[b], s
    }
}
