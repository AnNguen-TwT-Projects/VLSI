# model/ - Mo hinh tham chieu Python cho ALU 8-bit

Chay tren may Windows (Python 3, chi thu vien chuan). Khong chay trong VM.

| File | Noi dung |
|---|---|
| `alu_ref.py` | Mo hinh chuan: `ksa8`, `alu_core` (khoi ALU_CORE cua A), `alu_full` (ca ALU), `div_signed`, `booth_pp_rows` (4 hang tich rieng Booth cho B kiem tra tung bit) |
| `test_alu_ref.py` | Unit test: KSA8 vet can 2x65536, MUL/DIV/Booth vet can 65536 cap, gia tri bien, kiem tra file CSV |
| `gen_vectors.py` | Sinh `vectors/ksa8.csv`, `vectors/alu_core.csv`, `vectors/alu_full.csv` (seed 2026, LF) |

## Chay test

```
python -m unittest discover -s model -v
```

## Sinh lai vector

```
python model/gen_vectors.py
```

Ket qua luon giong het (seed co dinh). Sua `alu_ref.py` hoac `gen_vectors.py` thi phai sinh lai va commit
`vectors/` cung luc; test `test_committed_vectors_up_to_date` se bao loi neu `vectors/` cu.

## Quy uoc trong CSV

- So nguyen thap phan khong dau (dang bit), vd `a=255` la `0xFF` = -1 co dau.
- `alu_core.csv`: cot `mulp, divq, divr, divv, divdz` la ngo vao ghep tu bo nhan/bo chia, lay ngau nhien
  o moi dong de kiem tra MUX. ALU_CORE chi cho di qua: MUL -> `y = mulp`; DIV -> `y = divr*256 + divq`,
  `v = divv`, `dz = divdz`.
- `alu_full.csv`: DIV voi `b = 0` -> `dz = 1`, `y` va `z` khong xac dinh, ghi `-1` (bo qua khi so sanh).
- Cot khong dung cho mot phep thi bo qua khi so sanh (CONVENTIONS muc 7).

## Cac diem dac ta da chot trong mo hinh

- `C` chi co nghia cho ADD/SUB (= c8; SUB: C = 1 la khong muon). Phep khac C = 0. MUL: V = 0.
- -128 / -1: `V = 1`, Q = 0x80, R = 0 (dung voi lop boc dau `(X xor s) + s` cho ra).
- Chia: lam tron ve 0, R mang dau cua A (vd -7 / 2: Q = -3, R = -1).
- OP du tru (0110-1000 = dich, chua lam; 1010; 1100-1111): mo hinh cho Y = 0, nen Z = NOR(Y) = 1,
  C = V = DZ = 0. Khong dua vao vector vi phan cung chua dinh nghia.
- Booth: `neg_i = b[2i+1]` (bo chon kieu XOR), nen nhom `111` cho hang toan 1 cong neg = 1 (tong van = 0).
  Hang 0 them `~s s s`, hang 1-3 them `1 ~s`; `neg_i` dat o cot 2i cua hang i+1; `neg_3` la bit le o cot 6.
  Bat bien: `(sum(rows) + (neg[3] << 6)) & 0xFFFF == A*B & 0xFFFF`.
