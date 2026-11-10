#!/usr/bin/env python3
"""Sinh testbench Spectre tu vectors/*.csv cho KSA8 va ALU_CORE (chay tren Windows).

    python blocks/gen_tb.py

Ghi blocks/<khoi>/tb/tb_<TOP>.scs (nguon PWL, DUT, tai FO4, phan tich tran) va
tb_<TOP>_<CORNER>.scs (include mo hinh + cell + khoi + tb_<TOP>.scs) cho NN, SS, FF.
Moi vector 2 ns, suon 20 ps. Chan <X>_<i> lay bit i cua cot <x>; chan khong co '_<i>' lay cot <x>.
Chay trong VM (tu thu muc repo):
    spectre blocks/ALU_ADD/tb/tb_KSA8_NN.scs -format psfascii -raw out/KSA8_NN
"""
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_blocks import BLOCKS, CELL_FILES, REPO, build  # noqa: E402

T, EDGE, VDD = 2e-9, 20e-12, 1.2
MODEL = '/home/buet/cadence/gpdk090_v4.6/models/spectre/gpdk090.scs'
CORNERS = ('NN', 'SS', 'FF')
# top -> (thu muc, file vector, ham chon vector de do tre)
BENCH = {
    'KSA8': ('blocks/ALU_ADD/tb', 'vectors/ksa8.csv', lambda r: True),
    'ALU_CORE': ('blocks/ALU_CORE/tb', 'vectors/alu_core.csv', lambda r: int(r['op']) in (0, 1)),
}


def col_bit(port):
    """'A_3' -> ('a', 3); 'CIN' -> ('cin', 0)."""
    base, _, idx = port.partition('_')
    return base.lower(), int(idx) if idx else 0


def rows(top):
    with (REPO / BENCH[top][1]).open(newline='') as f:
        return list(csv.DictReader(f))


def pwl(levels):
    """Danh sach muc logic moi vector -> wave PWL (chi them diem khi doi muc)."""
    w = [0.0, levels[0] * VDD]
    for k in range(1, len(levels)):
        if levels[k] != levels[k - 1]:
            w += [k * T, levels[k - 1] * VDD, k * T + EDGE, levels[k] * VDD]
    toks = [f'{w[i] * 1e12:.0f}p {w[i + 1]:g}' for i in range(0, len(w), 2)]
    lines, cur = [], []
    for t in toks:
        cur.append(t)
        if len(cur) == 8:
            lines.append(' '.join(cur))
            cur = []
    if cur:
        lines.append(' '.join(cur))
    return ' \\\n    '.join(lines)


def gen(top):
    b = build()[top]
    d, _, _ = BENCH[top]
    R = rows(top)
    out = REPO / d
    out.mkdir(parents=True, exist_ok=True)
    L = [f'// Testbench {top}: sinh tu dong boi blocks/gen_tb.py tu {BENCH[top][1]} ({len(R)} vector)',
         f'// {T * 1e9:g} ns/vector, suon {EDGE * 1e12:g} ps, tai 4x INV_X1 moi ngo ra',
         'simulator lang=spectre', 'global 0',
         f'VVDD (VDD 0) vsource dc={VDD}', 'VVSS (VSS 0) vsource dc=0']
    for p in b.ins:
        c, i = col_bit(p)
        lv = [(int(r[c]) >> i) & 1 for r in R]
        L.append(f'V{p} ({p} 0) vsource type=pwl wave=[ \\\n    {pwl(lv)} ]')
    ports = ' '.join(b.ins + b.outs)
    L.append(f'XDUT ({ports} VDD VSS) {top}')
    for p in b.outs:
        for k in range(4):
            L.append(f'XL{p}_{k} ({p} ld_{p}_{k} VDD VSS) INV_X1')
    L.append('save ' + ' '.join(b.outs) + ' VVDD:p')   # dong nguon -> cong suat (tools/power.py)
    L.append('opts options save=selected temp=27 reltol=1e-3')
    L.append(f'tran tran stop={len(R) * T * 1e9:g}n maxstep=10p errpreset=moderate')
    (out / f'tb_{top}.scs').write_text('\n'.join(L) + '\n', encoding='ascii', newline='\n')
    # include tuong doi so voi thu muc chua file tb (Spectre tim include theo file goi)
    rel = lambda p: os.path.relpath(REPO / p, out).replace('\\', '/')
    # cells_A.scs include moi cell cua A dung mot lan (Spectre cam dinh nghia subckt 2 lan)
    incs = ['cells/A/cells_A.scs'] + [c for c in CELL_FILES if '_stub_B' in c] + [x.path for x in BLOCKS.values()]
    for cn in CORNERS:
        w = [f'// {top} corner {cn}: sinh tu dong boi blocks/gen_tb.py', 'simulator lang=spectre',
             f'include "{MODEL}" section={cn}'] + [f'include "{rel(p)}"' for p in incs] + \
            [f'include "tb_{top}.scs"']
        (out / f'tb_{top}_{cn}.scs').write_text('\n'.join(w) + '\n', encoding='ascii', newline='\n')
    print(f'ghi {d}/tb_{top}.scs ({len(R)} vector) + {len(CORNERS)} corner')


if __name__ == '__main__':
    for top in BENCH:
        gen(top)
