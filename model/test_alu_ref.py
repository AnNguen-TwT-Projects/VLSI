"""Tests for model/alu_ref.py and model/gen_vectors.py.

Run:  python -m unittest discover -s model -v
"""
import csv
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alu_ref as m  # noqa: E402
import gen_vectors  # noqa: E402

OPS = {'ADD': 0b0000, 'SUB': 0b0001, 'AND': 0b0010, 'OR': 0b0011,
       'XOR': 0b0100, 'NOT': 0b0101, 'MUL': 0b1001, 'DIV': 0b1011}
RESERVED = [0b0110, 0b0111, 0b1000, 0b1010, 0b1100, 0b1101, 0b1110, 0b1111]


def s8(x):
    return x - 256 if x & 0x80 else x


def s16(x):
    return x - 65536 if x & 0x8000 else x


def tdiv(a, b):
    """Reference signed division, truncation toward zero (C semantics)."""
    q = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        q = -q
    return q, a - q * b


class TestKsa8(unittest.TestCase):
    def test_exhaustive(self):
        for cin in (0, 1):
            for a in range(256):
                for b in range(256):
                    r = m.ksa8(a, b, cin)
                    tot = a + b + cin
                    self.assertEqual(r['s'], tot & 0xFF)
                    self.assertEqual(r['c8'], tot >> 8)
                    self.assertEqual(r['c7'], ((a & 0x7F) + (b & 0x7F) + cin) >> 7)

    def test_full_carry_chain(self):
        self.assertEqual(m.ksa8(0xFF, 0x01, 0), {'s': 0, 'c7': 1, 'c8': 1})
        self.assertEqual(m.ksa8(0xFF, 0x00, 1), {'s': 0, 'c7': 1, 'c8': 1})
        self.assertEqual(m.ksa8(0x55, 0xAA, 0), {'s': 0xFF, 'c7': 0, 'c8': 0})


class TestDivSigned(unittest.TestCase):
    def test_exhaustive(self):
        for a in range(256):
            for b in range(256):
                r = m.div_signed(a, b)
                if b == 0:
                    self.assertEqual(r['dz'], 1)
                    self.assertIsNone(r['q'])
                    self.assertIsNone(r['r'])
                    self.assertEqual(r['v'], 0)
                    continue
                self.assertEqual(r['dz'], 0)
                if a == 0x80 and b == 0xFF:
                    self.assertEqual(r, {'q': 0x80, 'r': 0, 'v': 1, 'dz': 0})
                    continue
                q, rem = tdiv(s8(a), s8(b))
                self.assertEqual((s8(r['q']), s8(r['r']), r['v']), (q, rem, 0), (a, b))
                # remainder takes the dividend's sign (or is zero)
                self.assertTrue(rem == 0 or (rem < 0) == (s8(a) < 0))

    def test_examples(self):
        r = m.div_signed(256 - 7, 2)          # -7 / 2
        self.assertEqual((s8(r['q']), s8(r['r'])), (-3, -1))
        r = m.div_signed(7, 256 - 2)          # 7 / -2
        self.assertEqual((s8(r['q']), s8(r['r'])), (-3, 1))
        r = m.div_signed(0x80, 0x80)          # -128 / -128
        self.assertEqual((s8(r['q']), s8(r['r'])), (1, 0))


class TestBooth(unittest.TestCase):
    def test_rows_sum_to_product_exhaustive(self):
        for a in range(256):
            for b in range(256):
                bp = m.booth_pp_rows(a, b)
                tot = sum(bp['rows']) + (bp['neg'][3] << 6)
                self.assertEqual(tot & 0xFFFF, (s8(a) * s8(b)) & 0xFFFF, (a, b))

    def test_row_structure(self):
        for a, b in [(0x80, 0x80), (0x7F, 0x80), (0x05, 0xFD), (0, 0), (0xFF, 0xFF)]:
            bp = m.booth_pp_rows(a, b)
            for i in range(4):
                d, n, pp = bp['digits'][i], bp['neg'][i], bp['pp9'][i]
                self.assertIn(d, (-2, -1, 0, 1, 2))
                self.assertEqual(n, (b >> (2 * i + 1)) & 1)  # neg_i = b[2i+1]
                mag = (abs(d) * s8(a)) & 0x1FF
                self.assertEqual(pp, mag ^ (0x1FF if n else 0))
                s = pp >> 8
                row = bp['rows'][i]
                self.assertEqual((row >> (2 * i)) & 0x1FF, pp)
                if i == 0:
                    self.assertEqual((row >> 9) & 0b111, ((s ^ 1) << 2) | (s << 1) | s)
                else:
                    top = (1 << (2 * i + 10)) | ((s ^ 1) << (2 * i + 9))
                    self.assertEqual(row & (top & 0xFFFF), top & 0xFFFF)
                    # neg of the previous row sits in this row's empty slot
                    self.assertEqual((row >> (2 * i - 2)) & 1, bp['neg'][i - 1])
                    self.assertEqual((row >> (2 * i - 1)) & 1, 0)

    def test_digits_recode_b(self):
        for b in range(256):
            bp = m.booth_pp_rows(1, b)
            self.assertEqual(sum(d * 4 ** i for i, d in enumerate(bp['digits'])), s8(b))


class TestAluCore(unittest.TestCase):
    def test_add_sub_exhaustive(self):
        for a in range(256):
            for b in range(256):
                r = m.alu_core(OPS['ADD'], a, b)
                t = a + b
                self.assertEqual(r['y'], t & 0xFF)
                self.assertEqual(r['c'], t >> 8)
                self.assertEqual(r['v'], int(not (-128 <= s8(a) + s8(b) <= 127)))
                self.assertEqual(r['z'], int(t & 0xFF == 0))
                self.assertEqual(r['dz'], 0)
                r = m.alu_core(OPS['SUB'], a, b)
                self.assertEqual(r['y'], (a - b) & 0xFF)
                self.assertEqual(r['c'], int(a >= b))  # C=1 means no borrow
                self.assertEqual(r['v'], int(not (-128 <= s8(a) - s8(b) <= 127)))

    def test_logic(self):
        for a in range(0, 256, 3):
            for b in range(0, 256, 5):
                for op, y in ((OPS['AND'], a & b), (OPS['OR'], a | b),
                              (OPS['XOR'], a ^ b), (OPS['NOT'], ~a & 0xFF)):
                    r = m.alu_core(op, a, b, mulp=0xFFFF, divq=1, divr=2, divv=1, divdz=1)
                    self.assertEqual(r, {'y': y, 'z': int(y == 0), 'c': 0, 'v': 0, 'dz': 0})

    def test_mul_div_passthrough(self):
        r = m.alu_core(OPS['MUL'], 3, 4, mulp=0xBEEF, divq=1, divr=2, divv=1, divdz=1)
        self.assertEqual(r, {'y': 0xBEEF, 'z': 0, 'c': 0, 'v': 0, 'dz': 0})
        r = m.alu_core(OPS['MUL'], 3, 4, mulp=0)
        self.assertEqual(r['z'], 1)
        r = m.alu_core(OPS['DIV'], 3, 4, mulp=0xBEEF, divq=0x12, divr=0x34, divv=1, divdz=1)
        self.assertEqual(r, {'y': 0x3412, 'z': 0, 'c': 0, 'v': 1, 'dz': 1})
        r = m.alu_core(OPS['DIV'], 3, 4, divq=0, divr=0)
        self.assertEqual(r, {'y': 0, 'z': 1, 'c': 0, 'v': 0, 'dz': 0})

    def test_reserved(self):
        for op in RESERVED:
            r = m.alu_core(op, 0xFF, 0xFF, mulp=0xFFFF, divq=0xFF, divr=0xFF, divv=1, divdz=1)
            self.assertEqual(r, {'y': 0, 'z': 1, 'c': 0, 'v': 0, 'dz': 0})


class TestAluFull(unittest.TestCase):
    def test_mul_exhaustive(self):
        for a in range(256):
            for b in range(256):
                r = m.alu_full(OPS['MUL'], a, b)
                p = s8(a) * s8(b)
                self.assertEqual(s16(r['y']), p)
                self.assertEqual(r, {'y': p & 0xFFFF, 'z': int(p == 0), 'c': 0, 'v': 0, 'dz': 0})

    def test_div_exhaustive(self):
        for a in range(256):
            for b in range(256):
                r = m.alu_full(OPS['DIV'], a, b)
                if b == 0:
                    self.assertEqual(r, {'y': None, 'z': None, 'c': 0, 'v': 0, 'dz': 1})
                    continue
                d = m.div_signed(a, b)
                y = (d['r'] << 8) | d['q']
                self.assertEqual(r, {'y': y, 'z': int(y == 0), 'c': 0, 'v': d['v'], 'dz': 0})

    def test_boundaries(self):
        r = m.alu_full(OPS['MUL'], 0x80, 0x80)          # -128 * -128
        self.assertEqual(r['y'], 16384)
        r = m.alu_full(OPS['MUL'], 0x80, 0x7F)          # -128 * 127
        self.assertEqual(s16(r['y']), -16256)
        r = m.alu_full(OPS['MUL'], 0xFF, 0xFF)          # -1 * -1
        self.assertEqual(r['y'], 1)
        r = m.alu_full(OPS['DIV'], 0x80, 0xFF)          # -128 / -1
        self.assertEqual((r['y'], r['v'], r['dz']), (0x0080, 1, 0))
        r = m.alu_full(OPS['DIV'], 256 - 7, 2)          # -7 / 2 -> Q=-3 R=-1
        self.assertEqual(r['y'], (0xFF << 8) | 0xFD)
        r = m.alu_full(OPS['DIV'], 0, 5)                # 0 / 5 -> Z
        self.assertEqual((r['y'], r['z']), (0, 1))
        r = m.alu_full(OPS['ADD'], 0x7F, 0x01)          # 127 + 1 overflow
        self.assertEqual((r['y'], r['v'], r['c']), (0x80, 1, 0))
        r = m.alu_full(OPS['SUB'], 0x80, 0x01)          # -128 - 1 overflow
        self.assertEqual((r['y'], r['v'], r['c']), (0x7F, 1, 1))

    def test_non_mul_div_matches_core(self):
        for op in ('ADD', 'SUB', 'AND', 'OR', 'XOR', 'NOT'):
            for a, b in [(0, 0), (1, 0xFF), (0x7F, 0x80), (0x55, 0xAA), (200, 100)]:
                self.assertEqual(m.alu_full(OPS[op], a, b), m.alu_core(OPS[op], a, b))


class TestVectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        gen_vectors.main(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def read(self, name):
        with open(os.path.join(self.tmp.name, name), newline='') as f:
            return list(csv.DictReader(f))

    def test_deterministic_and_lf(self):
        with tempfile.TemporaryDirectory() as d2:
            gen_vectors.main(d2)
            for name in gen_vectors.FILES:
                with open(os.path.join(self.tmp.name, name), 'rb') as f1, \
                        open(os.path.join(d2, name), 'rb') as f2:
                    b1 = f1.read()
                    self.assertEqual(b1, f2.read(), name)
                    self.assertNotIn(b'\r', b1)

    def test_committed_vectors_up_to_date(self):
        repo_vec = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vectors')
        for name in gen_vectors.FILES:
            path = os.path.join(repo_vec, name)
            if not os.path.exists(path):
                self.skipTest('vectors/ not generated yet')
            with open(path, 'rb') as f1, open(os.path.join(self.tmp.name, name), 'rb') as f2:
                self.assertEqual(f1.read(), f2.read(), name + ' is stale: rerun gen_vectors.py')

    def test_ksa8_csv(self):
        rows = self.read('ksa8.csv')
        self.assertGreaterEqual(len(rows), 120)
        self.assertEqual(list(rows[0]), ['a', 'b', 'cin', 's', 'c7', 'c8'])
        for r in rows:
            v = {k: int(x) for k, x in r.items()}
            self.assertEqual(m.ksa8(v['a'], v['b'], v['cin']),
                             {'s': v['s'], 'c7': v['c7'], 'c8': v['c8']})

    def test_alu_core_csv(self):
        rows = self.read('alu_core.csv')
        self.assertGreaterEqual(len(rows), 450)
        self.assertEqual(list(rows[0]), ['op', 'a', 'b', 'mulp', 'divq', 'divr', 'divv',
                                         'divdz', 'y', 'z', 'c', 'v', 'dz'])
        seen_zero, seen_ovf = set(), set()
        for r in rows:
            v = {k: int(x) for k, x in r.items()}
            exp = m.alu_core(v['op'], v['a'], v['b'], v['mulp'], v['divq'], v['divr'],
                             v['divv'], v['divdz'])
            self.assertEqual(exp, {k: v[k] for k in ('y', 'z', 'c', 'v', 'dz')})
            if v['z']:
                seen_zero.add(v['op'])
            if v['v'] and v['op'] in (OPS['ADD'], OPS['SUB']):
                seen_ovf.add(v['op'])
        self.assertEqual(seen_zero, set(OPS.values()))
        self.assertEqual(seen_ovf, {OPS['ADD'], OPS['SUB']})
        for op in OPS.values():
            self.assertGreaterEqual(sum(int(r['op']) == op for r in rows), 55)

    def test_alu_full_csv(self):
        rows = self.read('alu_full.csv')
        self.assertGreaterEqual(len(rows), 550)
        self.assertEqual(list(rows[0]), ['op', 'a', 'b', 'y', 'z', 'c', 'v', 'dz'])
        pairs = set()
        for r in rows:
            v = {k: int(x) for k, x in r.items()}
            exp = m.alu_full(v['op'], v['a'], v['b'])
            exp = {k: -1 if x is None else x for k, x in exp.items()}
            self.assertEqual(exp, {k: v[k] for k in ('y', 'z', 'c', 'v', 'dz')})
            pairs.add((v['op'], v['a'], v['b']))
        for need in [(OPS['MUL'], 0x80, 0x80), (OPS['DIV'], 0x80, 0xFF),
                     (OPS['DIV'], 256 - 7, 2), (OPS['DIV'], 5, 0)]:
            self.assertIn(need, pairs)


if __name__ == '__main__':
    unittest.main()
