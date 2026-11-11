#!/usr/bin/env python3
"""ALU_TOP = ALU_CORE (A) + MUL8 (B+C) + DIV8 (D). Chay tren Windows, Python 3 stdlib.

    python blocks/ALU_TOP/gen_top.py           # ghi blocks/ALU_TOP/ALU_TOP.scs + tb smoke
    python blocks/ALU_TOP/gen_top.py --check   # muc logic: vectors/alu_full.csv vs model.alu_full
    python blocks/ALU_TOP/gen_top.py --count   # dem transistor
    python blocks/ALU_TOP/gen_top.py --res out/ALU_TOP_NN   # so ket qua Spectre smoke
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(REPO / 'blocks' / 'ALU_DIV'), str(REPO / 'blocks' / 'ALU_MUL'), str(REPO / 'blocks'), str(REPO)]
import gen_blocks as gb  # noqa: E402
import gen_div  # noqa: E402
import gen_mul  # noqa: E402
from gen_blocks import BLOCKS, Block, bits, bus, val  # noqa: E402
from model.alu_ref import alu_full  # noqa: E402

T_NS = 12.0   # DIV8 cham nhat (~9.4 ns o NN)
SMOKE = [(0, 100, 27), (0, 127, 1), (1, 128, 1), (2, 0xF0, 0x3C), (3, 0x0F, 0x30),
         (4, 0xAA, 0xFF), (5, 0x55, 0), (9, 128, 128), (9, 255, 127), (11, 128, 255),
         (11, 249, 2), (11, 5, 0)]   # 12 vector: Spectre ALU_TOP ~8000 T rat cham


KSA = '--div' in sys.argv and sys.argv[sys.argv.index('--div') + 1] == 'ksa'   # ALU_TOPK = DIV8K (docs/huong_toi_uu.md)
TOP, DIV = ('ALU_TOPK', 'DIV8K') if KSA else ('ALU_TOP', 'DIV8')


def gen_top():
    gen_div.build()
    if KSA and DIV not in BLOCKS:
        gen_div.gen_div8('ksa')
    gen_mul.gen_mul8().__class__ = gen_div.TieBlock   # MUL8 dung VDD/VSS lam hang so trong mo phong logic
    if TOP in BLOCKS:
        return BLOCKS[TOP]
    A, B, OP = bus('A', 8), bus('B', 8), bus('OP', 4)
    t = Block(TOP, f'blocks/ALU_TOP/{TOP}.scs', A + B + OP, bus('Y', 16) + ['Z', 'C', 'V', 'DZ'])
    t.x('MUL8', A + B, bus('MULP', 16))
    t.x(DIV, A + B, bus('DIVQ', 8) + bus('DIVR', 8) + ['DIVV', 'DIVDZ'])
    t.x('ALU_CORE', A + B + OP + bus('MULP', 16) + bus('DIVQ', 8) + bus('DIVR', 8) + ['DIVV', 'DIVDZ'], t.outs)
    return t


def run_top(op, a, b):
    o = BLOCKS[TOP].call(bits(a, 8) + bits(b, 8) + bits(op, 4))
    return {'y': val(o[:16]), 'z': o[16], 'c': o[17], 'v': o[18], 'dz': o[19]}


def check():
    gen_top()
    tot = bad = 0
    with (REPO / 'vectors' / 'alu_full.csv').open(newline='') as f:
        for r in csv.DictReader(f):
            op, a, b = int(r['op']), int(r['a']), int(r['b'])
            got, ref = run_top(op, a, b), alu_full(op, a, b)
            tot += 1
            errs = [k for k in got if r[k] != '-1' and (got[k] != int(r[k]) or (ref[k] is not None and ref[k] != int(r[k])))]
            if errs:
                bad += 1
                if bad <= 10:
                    print('SAI', dict(r), '->', got)
    print(f'{TOP} muc logic: {tot - bad}/{tot} dong vectors/alu_full.csv dung (y=-1 bo qua)')
    return 1 if bad else 0


def incs():
    seen = ['cells/A/cells_A.scs'] + [c for c in gb.CELL_FILES if '_stub_B' in c] + \
           [c.path for c in gen_mul.make_cells()]
    for b in BLOCKS.values():
        if b.path not in seen:
            seen.append(b.path)
    return seen


def smoke_rows():
    R = []
    for op, a, b in SMOKE:
        e = alu_full(op, a, b)
        R.append({'op': op, 'a': a, 'b': b, **{k: -1 if e[k] is None else e[k] for k in ('y', 'z', 'c', 'v', 'dz')}})
    return R


def main():
    t = gen_top()
    if '--check' in sys.argv:
        return check()
    if '--count' in sys.argv:
        subs = gb.parse_subckts(incs()[1:] + gb.CELL_FILES)

        def n(m):
            return 1 if m.startswith('gpdk090_') else sum(n(x) for x in subs[m])
        for name in ('ALU_CORE', 'MUL8', DIV, TOP):
            print(f'{name:10s} {n(name):6d} transistor')
        return 0
    if '--res' in sys.argv:
        return gen_div.check_res(TOP, smoke_rows(), Path(sys.argv[sys.argv.index('--res') + 1]), T_NS)
    p = REPO / t.path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f'// {TOP}: sinh tu dong boi blocks/ALU_TOP/gen_top.py - khong sua tay\n'
                 f'// = ALU_CORE + MUL8 + {DIV}. Can include moi cell/khoi con (xem tb/tb_ALU_TOP_NN.scs).\n'
                 'simulator lang=spectre\n' + t.scs(), encoding='ascii', newline='\n')
    print('ghi', t.path)
    gen_div.write_tb(TOP, smoke_rows(), T_NS, incs(), tag='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
