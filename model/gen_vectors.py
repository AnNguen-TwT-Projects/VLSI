"""Generate CSV test vectors from alu_ref.py into vectors/.

    python model/gen_vectors.py          # writes vectors/*.csv (deterministic, seed 2026)

Values are unsigned decimal bit patterns (docs/CONVENTIONS.md section 7).
Don't-care outputs (DIV by zero: y, z) are written as -1.
"""
import csv
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alu_ref import ADD, SUB, AND, OR, XOR, NOT, MUL, DIV, OPS, ksa8, alu_core, alu_full  # noqa: E402

SEED = 2026
FILES = ('ksa8.csv', 'alu_core.csv', 'alu_full.csv')
EDGE = (0, 1, 0x7F, 0x80, 0xFF)
BOUND_PAIRS = [(x, y) for x in EDGE for y in EDGE] + [(0x55, 0xAA), (0xAA, 0x55)]
OUT = ('y', 'z', 'c', 'v', 'dz')


def ksa8_rows(rng):
    pairs = [(x, y) for x in EDGE + (0x55, 0xAA) for y in EDGE + (0x55, 0xAA)]
    pairs += [(0xFF, 0x01), (0x01, 0xFF), (0x0F, 0x01), (0x7F, 0x7F), (0x80, 0x80)]
    rows = [(x, y, cin) for x, y in pairs for cin in (0, 1)]
    rows += [(rng.randrange(256), rng.randrange(256), rng.randrange(2)) for _ in range(40)]
    return [[a, b, cin] + list(ksa8(a, b, cin).values()) for a, b, cin in rows]


def alu_core_rows(rng):
    def rnd_side():
        return {'mulp': rng.randrange(65536), 'divq': rng.randrange(256), 'divr': rng.randrange(256),
                'divv': rng.randrange(2), 'divdz': rng.randrange(2)}

    cases = []  # (op, a, b, side-input overrides)
    for op in OPS.values():
        pairs = BOUND_PAIRS + [(rng.randrange(256), rng.randrange(256)) for _ in range(33)]
        cases += [(op, a, b, {}) for a, b in pairs]
    # Y == 0 for every op (Z flag)
    cases += [(ADD, 0, 0, {}), (ADD, 0x01, 0xFF, {}), (ADD, 0x80, 0x80, {}),
              (SUB, 0x5A, 0x5A, {}), (AND, 0x55, 0xAA, {}), (OR, 0, 0, {}),
              (XOR, 0xC3, 0xC3, {}), (NOT, 0xFF, 0x12, {}),
              (MUL, 0x12, 0x34, {'mulp': 0}), (DIV, 0x12, 0x34, {'divq': 0, 'divr': 0})]
    # signed overflow for ADD/SUB
    cases += [(ADD, 0x7F, 0x01, {}), (ADD, 0x40, 0x40, {}), (ADD, 0x80, 0xFF, {}),
              (ADD, 0x81, 0x81, {}), (SUB, 0x80, 0x01, {}), (SUB, 0x7F, 0xFF, {}),
              (SUB, 0x00, 0x80, {}), (SUB, 0x40, 0xC0, {})]
    rows = []
    for op, a, b, over in cases:
        side = rnd_side()
        side.update(over)
        res = alu_core(op, a, b, **side)
        rows.append([op, a, b] + list(side.values()) + [res[k] for k in OUT])
    return rows


def alu_full_rows(rng):
    cases = []
    for op in OPS.values():
        cases += [(op, a, b) for a, b in BOUND_PAIRS]
        cases += [(op, rng.randrange(256), rng.randrange(256)) for _ in range(46)]
    cases += [(MUL, 0x80, 0x81), (MUL, 0x7F, 0x7F), (MUL, 0x02, 0xFE),
              (DIV, 0xF9, 0x02), (DIV, 0x07, 0xFE), (DIV, 0xF9, 0xFE), (DIV, 0x05, 0x00),
              (DIV, 0x80, 0x80), (DIV, 0x80, 0x02), (DIV, 0x00, 0x05), (DIV, 0x03, 0x07)]
    rows = []
    for op, a, b in cases:
        res = alu_full(op, a, b)
        rows.append([op, a, b] + [-1 if res[k] is None else res[k] for k in OUT])
    return rows


def write(path, header, rows):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(header)
        w.writerows(rows)


def main(outdir=None):
    outdir = outdir or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vectors')
    os.makedirs(outdir, exist_ok=True)
    jobs = [('ksa8.csv', ['a', 'b', 'cin', 's', 'c7', 'c8'], ksa8_rows),
            ('alu_core.csv', ['op', 'a', 'b', 'mulp', 'divq', 'divr', 'divv', 'divdz'] + list(OUT),
             alu_core_rows),
            ('alu_full.csv', ['op', 'a', 'b'] + list(OUT), alu_full_rows)]
    for name, header, fn in jobs:
        rows = fn(random.Random(SEED))  # own RNG per file: editing one file keeps the others stable
        write(os.path.join(outdir, name), header, rows)
        print('%-13s %4d rows' % (name, len(rows)))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
