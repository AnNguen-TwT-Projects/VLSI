#!/usr/bin/env python3
"""Layout cell B/C/D tu netlist .scs -> layout/gen_layout_BCD.il (SKILL ve hinh), chay tren Windows.

    python layout/gen_layout_cells.py              # ghi layout/gen_layout_BCD.il
    python layout/gen_layout_cells.py FA_X1 -v     # chi mot cell, in so do ASCII (khong ghi file)

Cung khuon voi cell A (layout/gen_layout_A.il, docs/handoff_layout_A.md): cao 2.76, buoc cot 0.27,
cot chan = nut khuech tan, cot le = cong; hang n tam 0.64, hang p tam 2.00; ray VSS/VDD Metal1.
Khac cell A: day noi tu dong.
  1. Phang hoa netlist (CAS_X1 -> NAND2 + XOR2), chia finger: n > 0.24 um, p > 0.48 um
     (n rong hon thi dau poly cach oxide tap VSS < 0.10; Assura LVS gop MOS song song).
  2. Moi hang (n, p) = do thi nut-transistor; tim vet Euler ngau nhien, roi can hai hang bang quy hoach
     dong de cot cong chung poly (cung tin hieu), hang con lai "PASS" (oxide noi tiep, poly chi o hang kia)
     hoac "B" (dut khuech tan).
  3. Noi day: moi net M1 doc tren cot cua no, M2 ngang tren 7 track (y 0.50..2.24, buoc 0.29), Via1 o
     giao diem; cac cot ke nhau cung net noi bang cau M1 (Via1 cach nhau >= 0.15 nen khong dat 2 via ke).
     Kiem tra DRC so bo (M1 cung cot cach >= 0.12, M2 cung track cach >= 0.14), quay lui chon track.
"""
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
from scs2skill import PRIM, collect, num  # noqa: E402

G, H = 0.27, 2.76
YN, YP, YIN = 0.64, 2.00, 1.32
TRACKS = [0.50, 0.79, 1.08, 1.37, 1.66, 1.95, 2.24]
WMAX = {'n': 0.24, 'p': 0.48}
HM = 0.075             # nua be rong M1 tren cot
LAND = 0.13            # nua chieu cao M1 bao Via1 (0.07 + 0.06)
SP1, SP2 = 0.12, 0.14  # khoang cach M1, M2
YLO, YHI = 0.36, 2.40  # M1 tin hieu tranh ray
MINLEN = 0.48          # M1 0.15 x 0.48 >= 0.07 um2
RAILS = ('VDD', 'VSS')
YC = {'n': YN, 'p': YP}

LIBS = (('ALU_CELLS_A', 'cells/A'), ('ALU_STUB_B', 'cells/_stub_B'), ('ALU_CELLS_B', 'cells/B'),
        ('ALU_CELLS_C', 'cells/C'), ('ALU_CELLS_D', 'cells/D'))
TARGETS = (('ALU_STUB_B', 'XOR2_X1'), ('ALU_STUB_B', 'XNOR2_X1'), ('ALU_CELLS_B', 'BOOTH_ENC'),
           ('ALU_CELLS_B', 'BOOTH_SEL'), ('ALU_CELLS_B', 'CMP42'), ('ALU_CELLS_C', 'FA_X1'),
           ('ALU_CELLS_C', 'HA_X1'), ('ALU_CELLS_C', 'INV_X4'), ('ALU_CELLS_D', 'CAS_X1'))


def X(k):
    return round(G * (k + 1), 4)


def load():
    cells = {}
    for lib, d in LIBS:
        cells.update(collect(f'{lib}={REPO / d}'))
    return cells


def flatten(cells, name, nmap=None, pre=''):
    c = cells[name]
    nmap = nmap or {p: p for p in c['pins']}
    out = []
    for inst, master, nodes, params in c['insts']:
        ns = [nmap.get(n, pre + n) for n in nodes]
        if master in PRIM:
            t = 'n' if 'nmos' in master else 'p'
            w = round(num(params['w']) * 1e6, 4)
            k = math.ceil(w / WMAX[t] - 1e-9)
            out += [(t, ns[0], ns[1], ns[2], round(w / k, 4))] * k
        else:
            out += flatten(cells, master, dict(zip(cells[master]['pins'], ns)), pre + inst + '.')
    return out


def trails(edges, rng):
    """Phu canh bang cac vet di ngau nhien (bat dau o nut bac le neu co)."""
    adj = defaultdict(list)
    for i, (a, b, _, _) in enumerate(edges):
        adj[a].append(i)
        adj[b].append(i)
    used, res = set(), []
    while len(used) < len(edges):
        deg = {n: sum(i not in used for i in v) for n, v in adj.items()}
        cand = [n for n, d in deg.items() if d % 2] or [n for n, d in deg.items() if d]
        cur = rng.choice(sorted(cand))
        seq = [cur]
        while True:
            opts = [i for i in adj[cur] if i not in used]
            if not opts:
                break
            i = rng.choice(opts)
            used.add(i)
            a, b, g, w = edges[i]
            cur = b if a == cur else a
            seq += [(g, w), cur]
        res.append(seq)
    return res


def row_tokens(tr, rng):
    tr = [t[::-1] if rng.random() < 0.5 else t for t in tr]
    rng.shuffle(tr)
    toks = []                                    # (kind, trai, phai, cong, w); G = transistor, B = dut
    for t in tr:
        if toks and toks[-1][2] != t[0]:
            toks.append(('B', toks[-1][2], t[0], None, 0))
        toks += [('G', t[i - 1], t[i + 1], t[i][0], t[i][1]) for i in range(1, len(t), 2)]
    return toks


def align(A, B):
    """So cot le nho nhat; cot chung chi khi hai cong cung tin hieu (hoac mot ben la B)."""
    n, m, INF = len(A), len(B), 10 ** 9
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    bk = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            v = dp[i][j]
            if v == INF:
                continue
            steps = []
            if i < n and j < m and (A[i][0] == 'B' or B[j][0] == 'B' or A[i][3] == B[j][3]):
                steps.append((i + 1, j + 1))
            if i < n:
                steps.append((i + 1, j))
            if j < m:
                steps.append((i, j + 1))
            for a, b in steps:
                if v + 1 < dp[a][b]:
                    dp[a][b], bk[a][b] = v + 1, (i, j)
    cols, i, j = [], n, m
    while (i, j) != (0, 0):
        pi, pj = bk[i][j]
        cols.append((A[pi] if pi < i else None, B[pj] if pj < j else None))
        i, j = pi, pj
    return cols[::-1]


class Cell:
    pass


def stages(devs):
    """Tang = cac transistor noi nhau qua khuech tan (khong tinh ray) ~ mot cong CMOS."""
    par = list(range(len(devs)))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    first = {}
    for i, (_, d, _, s, _) in enumerate(devs):
        for net in (d, s):
            if net in RAILS:
                continue
            if net in first:
                par[f(i)] = f(first[net])
            else:
                first[net] = i
    out = defaultdict(list)
    for i, dv in enumerate(devs):
        out[f(i)].append(dv)
    return list(out.values())


def stage_variants(st, rng, n=40, keep=6):
    """Cac cach dat mot tang: list cap (token n, token p) da can, giu cac ban ngan nhat."""
    rows = {t: [(d, s, g, w) for tt, d, g, s, w in st if tt == t] for t in 'np'}
    vs = set()
    out = []
    for _ in range(n):
        odd = align(*(row_tokens(trails(rows[t], rng), rng) for t in 'np'))
        key = tuple(odd)
        if key not in vs:
            vs.add(key)
            out.append(odd)
    return sorted(out, key=len)[:keep]


def flip(odd):
    r = lambda t: None if t is None else (t[0], t[2], t[1], t[3], t[4])  # noqa: E731
    return [(r(a), r(b)) for a, b in odd[::-1]]


def ends(odd, k):
    ts = [p[k] for p in odd if p[k] is not None]
    return ts[0][1], ts[-1][2]


def compose(svars, rng):
    """Noi cac tang theo thu tu ngau nhien; giua hai tang chen cot dut ('B') tru khi ca hai hang chung nut."""
    order = list(range(len(svars)))
    rng.shuffle(order)
    odd = []
    for s in order:
        o = rng.choice(svars[s])
        if rng.random() < 0.5:
            o = flip(o)
        if odd:
            a = [ends(odd, k)[1] for k in (0, 1)]
            b = [ends(o, k)[0] for k in (0, 1)]
            if a != b:
                odd.append(tuple(('B', a[k], b[k], None, 0) for k in (0, 1)))
        odd += o
    return odd


def place(odd):
    tok = {r: [p[k] for p in odd if p[k] is not None] for r, k in (('n', 0), ('p', 1))}
    c = Cell()
    c.ncols = 2 * len(odd) + 1
    c.item = {'n': {}, 'p': {}}                  # cot le -> ('G', cong, w) | 'B' | 'PASS' | None
    c.node = {'n': {}, 'p': {}}                  # cot chan -> net | None
    for r, k in (('n', 0), ('p', 1)):
        toks = tok[r]
        cur = toks[0][1]
        c.node[r][0] = cur
        done = 0
        for o, pair in enumerate(odd):
            col, t = 2 * o + 1, pair[k]
            if t is not None:
                c.item[r][col] = ('G', t[3], t[4]) if t[0] == 'G' else 'B'
                cur, done = t[2], done + 1
            elif done < len(toks):
                c.item[r][col] = 'PASS'          # truoc token dau / giua: oxide noi tiep
            else:
                c.item[r][col] = None            # hang da het
                cur = None
            c.node[r][col + 1] = cur
    return c


def groups(c):
    """Nhom khuech tan: cac cot chan noi nhau qua PASS. -> list (hang, [cot], net)."""
    out = []
    for r in 'np':
        cur = None
        for col in range(0, c.ncols, 2):
            net = c.node[r].get(col)
            if net is None:
                cur = None
                continue
            if cur is not None and c.item[r].get(col - 1) == 'PASS':
                cur[1].append(col)
            else:
                cur = (r, [col], net)
                out.append(cur)
    return out


def route(c, ports, rng, tries=60):
    gs = groups(c)
    gate_cols = defaultdict(list)
    for col in range(1, c.ncols, 2):
        nets = {it[1] for r in 'np' for it in [c.item[r].get(col)] if isinstance(it, tuple)}
        assert len(nets) <= 1, (col, nets)
        if nets:
            gate_cols[nets.pop()].append(col)
    ngroups = defaultdict(int)
    for _, _, net in gs:
        ngroups[net] += 1
    c.contacts, term = [], defaultdict(lambda: defaultdict(list))
    for r, cols, net in gs:
        if net in RAILS or ngroups[net] > 1 or gate_cols[net] or net in ports:
            col = cols[len(cols) // 2]
            c.contacts.append((r, col, net))
            if net not in RAILS:
                term[net][col].append((YC[r] - 0.12, YC[r] + 0.12))
    for net, cols in gate_cols.items():
        assert net not in RAILS, f'cong noi ray {net}: chua ho tro'
        for col in cols:
            term[net][col].append((YIN - 0.12, YIN + 0.12))
    c.term = term
    wcell = G * (c.ncols + 1)
    fixed = defaultdict(list)                    # cot -> [(net, lo, hi)]
    for r, col, net in c.contacts:
        if net == 'VSS':
            fixed[col].append(('VSS', -1.0, YN + 0.12))
        elif net == 'VDD':
            fixed[col].append(('VDD', YP - 0.12, H + 1.0))
    single = [n for n in term if len(term[n]) == 1]
    multi = sorted((n for n in term if len(term[n]) > 1), key=lambda n: -(max(term[n]) - min(term[n])))

    def hull(ivs):
        lo, hi = min(a for a, _ in ivs), max(b for _, b in ivs)
        if hi - lo < MINLEN:                     # dien tich M1: keo dai trong khoang cho phep
            mid = min(max((lo + hi) / 2, YLO + MINLEN / 2), YHI - MINLEN / 2)
            lo, hi = min(lo, mid - MINLEN / 2), max(hi, mid + MINLEN / 2)
        return round(lo, 4), round(hi, 4)

    def runs(cols):
        out = []
        for k in sorted(cols):
            if out and k == out[-1][-1] + 1:
                out[-1].append(k)
            else:
                out.append([k])
        return out

    def span(x1, x2):
        if x2 - x1 < 0.54:                       # dien tich M2/M3 >= 0.08 (0.15 x 0.54)
            x1, x2 = (x1 + x2) / 2 - 0.27, (x1 + x2) / 2 + 0.27
        sh = max(0.07 - x1, 0) - max(x2 - (wcell - 0.07), 0)   # cach bien cell 0.07 (ghep cell)
        return round(x1 + sh, 4), round(x2 + sh, 4)

    def plan(net, y, layer=2):
        """M1 doc tren moi cot + ngang tren track y o Metal<layer>; M3 can dem M2 + Via2 tai moi via."""
        segs = {col: hull(ivs + ([(y - LAND, y + LAND)] if y is not None else [])) for col, ivs in term[net].items()}
        rs = runs(term[net]) if y is not None else []
        vias = [r[len(r) // 2] for r in rs] if len(rs) > 1 else []
        wires = []
        if vias:
            wires.append((layer, *span(X(min(vias)) - 0.13, X(max(vias)) + 0.13)))
            if layer == 3:
                wires += [(2, *span(X(v), X(v))) for v in vias]
        return segs, [r for r in rs if len(r) > 1], vias, wires

    def ok_col(occ, col, net, lo, hi):
        if lo < YLO - 1e-9 or hi > YHI + 1e-9:
            return False
        return all(n == net or lo >= h + SP1 - 1e-9 or hi <= l - SP1 + 1e-9 for n, l, h in occ[col])

    def ok_m(mocc, y, net, wires):
        return all(n == net or x1 >= b + SP2 - 1e-9 or x2 <= a - SP2 + 1e-9
                   for L, x1, x2 in wires for n, a, b in mocc[(L, y)])

    def free(x, y, net, res):
        """Router khoi dat Via1 (dem M2 doc 0.15x0.27) + Via2 (dem M3 ngang 0.27x0.15) tai (x, y) duoc khong."""
        if x - 0.075 < 0.07 or x + 0.075 > wcell - 0.07:
            return False
        for n, (yt, _, _, _, wires) in res.items():
            if n == net or yt is None:
                continue
            for L, x1, x2 in wires:
                hx, hy = (0.075, 0.135) if L == 2 else (0.135, 0.075)
                if not (x1 >= x + hx + SP2 - 1e-9 or x2 <= x - hx - SP2 + 1e-9 or
                        yt - 0.075 >= y + hy + SP2 - 1e-9 or yt + 0.075 <= y - hy - SP2 + 1e-9):
                    return False
        return True

    def access(res):
        """Moi cong phai co diem vao tu ngoai cell (khoi P&R); luu c.pinat[p] = (cot, y)."""
        pinat = {}
        for p in ports:
            segs = res[p][1]
            pts = [(col, round(y, 3)) for col, (lo, hi) in sorted(segs.items())
                   for y in [lo + 0.135 + 0.01 * k for k in range(int((hi - lo - 0.27) / 0.01) + 1)]]
            # diem vao cua cac cong khac nhau phai cung dat via duoc: dem M2 doc / M3 ngang 0.27 dai,
            # cach 0.14 -> |dx| >= 0.41 hoac |dy| >= 0.41 (hai chan BOOTH_SEL o cot ke nhau tung chong nhau)
            def compat(pt):
                return all(abs(X(pt[0]) - X(q[0])) >= 0.41 - 1e-9 or abs(pt[1] - q[1]) >= 0.41 - 1e-9
                           for q in pinat.values())
            hit = next((pt for pt in sorted(pts, key=lambda t: abs(t[1] - YIN))
                        if compat(pt) and free(X(pt[0]), pt[1], p, res)), None)
            if hit is None:
                return False
            pinat[p] = hit
        c.pinat = pinat
        return True

    for attempt in range(tries):
        occ = defaultdict(list, {k: list(v) for k, v in fixed.items()})
        m2occ = defaultdict(list)
        res, fail = {}, False
        for net in single:
            (col, seg), = plan(net, None)[0].items()
            if not ok_col(occ, col, net, *seg):
                fail = True
                break
            occ[col].append((net, *seg))
            res[net] = (None, {col: seg}, [], [], [])
        if fail:
            return False
        order = multi[:]
        if attempt:
            rng.shuffle(order)
        budget = [3000]

        def dfs(i):
            if i == len(order):
                return access(res)
            budget[0] -= 1
            if budget[0] < 0:
                return False
            net = order[i]
            ivs = [iv for v in term[net].values() for iv in v]
            ymid = sum(a + b for a, b in ivs) / 2 / len(ivs)
            for y, layer in sorted(((t, L) for t in TRACKS for L in (2, 3)),
                                   key=lambda t: (abs(t[0] - ymid) + 0.2 * (t[1] - 2), rng.random())):
                segs, bridges, vias, wires = plan(net, y, layer)
                if not all(ok_col(occ, col, net, *s) for col, s in segs.items()):
                    continue
                if not ok_m(m2occ, y, net, wires):
                    continue
                for col, s in segs.items():
                    occ[col].append((net, *s))
                for L, x1, x2 in wires:
                    m2occ[(L, y)].append((net, x1, x2))
                res[net] = (y, segs, bridges, vias, wires)
                if dfs(i + 1):
                    return True
                for col in segs:
                    occ[col].pop()
                for L, _, _ in wires:
                    m2occ[(L, y)].pop()
                del res[net]
            return False

        if dfs(0):
            c.routes, c.fixed = res, fixed
            return True
    return False


def density(c, ports):
    """So net nhieu cot cat qua mot cot (can duoi so track M2)."""
    gs = groups(c)
    cols, ng = defaultdict(set), defaultdict(int)
    for _, _, net in gs:
        ng[net] += 1
    for col in range(1, c.ncols, 2):
        for r in 'np':
            it = c.item[r].get(col)
            if isinstance(it, tuple):
                cols[it[1]].add(col)
    for _, cs, net in gs:
        if net not in RAILS and (ng[net] > 1 or cols[net] or net in ports):
            cols[net].add(cs[len(cs) // 2])
    spans = [(min(s), max(s)) for s in cols.values() if len(s) > 1]
    return max(sum(a <= x <= b for a, b in spans) for x in range(c.ncols))


def build(cells, name, seed=1, samples=1500, budget_s=900):
    import time
    t0 = time.time()
    devs = flatten(cells, name)
    ports = [p for p in cells[name]['pins'] if p not in RAILS]
    rng = random.Random(seed)
    svars = [stage_variants(st, rng) for st in stages(devs)]
    cands = []
    for _ in range(samples):
        c = place(compose(svars, rng))
        cands.append((density(c, ports), c.ncols, len(cands), c))
    cands.sort(key=lambda t: t[:3])
    for d, _, _, c in cands[:80]:
        if d > 2 * len(TRACKS) or time.time() - t0 > budget_s:
            break
        if route(c, ports, rng, tries=20):          # 20: rang buoc diem vao chan (access) can thu nhieu hon
            c.name, c.devs, c.ports = name, devs, ports
            c.dirs = {p: 'output' if any(p in (d, s) for _, d, _, s, _ in devs) else 'input' for p in ports}
            return c
    raise SystemExit(f"{name}: khong di day duoc; mat do tot nhat {cands[0][0]} > {len(TRACKS)} track hoac het gio")


def geometry(c):
    R, W = [], round(G * (c.ncols + 1), 4)

    def add(lyr, x1, y1, x2, y2):
        R.append((lyr, round(x1, 4), round(y1, 4), round(x2, 4), round(y2, 4)))
    # khung giong laFrame (gen_layout_A.il): tiep xuc tap tren bien cell (hang lat dung chung ray)
    add('Oxide', 0, -0.12, W, 0.24)
    add('Pimp', -0.02, -0.14, W + 0.02, 0.26)
    add('Oxide', 0, H - 0.24, W, H + 0.12)
    add('Nimp', -0.02, H - 0.34, W + 0.02, H + 0.14)
    add('Nwell', -0.12, 1.38, W + 0.12, H + 0.24)
    add('Nimp', 0, 0.26, W, 1.00)
    add('Pimp', 0, 1.50, W, H - 0.34)
    add('prBoundary', 0, 0, W, H)
    add('Metal1', 0, -0.06, W, 0.24)
    add('Metal1', 0, H - 0.24, W, H + 0.06)
    for k in range(c.ncols):
        add('Cont', X(k) - 0.06, -0.06, X(k) + 0.06, 0.06)
        add('Cont', X(k) - 0.06, H - 0.06, X(k) + 0.06, H + 0.06)
    contacted = {(r, col) for r, col, _ in c.contacts}
    for r in 'np':
        yc, it = YC[r], c.item[r]
        hnode = {}
        for col in range(0, c.ncols, 2):
            if c.node[r].get(col) is None:
                continue
            ws = [i[2] for i in (it.get(col - 1), it.get(col + 1)) if isinstance(i, tuple)]
            hnode[col] = max(ws + [0.24 if (r, col) in contacted or not ws else 0])
        for col, h in hnode.items():
            add('Oxide', X(col) - 0.12, yc - h / 2, X(col) + 0.12, yc + h / 2)
            if (r, col) in contacted:
                add('Cont', X(col) - 0.06, yc - 0.06, X(col) + 0.06, yc + 0.06)
        for col, i in it.items():
            if isinstance(i, tuple):
                add('Oxide', X(col) - 0.15, yc - i[2] / 2, X(col) + 0.15, yc + i[2] / 2)
            elif i == 'PASS':
                h = min(hnode[col - 1], hnode[col + 1])
                add('Oxide', X(col) - 0.15, yc - h / 2, X(col) + 0.15, yc + h / 2)
    for col in range(1, c.ncols, 2):
        n, p = c.item['n'].get(col), c.item['p'].get(col)
        gn, gp = isinstance(n, tuple), isinstance(p, tuple)
        if not (gn or gp):
            continue
        lo = YN - n[2] / 2 - 0.18 if gn else YIN - 0.12
        hi = YP + p[2] / 2 + 0.18 if gp else YIN + 0.12
        x = X(col)
        add('Poly', x - 0.05, lo, x + 0.05, hi)
        add('Poly', x - 0.10, YIN - 0.12, x + 0.10, YIN + 0.12)
        add('Cont', x - 0.06, YIN - 0.06, x + 0.06, YIN + 0.06)
    for col, lst in c.fixed.items():
        for net, lo, hi in lst:
            add('Metal1', X(col) - HM, max(lo, 0), X(col) + HM, min(hi, H))
    for net, (y, segs, bridges, vias, wires) in c.routes.items():
        for col, (lo, hi) in segs.items():
            add('Metal1', X(col) - HM, lo, X(col) + HM, hi)
        for r in bridges:
            add('Metal1', X(r[0]) - HM, y - LAND, X(r[-1]) + HM, y + LAND)
        for col in vias:
            add('Via1', X(col) - 0.07, y - 0.07, X(col) + 0.07, y + 0.07)
            if any(L == 3 for L, _, _ in wires):
                add('Via2', X(col) - 0.07, y - 0.07, X(col) + 0.07, y + 0.07)
        for L, x1, x2 in wires:
            add(f'Metal{L}', x1, y - 0.075, x2, y + 0.075)
    pins = [('VSS', 'inputOutput', 0, 0, W, 0.24), ('VDD', 'inputOutput', 0, H - 0.24, W, H)]
    for p in c.ports:
        if p in getattr(c, 'pinat', {}):          # diem vao da kiem tra (route.access)
            col, y = c.pinat[p]
            lo, hi = y - 0.135, y + 0.135
        else:
            col, ivs = sorted(c.term[p].items())[0]
            lo, hi = ivs[0]
        pins.append((p, c.dirs[p], round(X(col) - HM, 4), round(lo, 4), round(X(col) + HM, 4), round(hi, 4)))
    return W, R, pins


def ascii(c):
    rows = []
    for r in 'pn':
        s = ''
        for col in range(c.ncols):
            if col % 2 == 0:
                s += (c.node[r].get(col) or '.')[:5].ljust(6)
            else:
                i = c.item[r].get(col)
                s += ('[' + i[1][:3] + ']' if isinstance(i, tuple) else {'PASS': '=====', 'B': '  |  '}.get(i, '     ')).ljust(6)
        rows.append(f'{r}: {s}')
    for net, (y, segs, bridges, vias, m2) in sorted(c.routes.items()):
        rows.append(f'   {net:8s} y={y} cot={sorted(segs)} via={vias} day={m2}')
    return '\n'.join(rows)


SKILL_HEAD = r''';; layout/gen_layout_BCD.il -- sinh boi layout/gen_layout_cells.py, khong sua tay.
;; Chay trong VM qua layout/run_layout_A.sh (GEN=layout/gen_layout_BCD.il).
laErr = 0
procedure(laBox(cv lyr purp x1 y1 x2 y2)
  let((fig)
    fig = dbCreateRect(cv list(lyr purp) list(list(x1 y1) list(x2 y2)))
    unless(fig printf("LA_ERROR rect %s %s failed in %s\n" lyr purp cv~>cellName) laErr = laErr + 1)
    fig))
procedure(laPin(cv name dir x1 y1 x2 y2)
  let((fig net lb)
    fig = laBox(cv "Metal1" "pin" x1 y1 x2 y2)
    net = or(dbFindNetByName(cv name) dbCreateNet(cv name))
    unless(dbFindTermByName(cv name) dbCreateTerm(net name dir))
    dbCreatePin(net fig name)
    lb = car(errset(dbCreateLabel(cv list("Metal1" "label") list((x1 + x2) / 2.0 (y1 + y2) / 2.0)
                     name "centerCenter" "R0" "stick" 0.1)))
    unless(lb dbCreateLabel(cv list("Metal1" "pin") list((x1 + x2) / 2.0 (y1 + y2) / 2.0)
                     name "centerCenter" "R0" "stick" 0.1))))
procedure(laDraw(libName cellName w rects pins)
  let((lib cv)
    lib = ddGetObj(libName)
    unless(lib
      lib = ddCreateLib(libName strcat("./" libName))
      techBindTechFile(lib "gpdk090")
      printf("LA_LIB created %s\n" libName))
    cv = dbOpenCellViewByType(libName cellName "layout" "maskLayout" "w")
    foreach(r rects laBox(cv car(r) "drawing" nth(1 r) nth(2 r) nth(3 r) nth(4 r)))
    foreach(p pins laPin(cv car(p) cadr(p) nth(2 p) nth(3 p) nth(4 p) nth(5 p)))
    dbSave(cv)
    printf("LA_CELL %s/%s W=%.3f H=2.760 area=%.4f um2 shapes=%d\n" libName cellName w w * 2.76 length(rects))
    t))
'''


def skill(cells_out):
    L = [SKILL_HEAD, 'procedure(laMain()']
    for lib, c, W, R, pins in cells_out:
        L.append(f'  ;; {c.name}: {len(c.devs)} T (sau khi chia finger), {c.ncols} cot')
        L.append(f'  laDraw("{lib}" "{c.name}" {W:g}')
        L.append('    list(' + '\n      '.join(f'list("{a}" {b:g} {cc:g} {d:g} {e:g})' for a, b, cc, d, e in R) + ')')
        L.append('    list(' + '\n      '.join(f'list("{a}" "{b}" {cc:g} {d:g} {e:g} {f:g})' for a, b, cc, d, e, f in pins) + '))')
    L += ['  t)',
          'unless(errset(laMain() t) printf("LA_ERROR SKILL error, see message above\\n") laErr = laErr + 1)',
          'printf("LA_SUMMARY errors=%d\\n" laErr)',
          'exit(if(laErr == 0 0 1))', '']
    return '\n'.join(L)


def selftest():
    A = [('G', 'x', 'y', 'A', 1), ('G', 'y', 'z', 'B', 1)]
    assert len(align(A, A)) == 2
    assert len(align(A, A[::-1])) == 3
    tr = trails([('a', 'b', 'G1', 1), ('b', 'c', 'G2', 1), ('b', 'a', 'G3', 1)], random.Random(0))
    assert sum((len(t) - 1) // 2 for t in tr) == 3


def main():
    selftest()
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    cells = load()
    out = []
    for lib, name in TARGETS:
        if args and name not in args:
            continue
        c = build(cells, name)
        W, R, pins = geometry(c)
        out.append((lib, c, W, R, pins))
        print(f'{lib}/{name}: {len(c.devs)} T, {c.ncols} cot, W={W:.2f} um, dien tich {W * H:.2f} um2, '
              f'net qua M2/M3: {sum(1 for r in c.routes.values() if r[4])}/{sum(1 for r in c.routes.values() if any(w[0] == 3 for w in r[4]))}')
        if '-v' in sys.argv:
            print(ascii(c))
    if not args:
        (REPO / 'layout' / 'gen_layout_BCD.il').write_text(skill(out), encoding='ascii', newline='\n')
        print('ghi layout/gen_layout_BCD.il')
    return 0


if __name__ == '__main__':
    sys.exit(main())
