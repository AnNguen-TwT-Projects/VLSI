#!/usr/bin/env python3
"""Sinh netlist Spectre cho khoi cua A (chay tren Windows, Python 3 stdlib).

    python blocks/gen_blocks.py           # ghi blocks/ALU_ADD/*.scs, blocks/ALU_CORE/*.scs
    python blocks/gen_blocks.py --check   # mo phong muc logic cac netlist vua sinh (Python)
    python blocks/gen_blocks.py --count   # dem transistor (doc file .scs cua cell + khoi)

Chi dung cell cua A (CONVENTIONS muc 4) + XOR2_X1/XNOR2_X1 (stub cua B).
Thu tu chan moi cell: ngo vao, ngo ra, VDD VSS.
"""
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

nt = lambda x: 1 - x
# Ham logic cua cell (dung cho --check), dung thu tu chan trong CONVENTIONS muc 4
FUNC = {
    'INV_X1':   lambda a: (nt(a),),
    'NAND2_X1': lambda a, b: (nt(a & b),),
    'NOR2_X1':  lambda a, b: (nt(a | b),),
    'AOI21_X1': lambda a1, a2, b: (nt(a1 & a2 | b),),
    'OAI21_X1': lambda a1, a2, b: (nt((a1 | a2) & b),),
    'BLK_P':    lambda gi, pi, gk, pk: (nt(gi | pi & gk), nt(pi & pk)),
    'BLK_N':    lambda gin, pin, gkn, pkn: (nt(gin & (pin | gkn)), nt(pin | pkn)),
    'GRY_P':    lambda gi, pi, gk: (nt(gi | pi & gk),),
    'GRY_N':    lambda gin, pin, gkn: (nt(gin & (pin | gkn)),),
    'XOR2_X1':  lambda a, b: (a ^ b,),
    'XNOR2_X1': lambda a, b: (nt(a ^ b),),
}
CELL_FILES = [f'cells/A/{c}/{c}.scs' for c in
              ('INV_X1', 'NAND2_X1', 'NOR2_X1', 'AOI21_X1', 'OAI21_X1',
               'BLK_P', 'BLK_N', 'GRY_P', 'GRY_N')] + \
             [f'cells/_stub_B/{c}/{c}.scs' for c in ('XOR2_X1', 'XNOR2_X1')]
BLOCKS = {}   # ten -> Block, theo thu tu sinh (khoi con truoc)


def bus(name, w):
    return [f'{name}_{i}' for i in range(w)]


class Block:
    def __init__(self, name, path, ins, outs):
        self.name, self.path, self.ins, self.outs, self.insts = name, path, ins, outs, []
        BLOCKS[name] = self

    def x(self, master, ins, outs):
        """Them instance; tra ve ten net ra (str neu 1 ngo ra)."""
        outs = [outs] if isinstance(outs, str) else list(outs)
        self.insts.append((master, list(ins), outs))
        return outs[0] if len(outs) == 1 else outs

    def scs(self):
        L = [f'subckt {self.name} {" ".join(self.ins + self.outs)} VDD VSS']
        for k, (m, i, o) in enumerate(self.insts):
            L.append(f'I{k} ({" ".join(i + o)} VDD VSS) {m}')
        L.append(f'ends {self.name}')
        return '\n'.join(wrap(l) for l in L) + '\n'

    def run(self, vals):
        v = dict(vals)
        for m, i, o in self.insts:   # instance duoc sinh theo thu tu topo
            args = [v[n] for n in i]
            v.update(zip(o, FUNC[m](*args) if m in FUNC else BLOCKS[m].call(args)))
        return v

    def call(self, args):
        v = self.run(dict(zip(self.ins, args)))
        return [v[o] for o in self.outs]


def wrap(line, width=90):
    out, cur = [], ''
    for tok in line.split():
        if cur and len(cur) + 1 + len(tok) > width:
            out.append(cur + ' \\')
            cur = '    ' + tok
        else:
            cur = f'{cur} {tok}' if cur else tok
    return '\n'.join(out + [cur])


# ---------------------------------------------------------------- KSA8
def gen_ksa8():
    """Kogge-Stone 8 bit, 3 tang prefix xen ke cuc tinh N/P/N.
    Tang 0: gn = NAND(A,B), pn = XNOR(A,B) (tich cuc thap).  CIN gop vao bit 0:
    G0' = g0 + p0*CIN = GRY_N(gn0, pn0, !CIN) (tich cuc cao).
    Tang 1 BLK_N/GRY_N (vao thap, ra cao), tang 2 BLK_P/GRY_P (vao cao, ra thap),
    tang 3 GRY_N (vao thap, ra cao).  Tin hieu da xong (gray) di thang qua tang
    thi co the sai cuc -> them INV tren nhanh do (khong nam tren chuoi cell prefix)."""
    A, B, S = bus('A', 8), bus('B', 8), bus('S', 8)
    k = Block('KSA8', 'blocks/ALU_ADD/KSA8.scs', A + B + ['CIN'], S + ['C7', 'C8'])
    gn = [k.x('NAND2_X1', [A[i], B[i]], f'gn{i}') for i in range(8)]
    pn = [k.x('XNOR2_X1', [A[i], B[i]], f'pn{i}') for i in range(8)]
    k.x('INV_X1', ['CIN'], 'cinn')
    k.x('GRY_N', [gn[0], pn[0], 'cinn'], 'G0_0')        # G[0:cin], cuc cao
    # cur[i] = (G, P, cuc) cua nhom dang xet tai bit i; P=None khi da xong (gray)
    cur = {i: (gn[i], pn[i], 0, i) for i in range(1, 8)}
    fin = {0: {1: 'G0_0'}}                              # bit da xong: {cuc: ten net}
    orig = {0: 1}

    def need(j, pol):
        if pol not in fin[j]:
            src = fin[j][1 - pol]
            fin[j][pol] = k.x('INV_X1', [src], src + ('n' if pol == 0 else 'p'))
        return fin[j][pol]

    for lvl, d in ((1, 1), (2, 2), (3, 4)):
        want = 0 if lvl % 2 else 1                      # tang le: cell _N (vao tich cuc thap)
        suf = '_N' if want == 0 else '_P'
        sfx = '' if want == 0 else 'n'                  # cuc ngo ra = 1 - want
        nxt, done = {}, set(fin)                        # bit da xong truoc tang nay
        for i in range(d, 8):
            if i not in cur:
                continue
            gi, pi, pol, lo = cur[i]
            assert pol == want
            j = i - d
            if j in done:                               # gray cell -> xong bit i
                g = k.x('GRY' + suf, [gi, pi, need(j, want)], f'G{i}_0{sfx}')
                fin[i] = {1 - want: g}
                orig[i] = 1 - want
            else:
                gj, pj, polj, loj = cur[j]
                assert polj == want
                g, p = k.x('BLK' + suf, [gi, pi, gj, pj], [f'G{i}_{loj}{sfx}', f'P{i}_{loj}{sfx}'])
                nxt[i] = (g, p, 1 - want, loj)
        cur = nxt
    assert not cur and len(fin) == 8
    assert sum(m[:3] in ('GRY', 'BLK') for m, _, _ in k.insts) == 18   # 17 prefix + 1 gop CIN
    # Tong: s_i = p_i xor c_i, c_i = G[i-1:0]; dung cuc goc (khong qua INV)
    for i in range(8):
        c, cp = ('CIN', 1) if i == 0 else (fin[i - 1][orig[i - 1]], orig[i - 1])
        k.x('XNOR2_X1' if cp == 1 else 'XOR2_X1', [pn[i], c], S[i])
    for name, j in (('C7', 6), ('C8', 7)):
        assert orig[j] == 1
        # doi ten net ra: thay ten noi bo bang ten chan
        old = fin[j][1]
        k.insts = [(m, [name if n == old else n for n in i], [name if n == old else n for n in o])
                   for m, i, o in k.insts]
        fin[j][1] = name
    return k


def gen_addsub8():
    A, B, S = bus('A', 8), bus('B', 8), bus('S', 8)
    a = Block('ADDSUB8', 'blocks/ALU_ADD/ADDSUB8.scs', A + B + ['SUB'], S + ['C7', 'C8'])
    bx = [a.x('XOR2_X1', [B[i], 'SUB'], f'bx{i}') for i in range(8)]
    a.x('KSA8', A + bx + ['SUB'], S + ['C7', 'C8'])
    return a


# ---------------------------------------------------------------- ALU_CORE
SELS = ['SEL_AS', 'SEL_AND', 'SEL_OR', 'SEL_XOR', 'SEL_NOT', 'SEL_MUL', 'SEL_DIV']


def gen_logic8():
    A, B = bus('A', 8), bus('B', 8)
    outs = bus('AND', 8) + bus('OR', 8) + bus('XOR', 8) + bus('NOT', 8)
    g = Block('LOGIC8', 'blocks/ALU_CORE/LOGIC8.scs', A + B, outs)
    for i in range(8):
        g.x('INV_X1', [g.x('NAND2_X1', [A[i], B[i]], f'nand{i}')], f'AND_{i}')
        g.x('INV_X1', [g.x('NOR2_X1', [A[i], B[i]], f'nor{i}')], f'OR_{i}')
        g.x('XOR2_X1', [A[i], B[i]], f'XOR_{i}')
        g.x('INV_X1', [A[i]], f'NOT_{i}')
    return g


def gen_dec_op():
    """OP_3..0 -> select one-hot. ADD(0000)/SUB(0001) chung SEL_AS; ma khac -> tat ca 0."""
    OP = bus('OP', 4)
    d = Block('DEC_OP', 'blocks/ALU_CORE/DEC_OP.scs', OP, SELS)
    o = {}
    for i in range(4):
        o[(i, 1)] = OP[i]
        o[(i, 0)] = d.x('INV_X1', [OP[i]], f'opn{i}')
    hi = {v: d.x('NAND2_X1', [o[(3, v[0])], o[(2, v[1])]], f'h{v[0]}{v[1]}') for v in ((0, 0), (0, 1), (1, 0))}
    lo = {v: d.x('NAND2_X1', [o[(1, v[0])], o[(0, v[1])]], f'l{v[0]}{v[1]}') for v in ((0, 0), (0, 1), (1, 0), (1, 1))}
    d.x('NOR2_X1', [hi[(0, 0)], 'OP_1'], 'SEL_AS')      # 000x
    d.x('NOR2_X1', [hi[(0, 0)], lo[(1, 0)]], 'SEL_AND')  # 0010
    d.x('NOR2_X1', [hi[(0, 0)], lo[(1, 1)]], 'SEL_OR')   # 0011
    d.x('NOR2_X1', [hi[(0, 1)], lo[(0, 0)]], 'SEL_XOR')  # 0100
    d.x('NOR2_X1', [hi[(0, 1)], lo[(0, 1)]], 'SEL_NOT')  # 0101
    d.x('NOR2_X1', [hi[(1, 0)], lo[(0, 1)]], 'SEL_MUL')  # 1001
    d.x('NOR2_X1', [hi[(1, 0)], lo[(1, 1)]], 'SEL_DIV')  # 1011
    return d


def gen_outmux():
    """MUX AND-OR. Byte thap: 6 nguon qua NAND2(sel,x) -> NAND2 cap -> NOR2;
    tong cua bo cong (den muon nhat) vao AOI21 o tang 3 -> NAND2 -> Y.
    Byte cao: NAND2(SEL_MUL,MULP_hi), NAND2(SEL_DIV,DIVR) -> NAND2."""
    srcs = ['S', 'AND', 'OR', 'XOR', 'NOT']
    ins = sum((bus(s, 8) for s in srcs), []) + bus('MULP', 16) + bus('DIVQ', 8) + bus('DIVR', 8) + SELS
    m = Block('OUTMUX', 'blocks/ALU_CORE/OUTMUX.scs', ins, bus('Y', 16))
    for i in range(8):
        pairs = [('SEL_AND', f'AND_{i}'), ('SEL_OR', f'OR_{i}'), ('SEL_XOR', f'XOR_{i}'),
                 ('SEL_NOT', f'NOT_{i}'), ('SEL_MUL', f'MULP_{i}'), ('SEL_DIV', f'DIVQ_{i}')]
        n = [m.x('NAND2_X1', [s, x], f'n{i}_{k}') for k, (s, x) in enumerate(pairs)]
        o = [m.x('NAND2_X1', [n[2 * k], n[2 * k + 1]], f'o{i}_{k}') for k in range(3)]
        q1 = m.x('NOR2_X1', [o[0], o[1]], f'q{i}_1')
        q2 = m.x('AOI21_X1', ['SEL_AS', f'S_{i}', o[2]], f'q{i}_2')
        m.x('NAND2_X1', [q1, q2], f'Y_{i}')
    for i in range(8, 16):
        a = m.x('NAND2_X1', ['SEL_MUL', f'MULP_{i}'], f'hm{i}')
        b = m.x('NAND2_X1', ['SEL_DIV', f'DIVR_{i - 8}'], f'hd{i}')
        m.x('NAND2_X1', [a, b], f'Y_{i}')
    return m


def gen_flags():
    Y = bus('Y', 16)
    f = Block('FLAGS', 'blocks/ALU_CORE/FLAGS.scs',
              Y + ['C7', 'C8', 'DIVV', 'DIVDZ', 'SEL_AS', 'SEL_DIV'], ['Z', 'C', 'V', 'DZ'])
    a = [f.x('NOR2_X1', [Y[2 * k], Y[2 * k + 1]], f'za{k}') for k in range(8)]
    b = [f.x('NAND2_X1', [a[2 * k], a[2 * k + 1]], f'zb{k}') for k in range(4)]
    c = [f.x('NOR2_X1', [b[2 * k], b[2 * k + 1]], f'zc{k}') for k in range(2)]
    f.x('INV_X1', [f.x('NAND2_X1', c, 'zd')], 'Z')
    f.x('INV_X1', [f.x('NAND2_X1', ['C8', 'SEL_AS'], 'cn')], 'C')
    x = f.x('XOR2_X1', ['C7', 'C8'], 'ovf')
    f.x('NAND2_X1', [f.x('NAND2_X1', ['SEL_AS', x], 'v1'), f.x('NAND2_X1', ['SEL_DIV', 'DIVV'], 'v2')], 'V')
    f.x('INV_X1', [f.x('NAND2_X1', ['SEL_DIV', 'DIVDZ'], 'dzn')], 'DZ')
    return f


def gen_alu_core():
    A, B = bus('A', 8), bus('B', 8)
    ins = A + B + bus('OP', 4) + bus('MULP', 16) + bus('DIVQ', 8) + bus('DIVR', 8) + ['DIVV', 'DIVDZ']
    t = Block('ALU_CORE', 'blocks/ALU_CORE/ALU_CORE.scs', ins, bus('Y', 16) + ['Z', 'C', 'V', 'DZ'])
    t.x('DEC_OP', bus('OP', 4), SELS)
    t.x('ADDSUB8', A + B + ['OP_0'], bus('S', 8) + ['C7', 'C8'])
    lg = bus('AND', 8) + bus('OR', 8) + bus('XOR', 8) + bus('NOT', 8)
    t.x('LOGIC8', A + B, lg)
    t.x('OUTMUX', bus('S', 8) + lg + bus('MULP', 16) + bus('DIVQ', 8) + bus('DIVR', 8) + SELS, bus('Y', 16))
    t.x('FLAGS', bus('Y', 16) + ['C7', 'C8', 'DIVV', 'DIVDZ', 'SEL_AS', 'SEL_DIV'], ['Z', 'C', 'V', 'DZ'])
    return t


def build():
    if not BLOCKS:
        for g in (gen_ksa8, gen_addsub8, gen_logic8, gen_dec_op, gen_outmux, gen_flags, gen_alu_core):
            g()
    return BLOCKS


# ---------------------------------------------------------------- tham chieu + kiem tra
def bits(v, w):
    return [(v >> i) & 1 for i in range(w)]


def val(bs):
    return sum(b << i for i, b in enumerate(bs))


def ksa_ref(a, b, cin):
    s = a + b + cin
    return s & 0xFF, ((a & 0x7F) + (b & 0x7F) + cin) >> 7, s >> 8


def core_ref(op, a, b, mulp, divq, divr, divv, divdz):
    """Ham cua ALU_CORE (doc lap voi model/alu_ref.py). Tra ve y, z, c, v, dz."""
    c = v = dz = 0
    if op in (0, 1):
        bb = b ^ (0xFF if op else 0)
        y, c7, c = ksa_ref(a, bb, op)
        v = c7 ^ c
    elif op == 2: y = a & b
    elif op == 3: y = a | b
    elif op == 4: y = a ^ b
    elif op == 5: y = ~a & 0xFF
    elif op == 9: y = mulp
    elif op == 11: y, v, dz = (divr << 8) | divq, divv, divdz
    else: y = 0
    return y, int(y == 0), c, v, dz


def run_core(t, op, a, b, mulp, divq, divr, divv, divdz):
    o = t.call(bits(a, 8) + bits(b, 8) + bits(op, 4) + bits(mulp, 16) + bits(divq, 8) + bits(divr, 8) + [divv, divdz])
    return val(o[:16]), o[16], o[17], o[18], o[19]


def check():
    B = build()
    k = B['KSA8']
    for a in range(256):
        for b in range(256):
            for cin in (0, 1):
                o = k.call(bits(a, 8) + bits(b, 8) + [cin])
                assert (val(o[:8]), o[8], o[9]) == ksa_ref(a, b, cin), (a, b, cin, o)
    print('KSA8: 131072/131072 to hop dung')
    t, rnd = B['ALU_CORE'], random.Random(1)
    n = 0
    for op in range(16):
        for _ in range(400):
            args = (op, rnd.randrange(256), rnd.randrange(256), rnd.randrange(65536),
                    rnd.randrange(256), rnd.randrange(256), rnd.randrange(2), rnd.randrange(2))
            assert run_core(t, *args) == core_ref(*args), (args, run_core(t, *args))
            n += 1
    print(f'ALU_CORE: {n}/{n} vector ngau nhien dung (16 ma OP)')
    csv = REPO / 'vectors' / 'alu_core.csv'
    if csv.exists():
        import csv as _csv
        bad = tot = 0
        for r in _csv.DictReader(csv.open()):
            g = {key: int(r[key]) for key in ('op', 'a', 'b', 'mulp', 'divq', 'divr', 'divv', 'divdz')}
            got = run_core(t, **g)
            exp = [r[c] for c in ('y', 'z', 'c', 'v', 'dz')]
            tot += 1
            if any(e != '' and int(e) != x for e, x in zip(exp, got)):
                bad += 1
                if bad <= 10:
                    print('  lech so voi vectors/alu_core.csv:', dict(r), '-> netlist', got)
        print(f'vectors/alu_core.csv: {tot - bad}/{tot} dung (muc logic)')
    else:
        print('(chua co vectors/alu_core.csv)')


# ---------------------------------------------------------------- dem transistor
def parse_subckts(paths):
    """{subckt: [master,...]} tu cac file Spectre (bo qua dong chu thich, noi dong '\\')."""
    subs, cur = {}, None
    for p in paths:
        text = re.sub(r'\\\s*\n', ' ', (REPO / p).read_text())
        for line in text.splitlines():
            line = line.split('//')[0].strip()
            if not line or line.startswith('*'):
                continue
            w = line.split()
            if w[0] in ('subckt', 'inline') and 'subckt' in w[:2]:
                cur = w[w.index('subckt') + 1]
                subs[cur] = []
            elif w[0] == 'ends':
                cur = None
            elif cur and ')' in line:
                after = line.split(')', 1)[1].split()
                if after:
                    subs[cur].append(after[0])
    return subs


def count():
    build()
    subs = parse_subckts(CELL_FILES + [b.path for b in BLOCKS.values()])

    def n(m):
        if re.fullmatch(r'(gpdk090_)?[np]mos1v(_hvt)?', m):
            return 1
        return sum(n(x) for x in subs[m])
    for name in list(FUNC) + list(BLOCKS):
        print(f'{name:10s} {n(name):5d}')


def main():
    if '--check' in sys.argv:
        return check()
    if '--count' in sys.argv:
        return count()
    for b in build().values():
        p = REPO / b.path
        p.parent.mkdir(parents=True, exist_ok=True)
        hdr = (f'// {b.name}: sinh tu dong boi blocks/gen_blocks.py - khong sua tay\n'
               f'// Can include cac cell A + stub XOR2/XNOR2 va cac khoi con truoc khi dung.\n'
               'simulator lang=spectre\n')
        p.write_text(hdr + b.scs(), encoding='ascii', newline='\n')
        print('ghi', b.path, len(b.insts), 'instance')


if __name__ == '__main__':
    main()
