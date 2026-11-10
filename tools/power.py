#!/usr/bin/env python3
"""Cong suat trung binh, nang luong / phep, EDP tu ket qua Spectre psfascii (chay tren Windows).

    python tools/power.py out/MUL8_NN 3 1.43        # <thu muc ket qua> <ns / vector> [tpd ns]

Can testbench luu dong nguon `save ... VVDD:p` (cac gen_*.py da them). P = VDD * |mean I(VVDD)|
lay tich phan hinh thang tren toan bo thoi gian mo phong; E/phep = P * T (moi vector la 1 phep);
EDP = E * tpd. Gom ca 4 INV tai moi ngo ra (giong nhau giua cac khoi nen so sanh duoc).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'blocks'))
import check_results as cr  # noqa: E402  (read_psfascii, WORK)

VDD = 1.2


def power(res):
    res = Path(res)
    if not res.is_absolute() and not res.exists():
        res = cr.WORK / res
    d = cr.read_psfascii(res / 'tran.tran' if res.is_dir() else res)
    key = next((k for k in d if k.upper() in ('VVDD:P', 'VVDD:1')), None)
    if key is None:
        raise SystemExit(f'khong co dong VVDD:p trong {res} (tb cu, chay lai sau khi sinh lai tb)')
    t, i = d['time'], d[key]
    q = sum((t[k + 1] - t[k]) * (i[k + 1] + i[k]) / 2 for k in range(len(t) - 1))
    return VDD * abs(q) / (t[-1] - t[0])


def _selftest():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / 'tran.tran'
        f.write_text('HEADER\nSWEEP\n"time" "sweep"\nVALUE\n"time" 0\n"VVDD:p" -1e-3\n'
                     '"time" 1e-9\n"VVDD:p" -1e-3\nEND\n')
        assert abs(power(tmp) - 1.2e-3) < 1e-12, power(tmp)


if __name__ == '__main__':
    _selftest()
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    p = power(sys.argv[1])
    T = float(sys.argv[2]) * 1e-9
    line = f'{Path(sys.argv[1]).name}: P_avg {p * 1e6:.1f} uW, E/phep {p * T * 1e12:.3f} pJ'
    if len(sys.argv) > 3:
        line += f', EDP {p * T * float(sys.argv[3]) * 1e-9 * 1e24:.3f} pJ*ns'
    print(line)
