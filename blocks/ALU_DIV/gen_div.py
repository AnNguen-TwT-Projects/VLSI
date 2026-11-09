#!/usr/bin/env python3
"""Bo chia co dau 8 bit DIV8 cua D (chay tren Windows, Python 3 stdlib).

    python blocks/ALU_DIV/gen_div.py           # ghi cells/D/CAS_X1/CAS_X1.scs, blocks/ALU_DIV/DIV8.scs, tb
    python blocks/ALU_DIV/gen_div.py --check   # muc logic: 65536 cap (a,b) so voi model.alu_ref.div_signed
    python blocks/ALU_DIV/gen_div.py --count   # dem transistor
    python blocks/ALU_DIV/gen_div.py --res out/DIV8_p0_NN 0    # so ket qua Spectre phan 0 (psfascii)

Kien truc (docs/KE_HOACH_ALU.md):
  |A| = neg(A, sA), |B| = neg(B, sB)          -- bo dao dau co dieu kien
  mang chia khong dau non-restoring 8 hang x 9 CAS_X1 (phan du 9 bit bu 2)
  hang sua phan du: R = P + (sign ? D : 0)    -- 8 CAS_X1 voi T = 0
  Q = neg(Qu, sA ^ sB), R = neg(Ru, sA)
  DZ = (B == 0), V = Q_7 & !(sA ^ sB) & !DZ   (chi xay ra o -128 / -1)
neg(X, s): Y_0 = X_0, Y_i = X_i ^ (s & (X_{i-1} | ... | X_0)) == (X ^ s) + s.
"""
import csv
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1]))
import gen_blocks as gb  # noqa: E402
from gen_blocks import BLOCKS, REPO, Block, bus, bits, val  # noqa: E402
from model.alu_ref import DIV, div_signed  # noqa: E402

T_NS, EDGE, VDD = 12.0, 20e-12, 1.2   # do o NN: tre xau nhat ~9.4 ns
PARTS = 3   # 60 vector chia 3 job (~4 s mo phong / ns o NN, job < 15 phut)
MODEL = '/home/buet/cadence/gpdk090_v4.6/models/spectre/gpdk090.scs'
CORNERS = ('NN', 'SS', 'FF')
TB_DIR = 'blocks/ALU_DIV/tb'


class TieBlock(Block):
    """Block co chan noi thang VDD/VSS (hang so 1/0) trong netlist."""
    def run(self, vals):
        return super().run({**vals, 'VDD': 1, 'VSS': 0})


def gen_cas():
    """CAS: S = X ^ (D ^ T) ^ CI, CO = maj(X, D ^ T, CI). 3 XOR2 + 3 NAND2 = 48 transistor."""
    c = Block('CAS_X1', 'cells/D/CAS_X1/CAS_X1.scs', ['X', 'D', 'T', 'CI'], ['S', 'CO'])
    b = c.x('XOR2_X1', ['D', 'T'], 'b')
    p = c.x('XOR2_X1', ['X', b], 'p')
    c.x('XOR2_X1', [p, 'CI'], 'S')
    c.x('NAND2_X1', [c.x('NAND2_X1', ['X', b], 'g_n'), c.x('NAND2_X1', [p, 'CI'], 'pc_n')], 'CO')
    return c


def neg(blk, xs, s, outs, tag):
    """Dao dau co dieu kien; outs[0] phai la xs[0] (bit 0 khong doi)."""
    assert outs[0] == xs[0]
    kn = blk.x('NAND2_X1', [s, xs[0]], f'{tag}kn1')          # !(s & X_0)
    for i in range(1, 8):
        blk.x('XNOR2_X1', [xs[i], kn], outs[i])               # X_i ^ k_i
        if i < 7:
            k = blk.x('INV_X1', [kn], f'{tag}k{i}')
            kn = blk.x('AOI21_X1', [s, xs[i], k], f'{tag}kn{i + 1}')
    return outs


def gen_div8():
    A, B, Q, R = bus('A', 8), bus('B', 8), bus('Q', 8), bus('R', 8)
    d = TieBlock('DIV8', 'blocks/ALU_DIV/DIV8.scs', A + B, Q + R + ['V', 'DZ'])
    sA, sB = A[7], B[7]
    aa = neg(d, A, sA, [A[0]] + [f'aa{i}' for i in range(1, 8)], 'na')   # |A|
    dd = neg(d, B, sB, [B[0]] + [f'dd{i}' for i in range(1, 8)], 'nb') + ['VSS']  # |B|, 9 bit
    # mang non-restoring: hang i dich vao bit a_(7-i); T = 1 (tru) o hang 0, sau do T = q truoc
    P, t = ['VSS'] * 9, 'VDD'
    qu = [None] * 8
    for i in range(8):
        x = [aa[7 - i]] + P[:8]                               # 2P + a, 9 bit
        ci, S = t, []
        for j in range(9):
            s, ci = d.x('CAS_X1', [x[j], dd[j], t, ci], [f'p{i}_{j}', f'c{i}_{j}'])
            S.append(s)
        qn = f'Q_0' if i == 7 else f'qu{7 - i}'
        t = qu[7 - i] = d.x('INV_X1', [S[8]], qn)             # q = 1 khi phan du >= 0
        P = S
    # sua phan du: Ru = P + (P<0 ? D : 0)
    ru, ci = [], 'VSS'
    for j in range(8):
        dm = d.x('INV_X1', [d.x('NAND2_X1', [dd[j], P[8]], f'dmn{j}')], f'dm{j}')
        s, ci = d.x('CAS_X1', [P[j], dm, 'VSS', ci], ['R_0' if j == 0 else f'ru{j}', f'rc{j}'])
        ru.append(s)
    sq = d.x('XOR2_X1', [sA, sB], 'sq')
    neg(d, qu, sq, Q, 'nq')
    neg(d, ru, sA, R, 'nr')
    # DZ = NOR(B), V = Q_7 & !sq & !DZ
    z1 = [d.x('NOR2_X1', [B[2 * k], B[2 * k + 1]], f'z1_{k}') for k in range(4)]
    z2 = [d.x('NAND2_X1', [z1[2 * k], z1[2 * k + 1]], f'z2_{k}') for k in range(2)]
    d.x('NOR2_X1', z2, 'DZ')
    sqn = d.x('INV_X1', [sq], 'sqn')
    d.x('NOR2_X1', [d.x('NAND2_X1', ['Q_7', sqn], 'vn'), 'DZ'], 'V')
    # bo instance cuoi cung (tail carry) khong dung: c?_8, rc7 de ho - chap nhan duoc
    return d


def build():
    gb.build()
    if 'DIV8' not in BLOCKS:
        gen_cas()
        gen_div8()
    return BLOCKS


def run_div(a, b):
    o = BLOCKS['DIV8'].call(bits(a, 8) + bits(b, 8))
    return val(o[:8]), val(o[8:16]), o[16], o[17]


def check():
    build()
    c = BLOCKS['CAS_X1']
    for v in range(16):
        x, dd, t, ci = bits(v, 4)
        tot = x + (dd ^ t) + ci
        assert c.call([x, dd, t, ci]) == [tot & 1, tot >> 1], v
    print('CAS_X1: 16/16 dung')
    n = 0
    for a in range(256):
        for b in range(256):
            q, r, v, dz = run_div(a, b)
            e = div_signed(a, b)
            if b == 0:
                assert (v, dz) == (0, 1), (a, b, q, r, v, dz)
            else:
                assert (q, r, v, dz) == (e['q'], e['r'], e['v'], 0), (a, b, (q, r, v, dz), e)
            n += 1
    print(f'DIV8: {n}/{n} cap (a,b) dung so voi div_signed (b=0: chi kiem V=0, DZ=1)')


def count(names=('CAS_X1', 'DIV8')):
    build()
    subs = gb.parse_subckts(gb.CELL_FILES + [b.path for b in BLOCKS.values()])

    def n(m):
        return 1 if m.startswith('gpdk090_') else sum(n(x) for x in subs[m])
    for name in names:
        print(f'{name:10s} {n(name):6d} transistor')


# ---------------------------------------------------------------- testbench Spectre
def tb_rows():
    """Cac dong DIV cua vectors/alu_full.csv (81), bo bot ngau nhien con 60; q/r = -1 khi b = 0."""
    R = []
    with (REPO / 'vectors' / 'alu_full.csv').open(newline='') as f:
        for r in csv.DictReader(f):
            if int(r['op']) == DIV:
                a, b = int(r['a']), int(r['b'])
                e = div_signed(a, b)
                R.append({'a': a, 'b': b, 'q': -1 if b == 0 else e['q'], 'r': -1 if b == 0 else e['r'],
                          'v': e['v'], 'dz': e['dz']})
    keep = R[:25] + R[-8:]                                   # bien + dac biet (-128/-1, -7/2, x/0 ...)
    rest = R[25:-8]
    return keep[:25] + rest[:60 - len(keep)] + keep[25:]


def part_rows(k):
    R = tb_rows()
    n = -(-len(R) // PARTS)
    return R[k * n:(k + 1) * n]


def pwl(levels, T):
    w = [0.0, levels[0] * VDD]
    for k in range(1, len(levels)):
        if levels[k] != levels[k - 1]:
            w += [k * T, levels[k - 1] * VDD, k * T + EDGE, levels[k] * VDD]
    toks = [f'{w[i] * 1e12:.0f}p {w[i + 1]:g}' for i in range(0, len(w), 2)]
    return ' \\\n    '.join(' '.join(toks[i:i + 8]) for i in range(0, len(toks), 8))


def write_tb(top, rows, T_ns, incs, maxstep='40p', tag=''):
    """tb_<top>.scs + tb_<top>_<corner>.scs trong TB_DIR (giong blocks/gen_tb.py)."""
    b, T = BLOCKS[top], T_ns * 1e-9
    out = REPO / TB_DIR if top == 'DIV8' else REPO / 'blocks/ALU_TOP/tb'
    out.mkdir(parents=True, exist_ok=True)
    L = [f'// Testbench {top}: sinh tu dong boi {Path(sys.argv[0]).name} ({len(rows)} vector)',
         f'// {T_ns:g} ns/vector, suon {EDGE * 1e12:g} ps, tai 4x INV_X1 moi ngo ra',
         'simulator lang=spectre', 'global 0',
         f'VVDD (VDD 0) vsource dc={VDD}', 'VVSS (VSS 0) vsource dc=0']
    for p in b.ins:
        c, i = gb_col(p)
        L.append(f'V{p} ({p} 0) vsource type=pwl wave=[ \\\n    {pwl([(int(r[c]) >> i) & 1 for r in rows], T)} ]')
    L.append(f'XDUT ({" ".join(b.ins + b.outs)} VDD VSS) {top}')
    for p in b.outs:
        for k in range(4):
            L.append(f'XL{p}_{k} ({p} ld_{p}_{k} VDD VSS) INV_X1')
    L.append('save ' + ' '.join(b.ins + b.outs))
    L.append('opts options save=selected temp=27 reltol=1e-3')
    L.append(f'tran tran stop={len(rows) * T_ns:g}n maxstep={maxstep} errpreset=moderate')
    (out / f'tb_{top}{tag}.scs').write_text('\n'.join(L) + '\n', encoding='ascii', newline='\n')
    rel = lambda p: os.path.relpath(REPO / p, out).replace('\\', '/')
    for cn in CORNERS:
        w = [f'// {top} corner {cn}', 'simulator lang=spectre', f'include "{MODEL}" section={cn}'] + \
            [f'include "{rel(p)}"' for p in incs] + [f'include "tb_{top}{tag}.scs"']
        (out / f'tb_{top}{tag}_{cn}.scs').write_text('\n'.join(w) + '\n', encoding='ascii', newline='\n')
    print(f'ghi {out.relative_to(REPO).as_posix()}/tb_{top}{tag}.scs ({len(rows)} vector x {T_ns:g} ns) + 3 corner')


def gb_col(port):
    base, _, idx = port.partition('_')
    return base.lower(), int(idx) if idx else 0


def div_incs():
    return ['cells/A/cells_A.scs'] + [c for c in gb.CELL_FILES if '_stub_B' in c] + \
           ['cells/D/CAS_X1/CAS_X1.scs', 'blocks/ALU_DIV/DIV8.scs']


def check_res(top, rows, res, T_ns):
    """So psfascii voi rows: mau o cuoi chu ky, nguong 0.6 V; tre = lan cat 0.6 V cuoi cua ngo ra."""
    import check_results as cr
    if not res.is_absolute() and not res.exists():
        res = cr.WORK / res
    f = res / 'tran.tran' if res.is_dir() else res
    data, T = cr.read_psfascii(f), T_ns * 1e-9
    ts, outs = data['time'], BLOCKS[top].outs
    ok, bad, worst = 0, [], []
    for k, r in enumerate(rows):
        errs = []
        for p in outs:
            c, i = gb_col(p)
            e = int(r.get(c, -1))
            if e == -1:
                continue
            v = cr.at((k + 1) * T - 20e-12, ts, data[p])
            if ((e >> i) & 1) != int(v > VDD / 2):
                errs.append(f'{p}={v:.2f}V')
        if errs:
            bad.append((k, r, errs))
        else:
            ok += 1
        if k and -1 not in r.values():   # b = 0: ngo ra khong xac dinh, khong do tre
            lc = [(cr.last_cross(ts, data[p], k * T, (k + 1) * T), p) for p in outs]
            lc = [x for x in lc if x[0] is not None]
            if lc:
                tc, p = max(lc)
                worst.append((tc - k * T - EDGE / 2, k, p))
    for k, r, errs in bad[:20]:
        print(f'SAI vector {k}: {r}: ' + ', '.join(errs))
    print(f'{top} {f.parent.name}: {ok}/{len(rows)} vector dung, {len(bad)} sai')
    worst.sort(reverse=True)
    for dl, k, p in worst[:5]:
        print(f'  tre {dl * 1e12:8.1f} ps  vector {k} {rows[k]} (truoc {rows[k - 1]}) -> {p}')
    if worst:
        print(f'TPD_WORST {worst[0][0] * 1e12:.1f} ps')
    return 0 if not bad else 1


def main():
    if '--check' in sys.argv:
        return check()
    if '--count' in sys.argv:
        return count()
    if '--res' in sys.argv:
        k = sys.argv.index('--res')
        build()
        part = int(sys.argv[k + 2]) if len(sys.argv) > k + 2 else None
        rows = tb_rows() if part is None else part_rows(part)
        return check_res('DIV8', rows, Path(sys.argv[k + 1]), T_NS)
    build()
    for name in ('CAS_X1', 'DIV8'):
        b = BLOCKS[name]
        p = REPO / b.path
        p.parent.mkdir(parents=True, exist_ok=True)
        hdr = (f'// {name}: sinh tu dong boi blocks/ALU_DIV/gen_div.py - khong sua tay\n'
               '// Can include cell A (cells_A.scs) + XOR2/XNOR2' + (' + CAS_X1' if name == 'DIV8' else '') + '.\n'
               'simulator lang=spectre\n')
        p.write_text(hdr + b.scs(), encoding='ascii', newline='\n')
        print('ghi', b.path, len(b.insts), 'instance')
    for k in range(PARTS):
        write_tb('DIV8', part_rows(k), T_NS, div_incs(), tag=f'_p{k}')


if __name__ == '__main__':
    sys.exit(main())
