#!/usr/bin/env python3
"""ALU N bit (N chan, mac dinh 32) - cung kien truc voi ALU 8 bit de so sanh. Chay tren Windows.

    python alu32/gen_alun.py            # ghi alu32/netlist/*.scs + alu32/tb/*
    python alu32/gen_alun.py --check    # muc logic: N=4 quet het, N=8 MUL/DIV quet het, N=32 bien + ngau nhien
    python alu32/gen_alun.py --count    # transistor + do sau cell, 8 bit (ALU_TOPK) va 32 bit
    python alu32/gen_alun.py --res MUL32 out/MUL32_p0_NN 0     # so ket qua Spectre (psfascii) phan 0

Kien truc (nhu docs/KE_HOACH_ALU.md, tham so hoa theo N):
  KSA<w>   Kogge-Stone xen ke cuc tinh (cell BLK/GRY cua A), w bat ky
  CORE<N>  ADDSUB + LOGIC + DEC_OP (dung lai ban 8 bit) + OUTMUX + FLAGS, Y rong 2N
  MUL<N>   Booth co so 4 (N/2 hang) + cay nen 4:2 (CMP42/FA/HA) + KSA cuoi
  DIV<N>   mang non-restoring N hang, moi hang 1 KSA<N> (nhu DIV8K) + boc dau
Khac ban 8 bit: net co > LIM tai duoc chen cay dem INV_X4 (buffer()); bo cong cuoi cua MUL la
KSA tren moi cot cao 2 (ban 8 bit: ripple 8 cot thap + KSA8).
Dung lai Block/FUNC (blocks/gen_blocks.py), cell B/C (gen_mul.py), tb + so ket qua (gen_div.py).
"""
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path[:0] = [str(REPO / 'blocks' / 'ALU_DIV'), str(REPO / 'blocks' / 'ALU_MUL'), str(REPO / 'blocks'), str(REPO)]
import gen_blocks as gb  # noqa: E402
import gen_div  # noqa: E402
import gen_mul  # noqa: E402  (dang ky FUNC cua FA/HA/BOOTH/CMP42)
from gen_blocks import BLOCKS, bits, bus, val  # noqa: E402

LIM, PER = 12, 6      # net > LIM chan tai -> cay INV_X4, moi la keo <= PER chan
SELS = gb.SELS


def blk(name, ins, outs):
    return gen_div.TieBlock(name, f'alu32/netlist/{name}.scs', ins, outs)


def rename(b, old, new):
    b.insts = [(m, [new if n == old else n for n in i], [new if n == old else n for n in o]) for m, i, o in b.insts]


def buffer(b):
    """Chen cay INV_X4 (so tang chan -> giu cuc tinh) cho moi net co > LIM chan tai trong khoi b."""
    sinks = {}
    for k, (_, i, _) in enumerate(b.insts):
        for p, n in enumerate(i):
            if n not in ('VDD', 'VSS'):
                sinks.setdefault(n, []).append((k, p))
    drv = {n: k for k, (_, _, o) in enumerate(b.insts) for n in o}
    add = {}
    for n, sk in sinks.items():
        if len(sk) <= LIM:
            continue
        g = -(-len(sk) // PER)
        lv = [g]
        while lv[-1] > 1:
            lv.append(-(-lv[-1] // 4))
        new, src = [], [n]
        if len(lv) % 2:                                  # le tang -> them INV_X1 dau (tai nhe cho nguon)
            new.append(('INV_X1', [n], [f'{n}_b0']))
            src = [f'{n}_b0']
        for d, cnt in enumerate(reversed(lv)):
            outs = [f'{n}_b{d + 1}_{c}' for c in range(cnt)]
            new += [('INV_X4', [src[c * len(src) // cnt]], [outs[c]]) for c in range(cnt)]
            src = outs
        for q, (k, p) in enumerate(sk):
            b.insts[k][1][p] = src[q * g // len(sk)]
        add.setdefault(drv.get(n, -1), []).extend(new)   # ngay sau cell lai -> giu thu tu topo
    b.insts = [x for k in range(-1, len(b.insts)) for x in ([b.insts[k]] if k >= 0 else []) + add.get(k, [])]
    return b


def all_zero(b, nets, tag):
    """Net = 1 khi moi net vao = 0: cay NOR2/NAND2 xen ke."""
    cur, pol, lvl = list(nets), 0, 0                     # pol 0: 1 = khac 0; pol 1: 1 = bang 0
    while len(cur) > 1:
        g = 'NAND2_X1' if pol else 'NOR2_X1'
        nxt = [b.x(g, cur[i:i + 2], f'{tag}{lvl}_{i // 2}') for i in range(0, len(cur) - 1, 2)]
        if len(cur) % 2:
            nxt.append(b.x('INV_X1', [cur[-1]], f'{tag}{lvl}_x'))
        cur, pol, lvl = nxt, pol ^ 1, lvl + 1
    return cur[0] if pol else b.x('INV_X1', cur, f'{tag}z')


# ---------------------------------------------------------------- KSA
def gen_ksa(w):
    """Kogge-Stone w bit (gen_blocks.gen_ksa8 tong quat). Ra S, CM = nho vao bit cao nhat, CO = nho ra."""
    name = f'KSA{w}'
    if name in BLOCKS:
        return BLOCKS[name]
    A, B, S = bus('A', w), bus('B', w), bus('S', w)
    k = blk(name, A + B + ['CIN'], S + ['CM', 'CO'])
    gn = [k.x('NAND2_X1', [A[i], B[i]], f'gn{i}') for i in range(w)]
    pn = [k.x('XNOR2_X1', [A[i], B[i]], f'pn{i}') for i in range(w)]
    k.x('INV_X1', ['CIN'], 'cinn')
    k.x('GRY_N', [gn[0], pn[0], 'cinn'], 'G0_0')
    cur = {i: (gn[i], pn[i], i) for i in range(1, w)}    # nhom chua xong: (G, P, bit thap)
    fin, orig = {0: {1: 'G0_0'}}, {0: 1}                 # bit da xong: {cuc: net}, cuc goc

    def need(j, pol):
        if pol not in fin[j]:
            src = fin[j][1 - pol]
            fin[j][pol] = k.x('INV_X1', [src], src + ('n' if pol == 0 else 'p'))
        return fin[j][pol]

    lvl, d = 0, 1
    while cur:
        lvl += 1
        want = 0 if lvl % 2 else 1                       # tang le: cell _N (vao tich cuc thap)
        suf, sfx = ('_N', '') if want == 0 else ('_P', 'n')
        nxt, done = {}, set(fin)
        for i in sorted(cur):
            gi, pi, _ = cur[i]
            j = i - d
            if j in done:
                fin[i] = {1 - want: k.x('GRY' + suf, [gi, pi, need(j, want)], f'G{i}_0{sfx}')}
                orig[i] = 1 - want
            else:
                gj, pj, loj = cur[j]
                g, p = k.x('BLK' + suf, [gi, pi, gj, pj], [f'G{i}_{loj}{sfx}', f'P{i}_{loj}{sfx}'])
                nxt[i] = (g, p, loj)
        cur, d = nxt, d * 2
    for i in range(w):
        c, cp = ('CIN', 1) if i == 0 else (fin[i - 1][orig[i - 1]], orig[i - 1])
        k.x('XNOR2_X1' if cp == 1 else 'XOR2_X1', [pn[i], c], S[i])
    for pin, j in (('CM', w - 2), ('CO', w - 1)):
        if j < 0:
            k.x('INV_X1', ['cinn'], pin)                 # w = 1: nho vao bit cao nhat = CIN
        else:
            rename(k, need(j, 1), pin)
    return buffer(k)


# ---------------------------------------------------------------- CORE
def gen_core(N):
    name = f'CORE{N}'
    if name in BLOCKS:
        return BLOCKS[name]
    ks = gen_ksa(N)
    dec = BLOCKS.get('DEC_OP') or gb.gen_dec_op()
    A, B, S, Y = bus('A', N), bus('B', N), bus('S', N), bus('Y', 2 * N)
    lg = bus('AND', N) + bus('OR', N) + bus('XOR', N) + bus('NOT', N)
    mdv = bus('MULP', 2 * N) + bus('DIVQ', N) + bus('DIVR', N)

    a = blk(f'ADDSUB{N}', A + B + ['SUB'], S + ['CM', 'CO'])
    bx = [a.x('XOR2_X1', [B[i], 'SUB'], f'bx{i}') for i in range(N)]
    a.x(ks.name, A + bx + ['SUB'], S + ['CM', 'CO'])
    buffer(a)

    g = blk(f'LOGIC{N}', A + B, lg)
    for i in range(N):
        g.x('INV_X1', [g.x('NAND2_X1', [A[i], B[i]], f'nand{i}')], f'AND_{i}')
        g.x('INV_X1', [g.x('NOR2_X1', [A[i], B[i]], f'nor{i}')], f'OR_{i}')
        g.x('XOR2_X1', [A[i], B[i]], f'XOR_{i}')
        g.x('INV_X1', [A[i]], f'NOT_{i}')

    m = blk(f'OUTMUX{N}', S + lg + mdv + SELS, Y)        # nhu gen_blocks.gen_outmux
    for i in range(N):
        pairs = [('SEL_AND', f'AND_{i}'), ('SEL_OR', f'OR_{i}'), ('SEL_XOR', f'XOR_{i}'),
                 ('SEL_NOT', f'NOT_{i}'), ('SEL_MUL', f'MULP_{i}'), ('SEL_DIV', f'DIVQ_{i}')]
        n = [m.x('NAND2_X1', [s, x], f'n{i}_{k}') for k, (s, x) in enumerate(pairs)]
        o = [m.x('NAND2_X1', [n[2 * k], n[2 * k + 1]], f'o{i}_{k}') for k in range(3)]
        q1 = m.x('NOR2_X1', [o[0], o[1]], f'q{i}_1')
        q2 = m.x('AOI21_X1', ['SEL_AS', f'S_{i}', o[2]], f'q{i}_2')
        m.x('NAND2_X1', [q1, q2], f'Y_{i}')
    for i in range(N, 2 * N):
        x = m.x('NAND2_X1', ['SEL_MUL', f'MULP_{i}'], f'hm{i}')
        y = m.x('NAND2_X1', ['SEL_DIV', f'DIVR_{i - N}'], f'hd{i}')
        m.x('NAND2_X1', [x, y], f'Y_{i}')
    buffer(m)

    fl = ['CM', 'CO', 'DIVV', 'DIVDZ', 'SEL_AS', 'SEL_DIV']
    f = blk(f'FLAGS{N}', Y + fl, ['Z', 'C', 'V', 'DZ'])
    rename(f, all_zero(f, Y, 'z'), 'Z')
    f.x('INV_X1', [f.x('NAND2_X1', ['CO', 'SEL_AS'], 'cn')], 'C')
    x = f.x('XOR2_X1', ['CM', 'CO'], 'ovf')
    f.x('NAND2_X1', [f.x('NAND2_X1', ['SEL_AS', x], 'v1'), f.x('NAND2_X1', ['SEL_DIV', 'DIVV'], 'v2')], 'V')
    f.x('INV_X1', [f.x('NAND2_X1', ['SEL_DIV', 'DIVDZ'], 'dzn')], 'DZ')

    t = blk(name, A + B + bus('OP', 4) + mdv + ['DIVV', 'DIVDZ'], Y + ['Z', 'C', 'V', 'DZ'])
    t.x(dec.name, bus('OP', 4), SELS)
    t.x(a.name, A + B + ['OP_0'], S + ['CM', 'CO'])
    t.x(g.name, A + B, lg)
    t.x(m.name, S + lg + mdv + SELS, Y)
    t.x(f.name, Y + fl, ['Z', 'C', 'V', 'DZ'])
    return t


# ---------------------------------------------------------------- MUL
def reduce_stage(cols, cell):
    """Mot tang nen: CMP42 (5 bit -> S + C + CO; CO chi noi vao chan CI cot ke ben, khong lan truyen
    ngang), con lai FA; HA chi dung o tang cuoi (cao <= 3) de dua ve 2 hang."""
    W, last = len(cols), max(map(len, cols)) <= 3
    out, cis = [[] for _ in range(W + 1)], []
    for j in range(W):
        L, nxt = list(cols[j]), []
        while len(L) >= 5 or (len(L) == 4 and cis):
            x, L = L[:4], L[4:]
            ci = cis.pop(0) if cis else (L.pop(0) if L else 'VSS')
            s, c, co = cell('CMP42', x + [ci], 3)
            out[j].append(s); out[j + 1].append(c); nxt.append(co)
        L += cis                                         # CO thua: bit thuong cua cot j
        while len(L) >= 3 and len(L) + len(out[j]) > 2:
            s, c = cell('FA_X1', L[:3], 2)
            L = L[3:]; out[j].append(s); out[j + 1].append(c)
        if last and len(L) == 2 and out[j]:
            s, c = cell('HA_X1', L, 2)
            L = []; out[j].append(s); out[j + 1].append(c)
        out[j] += L
        cis = nxt
    return out[:W]                                       # cot W tro len: bo (mod 2^W)


def gen_muln(N):
    """Nhan co dau N x N -> 2N: hang Booth nhu model/alu_ref.booth_pp_rows, tong quat theo N."""
    name = f'MUL{N}'
    if name in BLOCKS:
        return BLOCKS[name]
    A, B, P, W = bus('A', N), bus('B', N), bus('P', 2 * N), 2 * N
    m = blk(name, A + B, P)
    cols = [[] for _ in range(W)]

    def put(j, n):
        if j < W:
            cols[j].append(n)

    aj = lambda j: 'VSS' if j < 0 else A[min(j, N - 1)]
    for i in range(N // 2):
        one, two = m.x('BOOTH_ENC', [B[2 * i + 1], B[2 * i], B[2 * i - 1] if i else 'VSS'], [f'one{i}', f'two{i}'])
        pp = [m.x('BOOTH_SEL', [aj(j), aj(j - 1), one, two, B[2 * i + 1]], f'pp{i}_{j}') for j in range(N + 1)]
        sn = m.x('INV_X1', [pp[N]], f'sn{i}')
        if i:
            put(2 * i - 2, B[2 * i - 1])                 # neg_(i-1)
        for k, n in enumerate(pp + ([pp[N], pp[N], sn] if i == 0 else [sn, 'VDD'])):
            put(2 * i + k, n)
    put(N - 2, B[N - 1])                                 # neg cua hang cuoi
    nid = [0]

    def cell(master, ins, nout):
        nid[0] += 1
        return m.x(master, ins, [f'{master[:2].lower()}{nid[0]}_{k}' for k in range(nout)])

    m.heights = [[len(c) for c in cols]]
    while max(map(len, cols)) > 2:
        cols = reduce_stage(cols, cell)
        m.heights.append([len(c) for c in cols])
        assert len(m.heights) < 12, m.heights
    j0 = next((j for j in range(W) if len(cols[j]) == 2), W)
    for j in range(j0):
        (n,) = cols[j]
        assert n not in A + B + ['VDD', 'VSS'], (j, n)
        rename(m, n, P[j])
    if j0 < W:
        hi = [c + ['VSS'] * (2 - len(c)) for c in cols[j0:]]
        m.x(gen_ksa(W - j0).name, [h[0] for h in hi] + [h[1] for h in hi] + ['VSS'], P[j0:] + ['kcm', 'kco'])
    return buffer(m)


# ---------------------------------------------------------------- DIV
def neg(b, xs, s, outs, tag):
    """Dao dau co dieu kien (gen_div.neg tong quat): outs = (xs ^ s) + s; outs[0] phai la xs[0]."""
    assert outs[0] == xs[0]
    kn = b.x('NAND2_X1', [s, xs[0]], f'{tag}kn1')
    for i in range(1, len(xs)):
        b.x('XNOR2_X1', [xs[i], kn], outs[i])
        if i < len(xs) - 1:
            kn = b.x('AOI21_X1', [s, xs[i], b.x('INV_X1', [kn], f'{tag}k{i}')], f'{tag}kn{i + 1}')
    return outs


def gen_divn(N):
    """Chia co dau N bit: gen_div.gen_div8('ksa') tong quat (moi hang 1 KSA<N>)."""
    name = f'DIV{N}'
    if name in BLOCKS:
        return BLOCKS[name]
    ks = gen_ksa(N).name
    A, B, Q, R = bus('A', N), bus('B', N), bus('Q', N), bus('R', N)
    d = blk(name, A + B, Q + R + ['V', 'DZ'])
    sA, sB = A[N - 1], B[N - 1]
    aa = neg(d, A, sA, [A[0]] + [f'aa{i}' for i in range(1, N)], 'na')
    dd = neg(d, B, sB, [B[0]] + [f'dd{i}' for i in range(1, N)], 'nb')
    P, t, qu = ['VSS'] * (N + 1), 'VDD', [None] * N
    for i in range(N):
        x = [aa[N - 1 - i]] + P[:N]                      # 2P + a, N+1 bit
        b = [d.x('XOR2_X1', [dd[j], t], f'b{i}_{j}') for j in range(N)]
        o = d.x(ks, x[:N] + b + [t], [f'p{i}_{j}' for j in range(N)] + [f'c{i}_m', f'c{i}_o'])
        h = d.x('XOR2_X1', [x[N], t], f'h{i}')
        P = list(o[:N]) + [d.x('XOR2_X1', [h, o[N + 1]], f'p{i}_{N}')]
        t = qu[N - 1 - i] = d.x('INV_X1' if i == N - 1 else 'INV_X4', [P[N]], 'Q_0' if i == N - 1 else f'qu{N - 1 - i}')
    dms = [d.x('INV_X1', [d.x('NAND2_X1', [dd[j], P[N]], f'dmn{j}')], f'dm{j}') for j in range(N)]
    ru = list(d.x(ks, P[:N] + dms + ['VSS'], ['R_0'] + [f'ru{j}' for j in range(1, N)] + ['rcm', 'rco'])[:N])
    sq = d.x('XOR2_X1', [sA, sB], 'sq')
    neg(d, qu, sq, Q, 'nq')
    neg(d, ru, sA, R, 'nr')
    rename(d, all_zero(d, B, 'z'), 'DZ')
    d.x('NOR2_X1', [d.x('NAND2_X1', [Q[N - 1], d.x('INV_X1', [sq], 'sqn')], 'vn'), 'DZ'], 'V')
    return buffer(d)


def gen_top(N):
    name = f'ALU{N}'
    if name in BLOCKS:
        return BLOCKS[name]
    mu, dv, co = gen_muln(N), gen_divn(N), gen_core(N)
    A, B, OP = bus('A', N), bus('B', N), bus('OP', 4)
    mdv = bus('MULP', 2 * N) + bus('DIVQ', N) + bus('DIVR', N) + ['DIVV', 'DIVDZ']
    t = blk(name, A + B + OP, bus('Y', 2 * N) + ['Z', 'C', 'V', 'DZ'])
    t.x(mu.name, A + B, mdv[:2 * N])
    t.x(dv.name, A + B, mdv[2 * N:])
    t.x(co.name, A + B + OP + mdv, t.outs)
    return t


# ---------------------------------------------------------------- tham chieu + kiem tra
def sgn(N, x):
    return x - (1 << N) if x >> (N - 1) else x


def ref(N, op, a, b, mulp=0, divq=0, divr=0, divv=0, divdz=0):
    """Mo hinh vang N bit cua CORE, doc lap voi netlist. Tra ve y, z, c, v, dz."""
    M = (1 << N) - 1
    c = v = dz = 0
    if op in (0, 1):
        bb = b ^ (M if op else 0)
        s = a + bb + op
        y, c = s & M, s >> N
        v = (((a & (M >> 1)) + (bb & (M >> 1)) + op) >> (N - 1)) ^ c
    elif op == 2: y = a & b
    elif op == 3: y = a | b
    elif op == 4: y = a ^ b
    elif op == 5: y = ~a & M
    elif op == 9: y = mulp
    elif op == 11: y, v, dz = (divr << N) | divq, divv, divdz
    else: y = 0
    return y, int(y == 0), c, v, dz


def mul_ref(N, a, b):
    return (sgn(N, a) * sgn(N, b)) & ((1 << 2 * N) - 1)


def div_ref(N, a, b):
    """(q, r, v, dz); q = r = None khi b = 0. Cat ve 0, du cung dau A; MIN / -1: v = 1, q = MIN, r = 0."""
    M = (1 << N) - 1
    if b == 0:
        return None, None, 0, 1
    q, r = divmod(abs(sgn(N, a)), abs(sgn(N, b)))
    if (sgn(N, a) < 0) != (sgn(N, b) < 0):
        q = -q
    if sgn(N, a) < 0:
        r = -r
    return q & M, r & M, int(a == 1 << (N - 1) and b == M), 0


def top_ref(N, op, a, b):
    """y = z = None (tuy y) khi chia 0."""
    if op == 9:
        return ref(N, op, a, b, mulp=mul_ref(N, a, b))
    if op == 11:
        q, r, v, dz = div_ref(N, a, b)
        return (None, None, 0, 0, 1) if dz else ref(N, op, a, b, divq=q, divr=r, divv=v)
    return ref(N, op, a, b)


def run_top(N, op, a, b):
    o = BLOCKS[f'ALU{N}'].call(bits(a, N) + bits(b, N) + bits(op, 4))
    return (val(o[:2 * N]), *o[2 * N:])


def run_mul(N, a, b):
    return val(BLOCKS[f'MUL{N}'].call(bits(a, N) + bits(b, N)))


def run_div(N, a, b):
    o = BLOCKS[f'DIV{N}'].call(bits(a, N) + bits(b, N))
    return val(o[:N]), val(o[N:2 * N]), o[2 * N], o[2 * N + 1]


def same(got, exp):
    return all(e is None or e == g for g, e in zip(got, exp))


def edges(N):
    M = (1 << N) - 1
    return [0, 1, 2, M, M - 1, 1 << (N - 1), (1 << (N - 1)) + 1, M >> 1, (M >> 1) - 1, M // 3, M - M // 3]


def check():
    gen_top(4)
    n = 0
    for op in range(16):
        for a in range(16):
            for b in range(16):
                assert same(run_top(4, op, a, b), top_ref(4, op, a, b)), (op, a, b, run_top(4, op, a, b))
                n += 1
    print(f'ALU4: {n}/{n} to hop (16 ma OP, quet het)')
    gen_top(8)
    for a in range(256):
        for b in range(256):
            assert run_mul(8, a, b) == mul_ref(8, a, b), (a, b)
            assert same(run_div(8, a, b), div_ref(8, a, b)), (a, b, run_div(8, a, b))
    print('MUL8 / DIV8 (bo sinh tong quat): 65536/65536 cap (a, b) moi khoi')
    rnd = random.Random(32)
    for N, per_op in ((8, 300), (32, 150)):
        gen_top(N)
        E = edges(N)
        V = [(a, b) for a in E for b in E] + [(rnd.getrandbits(N), rnd.getrandbits(N)) for _ in range(per_op)] + \
            [(rnd.getrandbits(N), rnd.getrandbits(rnd.randrange(1, N))) for _ in range(per_op // 3)]   # so chia nho
        n = 0
        for op in (0, 1, 2, 3, 4, 5, 9, 11, 6, 15):
            for a, b in V if op in (0, 1, 9, 11) else V[::4]:
                got = run_top(N, op, a, b)
                assert same(got, top_ref(N, op, a, b)), (N, op, hex(a), hex(b), got)
                n += 1
        print(f'ALU{N}: {n}/{n} vector (bien x bien + ngau nhien, 8 phep + 2 ma du tru)')
    return 0


# ---------------------------------------------------------------- dem transistor / do sau
def cell_t():
    subs = gb.parse_subckts(gb.CELL_FILES + [c.path for c in gen_mul.make_cells()])
    n = lambda m: 1 if m.startswith('gpdk090_') else sum(n(x) for x in subs[m])
    return {c: n(c) for c in subs}


def ntrans(b, ct):
    return sum(ct[m] if m in ct else ntrans(BLOCKS[m], ct) for m, _, _ in b.insts)


def depth(b, din):
    """So tang cell tu ngo vao den moi ngo ra (khoi con duoc mo). CMP42 = 2 tang FA; CO cua no
    chi phu thuoc X1..X3 (gen_mul.depth tinh ca CI -> ao giac lan truyen ngang)."""
    d = dict(din)
    for m, i, o in b.insts:
        di = [d.get(n, 0) for n in i]
        if m in BLOCKS:
            d.update(zip(o, depth(BLOCKS[m], dict(zip(BLOCKS[m].ins, di)))))
        elif m == 'CMP42':
            s1 = max(di[:3]) + 1
            d.update(zip(o, (max(s1, di[3], di[4]) + 1,) * 2 + (s1,)))
        else:
            d.update((x, max(di) + 1) for x in o)
    return [d[x] for x in b.outs]


def count():
    ct = cell_t()
    gb.build()                                           # ban 8 bit goc
    gen_div.build()
    gen_div.gen_div8('ksa')
    gen_mul.gen_mul8().__class__ = gen_div.TieBlock
    t8 = gb.Block('ALU_TOPK', '', bus('A', 8) + bus('B', 8) + bus('OP', 4), bus('Y', 16) + ['Z', 'C', 'V', 'DZ'])
    mdv = bus('MULP', 16) + bus('DIVQ', 8) + bus('DIVR', 8) + ['DIVV', 'DIVDZ']
    t8.x('MUL8', t8.ins[:16], mdv[:16])
    t8.x('DIV8K', t8.ins[:16], mdv[16:])
    t8.x('ALU_CORE', t8.ins + mdv, t8.outs)
    gen_top(32)
    print(f'{"khoi":16s} {"T 8b":>7s} {"T 32b":>8s} {"x":>5s}   {"sau 8b":>6s} {"sau 32b":>7s}')
    for a, b in (('KSA8', 'KSA32'), ('ALU_CORE', 'CORE32'), ('MUL8', 'MUL32'), ('DIV8K', 'DIV32'), ('ALU_TOPK', 'ALU32')):
        x, y = BLOCKS[a], BLOCKS[b]
        tx, ty = ntrans(x, ct), ntrans(y, ct)
        print(f'{a + "/" + b:16s} {tx:7d} {ty:8d} {ty / tx:5.1f}   '
              f'{max(depth(x, {})):6d} {max(depth(y, {})):7d}')
    m = BLOCKS['MUL32']
    print('MUL32 chieu cao cot lon nhat qua cac tang nen:', [max(h) for h in m.heights])
    nb = sum(mm == 'INV_X4' for bb in BLOCKS.values() if bb.path.startswith('alu32/') for mm, _, _ in bb.insts)
    print('INV_X4 trong cac khoi alu32 (dem moi khoi 1 lan):', nb)
    return 0


# ---------------------------------------------------------------- Spectre
def deps(b, seen):
    for m, _, _ in b.insts:
        if m in BLOCKS and BLOCKS[m].path not in seen:
            deps(BLOCKS[m], seen)
    if b.path not in seen:
        seen.append(b.path)
    return seen


def tb_set(N):
    """top -> (T_ns NN, T_ns SS, maxstep, vector moi phan, cac dong). Vector dau moi phan = trang thai dau."""
    M, MIN, MAX = (1 << N) - 1, 1 << (N - 1), (1 << (N - 1)) - 1
    rnd = random.Random(N)
    core = [(0, M, 0), (0, M, 1), (1, 0, 0), (1, 0, 1), (0, MAX, 1), (2, M // 3, M), (3, M // 3, MIN),
            (4, M // 3, M), (5, M // 3, 0), (0, rnd.getrandbits(N), rnd.getrandbits(N))]
    mul = [(0, 0), (M, M), (MIN, MIN), (MIN, MAX), (MAX, MAX), (M // 3, M - M // 3),
           (rnd.getrandbits(N), rnd.getrandbits(N)), (0, 0), (rnd.getrandbits(N), rnd.getrandbits(N))]
    div = [(0, 1), (MIN, M), (MAX, 1), (MIN, 1), (5, 0), (M - 6, 2), (MAX, 3), (rnd.getrandbits(N), 7)]
    return {
        f'CORE{N}': (3 * N / 32 + 1, 6 * N / 32 + 1, '20p', 10,
                     [dict(zip('op a b mulp divq divr divv divdz y z c v dz'.split(),
                               (o, a, b, 0, 0, 0, 0, 0) + ref(N, o, a, b))) for o, a, b in core]),
        f'MUL{N}': (6 * N / 32 + 1, 9 * N / 32 + 1, '20p', 3,
                    [{'a': a, 'b': b, 'p': mul_ref(N, a, b)} for a, b in mul]),
        # skipdc: diem lam viec DC cua DIV32 (86 nghin T) khong hoi tu sau 25 phut (gmin, source, dptran)
        f'DIV{N}': (40 * N / 32, 60 * N / 32, '50p skipdc=yes', 2,
                    [dict(zip('a b q r v dz'.split(), (a, b) + tuple(-1 if x is None else x for x in div_ref(N, a, b))))
                     for a, b in div])}


def write_tb(N):
    out = HERE / 'tb'
    out.mkdir(parents=True, exist_ok=True)
    cells = ['cells/A/cells_A.scs'] + [c for c in gb.CELL_FILES if '_stub_B' in c] + [c.path for c in gen_mul.make_cells()]
    for top, (T, Ts, ms, per, rows) in tb_set(N).items():
        incs = cells + deps(BLOCKS[top], [])
        for k in range(0, len(rows), per):
            tag = f'{top}_p{k // per}'
            gen_div.write_tb_body(out / f'tb_{tag}.scs', top, rows[k:k + per], T, ms)
            gen_div.write_tb_body(out / f'tb_{tag}_slow.scs', top, rows[k:k + per], Ts, ms)
            for cn in ('NN', 'SS', 'FF'):
                body = f'tb_{tag}_slow.scs' if cn == 'SS' else f'tb_{tag}.scs'
                (out / f'tb_{tag}_{cn}.scs').write_text('\n'.join(
                    [f'// {top} corner {cn}', 'simulator lang=spectre', f'include "{gen_div.MODEL}" section={cn}'] +
                    [f'include "../../{p}"' for p in incs] + [f'include "{body}"']) + '\n', encoding='ascii', newline='\n')
        print(f'ghi alu32/tb/tb_{top}_p*.scs: {len(rows)} vector, {per}/phan, T = {T:g} ns (SS {Ts:g} ns)')


def result(N, top, path, part):
    gen_top(N)
    T, Ts, _, per, rows = tb_set(N)[top]
    gen_div.T_SS = Ts                                    # check_res doi chu ky khi thu muc ket thuc _SS
    return gen_div.check_res(top, rows[part * per:(part + 1) * per], Path(path), T)


def main():
    N = int(sys.argv[sys.argv.index('--n') + 1]) if '--n' in sys.argv else 32
    if '--check' in sys.argv:
        return check()
    if '--count' in sys.argv:
        return count()
    if '--res' in sys.argv:
        k = sys.argv.index('--res')
        return result(N, sys.argv[k + 1], sys.argv[k + 2], int(sys.argv[k + 3]))
    t = gen_top(N)
    for p in deps(t, []):
        if p.startswith('alu32/'):
            b = next(x for x in BLOCKS.values() if x.path == p)
            (REPO / p).parent.mkdir(parents=True, exist_ok=True)
            (REPO / p).write_text(f'// {b.name}: sinh tu dong boi alu32/gen_alun.py - khong sua tay\n'
                                  'simulator lang=spectre\n' + b.scs(), encoding='ascii', newline='\n')
            print('ghi', p, len(b.insts), 'instance')
    write_tb(N)
    return 0


if __name__ == '__main__':
    sys.exit(main())
