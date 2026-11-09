"""Golden reference model for the 8-bit ALU (docs/KE_HOACH_ALU.md, section 1).

All inputs/outputs are unsigned bit patterns (0..255 for 8 bit, 0..65535 for
16 bit), as in docs/CONVENTIONS.md section 7. Use s8()/s16() to read them signed.

Opcodes: ADD 0000, SUB 0001, AND 0010, OR 0011, XOR 0100, NOT 0101,
         MUL 1001, DIV 1011.
Reserved (0110-1000 = optional shifts, not built yet; 1010; 1100-1111):
the model outputs Y = 0, so Z = NOR(Y) = 1, and C = V = DZ = 0.
Reserved opcodes are NOT put in the test vectors (hardware may output anything).
"""

ADD, SUB, AND, OR, XOR, NOT, MUL, DIV = 0b0000, 0b0001, 0b0010, 0b0011, 0b0100, 0b0101, 0b1001, 0b1011
OPS = {'ADD': ADD, 'SUB': SUB, 'AND': AND, 'OR': OR, 'XOR': XOR, 'NOT': NOT, 'MUL': MUL, 'DIV': DIV}


def s8(x):
    return x - 256 if x & 0x80 else x


def s16(x):
    return x - 65536 if x & 0x8000 else x


def ksa8(a, b, cin):
    """Bit-level Kogge-Stone 8-bit adder (3 prefix levels: span 1, 2, 4).

    Returns s (8 bit), c7 = carry into bit 7, c8 = carry out of bit 7.
    """
    p = [(a >> i ^ b >> i) & 1 for i in range(8)]
    g = [(a >> i & b >> i) & 1 for i in range(8)]
    G, P = g[:], p[:]
    G[0] |= p[0] & cin  # fold cin into bit 0 so G[i] = carry out of bit i
    for d in (1, 2, 4):
        G, P = ([G[i] | (P[i] & G[i - d]) if i >= d else G[i] for i in range(8)],
                [P[i] & P[i - d] if i >= d else P[i] for i in range(8)])
    c = [cin] + G  # c[i] = carry into bit i
    s = sum((p[i] ^ c[i]) << i for i in range(8))
    return {'s': s, 'c7': c[7], 'c8': c[8]}


def div_signed(a, b):
    """Signed 8/8 division, modelled like the hardware sign wrapper:
    |A|, |B| -> unsigned divide -> negate Q if sA != sB, negate R if sA.

    Truncates toward zero; R has the sign of A.
    -128 / -1: v = 1, Q = 0x80, R = 0 (what the wrapper produces).
    b == 0:    dz = 1, q = r = None (don't care).
    Returns dict(q, r, v, dz) with q, r as 8-bit patterns.
    """
    if b == 0:
        return {'q': None, 'r': None, 'v': 0, 'dz': 1}
    sa, sb = a >> 7, b >> 7
    # (X XOR s) + s read as unsigned 8 bit == |X|, including |-128| = 128
    q, r = divmod(abs(s8(a)), abs(s8(b)))
    q = ((q ^ -(sa ^ sb)) + (sa ^ sb)) & 0xFF
    r = ((r ^ -sa) + sa) & 0xFF
    return {'q': q, 'r': r, 'v': int(a == 0x80 and b == 0xFF), 'dz': 0}


def booth_pp_rows(a, b):
    """Radix-4 Booth partial products for signed A x B, as in the plan.

    Group i (i = 0..3) looks at b[2i+1], b[2i], b[2i-1] (b[-1] = 0).
    digit_i in {-2..2}; neg_i = b[2i+1] (XOR-select encoder: digit 0 from
    '111' gives pp9 = 0x1FF and neg = 1, which still sums to 0).
    pp9_i = (|digit_i| * A as 9-bit two's complement) XOR (neg_i ? 0x1FF : 0),
    s_i = pp9_i[8].
    Sign-extension elimination:
      row 0 = {~s0, s0, s0, pp9_0}               (bits 11..0)
      row i = {1, ~s_i, pp9_i} << 2i  (i = 1..3)
    neg_i is placed in the empty slot of row i+1 at column 2i
    (neg_0 -> row1 bit 0, neg_1 -> row2 bit 2, neg_2 -> row3 bit 4);
    neg_3 has no row and is an extra bit at column 6 (column height 5).
    Rows are masked to 16 bits (row3's constant 1 lands at bit 16 and is dropped).

    Invariant: (sum(rows) + (neg[3] << 6)) & 0xFFFF == (s8(a) * s8(b)) & 0xFFFF
    Returns dict(digits, neg, pp9, rows).
    """
    bb = b << 1  # bb bit k = b[k-1], bb bit 0 = b[-1] = 0
    digits, neg, pp9, rows = [], [], [], []
    for i in range(4):
        w = bb >> (2 * i) & 0b111  # (b[2i+1], b[2i], b[2i-1])
        d = -2 * (w >> 2) + (w >> 1 & 1) + (w & 1)
        n = w >> 2
        pp = ((abs(d) * s8(a)) & 0x1FF) ^ (0x1FF if n else 0)
        s = pp >> 8
        if i == 0:
            row = pp | (s << 9) | (s << 10) | ((s ^ 1) << 11)
        else:
            row = (pp | ((s ^ 1) << 9) | (1 << 10)) << (2 * i) | neg[i - 1] << (2 * i - 2)
        digits.append(d)
        neg.append(n)
        pp9.append(pp)
        rows.append(row & 0xFFFF)
    return {'digits': digits, 'neg': neg, 'pp9': pp9, 'rows': rows}


def alu_core(op, a, b, mulp=0, divq=0, divr=0, divv=0, divdz=0):
    """Team lead A's ALU_CORE block: KSA8 + logic + output mux + flags.

    MUL/DIV results come in from the other blocks (mulp, divq, divr, divv,
    divdz) and are only muxed through. Returns dict(y, z, c, v, dz).
    """
    c = v = dz = 0
    if op in (ADD, SUB):
        sub = int(op == SUB)
        k = ksa8(a, b ^ (0xFF * sub), sub)
        y, c, v = k['s'], k['c8'], k['c7'] ^ k['c8']
    elif op == AND:
        y = a & b
    elif op == OR:
        y = a | b
    elif op == XOR:
        y = a ^ b
    elif op == NOT:
        y = ~a & 0xFF
    elif op == MUL:
        y = mulp
    elif op == DIV:
        y, v, dz = (divr << 8) | divq, divv, divdz
    else:
        y = 0  # reserved opcode
    return {'y': y, 'z': int(y == 0), 'c': c, 'v': v, 'dz': dz}


def alu_full(op, a, b):
    """Whole-ALU golden model. MUL: signed 8x8 -> 16 bit. DIV: see div_signed;
    on B = 0, y and z are don't care (None; written as -1 in CSV)."""
    if op == MUL:
        return alu_core(op, a, b, mulp=(s8(a) * s8(b)) & 0xFFFF)
    if op == DIV:
        d = div_signed(a, b)
        if d['dz']:
            return {'y': None, 'z': None, 'c': 0, 'v': 0, 'dz': 1}
        return alu_core(op, a, b, divq=d['q'], divr=d['r'], divv=d['v'])
    return alu_core(op, a, b)
