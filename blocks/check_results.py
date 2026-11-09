#!/usr/bin/env python3
"""So ket qua Spectre (psfascii) voi vector mong doi va do tre (chay tren Windows).

    python blocks/check_results.py KSA8 out/KSA8_NN
    python blocks/check_results.py ALU_CORE out/ALU_CORE_NN

Thu muc ket qua tuong doi tinh tu Share/VLSI_work (bien VLSI_SHARE nhu tools/vmjob.py).
Lay mau ngo ra o cuoi moi chu ky (t = (k+1)T - 20 ps), nguong 0.6 V, so voi cot mong doi
(o trong hoac -1 = bo qua). Do tre: tu 50% suon vao (kT + 10 ps) den lan cat 0.6 V cuoi cung
cua bat ky ngo ra nao trong chu ky, voi cac vector ADD/SUB (KSA8: moi vector), bo vector 0.
Ma thoat 0 khi dung 100%.
"""
import bisect
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_tb import BENCH, EDGE, T, VDD, build, col_bit, rows  # noqa: E402

WORK = Path(os.environ.get('VLSI_SHARE', r'D:\Hoc\VLSI_Design\Share')) / 'VLSI_work'
VTH = VDD / 2


def read_psfascii(path):
    """{ten: [gia tri]} tu file tran psfascii; bien quet (time) dat ten 'time'."""
    data, sec, sweep = {}, None, None
    with open(path, encoding='ascii', errors='replace') as f:
        for line in f:
            s = line.strip()
            if s in ('HEADER', 'TYPE', 'SWEEP', 'TRACE', 'VALUE', 'END'):
                sec = s
                continue
            if sec == 'SWEEP' and sweep is None and s.startswith('"'):
                sweep = s.split('"')[1]
            elif sec == 'VALUE' and s.startswith('"'):
                name, _, v = s[1:].partition('"')
                try:
                    data.setdefault('time' if name == sweep else name, []).append(float(v.split()[0]))
                except (ValueError, IndexError):
                    pass
    return data


def at(t, ts, vs):
    i = bisect.bisect_left(ts, t)
    if i <= 0:
        return vs[0]
    if i >= len(ts):
        return vs[-1]
    t0, t1 = ts[i - 1], ts[i]
    return vs[i - 1] + (vs[i] - vs[i - 1]) * (t - t0) / (t1 - t0)


def last_cross(ts, vs, t_lo, t_hi):
    i, j = bisect.bisect_left(ts, t_lo), bisect.bisect_right(ts, t_hi)
    last = None
    for k in range(max(i, 1), j):
        a, b = vs[k - 1] - VTH, vs[k] - VTH
        if (a < 0) != (b < 0):
            last = ts[k - 1] + (ts[k] - ts[k - 1]) * a / (a - b)
    return last


def main():
    top, res = sys.argv[1], Path(sys.argv[2])
    if not res.is_absolute() and not res.exists():
        res = WORK / res
    f = res / 'tran.tran' if res.is_dir() else res
    data = read_psfascii(f)
    ts = data['time']
    outs = build()[top].outs
    R, sel = rows(top), BENCH[top][2]
    ok, bad, weak, worst = 0, [], 0, []
    for k, r in enumerate(R):
        t_s = (k + 1) * T - 20e-12
        errs = []
        for p in outs:
            c, i = col_bit(p)
            e = r.get(c, '')
            v = at(t_s, ts, data[p])
            if abs(v - VTH) < 0.3 * VDD:
                weak += 1
            if e in ('', '-1'):
                continue
            want, got = (int(e) >> i) & 1, int(v > VTH)
            if want != got:
                errs.append(f'{p}={got}(can {want}, {v:.3f}V)')
        if errs:
            bad.append((k, r, errs))
        else:
            ok += 1
        if k and sel(r):
            lc = [(last_cross(ts, data[p], k * T, (k + 1) * T), p) for p in outs]
            lc = [x for x in lc if x[0] is not None]
            if lc:
                tc, p = max(lc)
                worst.append((tc - k * T - EDGE / 2, k, p))
    for k, r, errs in bad[:30]:
        print(f'SAI vector {k}: {dict(r)}: ' + ', '.join(errs))
    print(f'{top} {f.parent.name}: {ok}/{len(R)} vector dung, {len(bad)} sai'
          f'{f", {weak} mau gan nguong (|V-0.6|<0.36V)" if weak else ""}')
    worst.sort(reverse=True)
    for d, k, p in worst[:5]:
        r = R[k]
        print(f'  tre {d * 1e12:7.1f} ps  vector {k} op={r.get("op", "-")} a={r["a"]} b={r["b"]}'
              f' (truoc: a={R[k - 1]["a"]} b={R[k - 1]["b"]} op={R[k - 1].get("op", "-")}) -> {p}')
    if worst:
        print(f'TPD_WORST {worst[0][0] * 1e12:.1f} ps')
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
