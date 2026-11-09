# DIV8 - bo chia co dau 8 bit (phan cua D) va ALU_TOP

## File

| File | Noi dung |
|---|---|
| `blocks/ALU_DIV/gen_div.py` | Sinh `CAS_X1`, `DIV8`, testbench; `--check` (65536 cap), `--count`, `--res` |
| `cells/D/CAS_X1/CAS_X1.scs` | O cong/tru co dieu khien (sinh tu dong) |
| `blocks/ALU_DIV/DIV8.scs` | `subckt DIV8 A_0..7 B_0..7 Q_0..7 R_0..7 V DZ VDD VSS` |
| `blocks/ALU_DIV/tb/tb_DIV8_p{0,1,2}_{NN,SS,FF}.scs` | 60 vector DIV cua `vectors/alu_full.csv`, chia 3 phan x 20 |
| `blocks/ALU_TOP/gen_top.py` | Sinh `ALU_TOP` = `ALU_CORE` + `MUL8` + `DIV8`; `--check`, `--count`, `--res` |
| `blocks/ALU_TOP/ALU_TOP.scs`, `tb/tb_ALU_TOP_*.scs` | Khoi tong + testbench smoke 12 vector |

Ca hai script dung lai `Block` va bo mo phong muc logic `FUNC` cua `blocks/gen_blocks.py`.

## Kien truc DIV8

```
A -> neg(A, sA) = |A| -+                           +-> neg(Qu, sA^sB) -> Q
                       +-> mang non-restoring 8x9 --+
B -> neg(B, sB) = |B| -+    CAS + hang sua du 8 CAS +-> neg(Ru, sA)    -> R
DZ = NOR(B_7..0)          V = Q_7 & !(sA^sB) & !DZ   (chi o -128 / -1)
```

- `neg(X, s)` = (X xor s) + s: Y_0 = X_0, Y_i = X_i xor (s & (X_{i-1} | ... | X_0)).
  Chuoi AOI21 + INV (ripple), XNOR2 ra moi bit. |-128| = 128 van dung (8 bit khong dau).
- `CAS_X1 (X D T CI S CO)`: S = X ^ (D^T) ^ CI, CO = maj(X, D^T, CI). 3 XOR2 + 3 NAND2 = 48 T.
- Mang: phan du 9 bit bu 2. Hang i: X = {P[7:0], |A|_(7-i)}, T = 1 o hang 0, sau do
  T = q cua hang truoc (q = !dau). Bit 8 cua so chia noi VSS. Hang sua: R = P + (P<0 ? D : 0)
  (D AND dau qua NAND2+INV, CAS voi T = VSS).
- B = 0: Q, R khong xac dinh; V = 0, DZ = 1 (giong `model.alu_ref.alu_full`, ALU_CORE dat V = SEL_DIV & DIVV).
- -128 / -1: Q = 0x80, R = 0, V = 1.

## Ket qua

| Muc | Ket qua |
|---|---|
| Muc logic `CAS_X1` | 16/16 |
| Muc logic `DIV8` | 65536/65536 cap (a,b) dung voi `div_signed` (b=0: chi kiem V=0, DZ=1) |
| Transistor | CAS_X1 48, DIV8 4498, ALU_TOP 8006 (ALU_CORE 1340 + MUL8 2168 + DIV8 4498) |
| Spectre DIV8 NN | xem bang duoi |
| Muc logic `ALU_TOP` | 595/595 dong `vectors/alu_full.csv` (y=-1 bo qua) |

Spectre DIV8, NN, 12 ns/vector, maxstep 40 ps, mau o cuoi chu ky, nguong 0.6 V:

| Phan | Vector dung | Tre xau nhat | Thoi gian chay VM |
|---|---|---|---|
| p0 | 20/20 | 9.37 ns (127/0 -> 127/1, ra R_0) | 638 s |
| p1 | (cho) | | |
| p2 | (cho) | | |

Tre do tu 50% suon vao den lan cat 0.6 V cuoi cung cua bat ky ngo ra nao trong chu ky;
vector co b = 0 (ngo ra khong xac dinh) khong tinh tre. Duong cham: chuoi carry 9 bit x 8 hang
(moi hang cho q cua hang truoc) + hang sua du + bo dao dau R.

## Chay lai

```
python blocks/ALU_DIV/gen_div.py --check
python blocks/ALU_DIV/gen_div.py
python tools/vmjob.py --label D_div_p0_NN --timeout 1500 -c "mkdir -p out; timeout 1200 spectre \
  blocks/ALU_DIV/tb/tb_DIV8_p0_NN.scs -format psfascii -raw out/DIV8_p0_NN +log out/DIV8_p0_NN.log < /dev/null > /dev/null 2>&1"
python blocks/ALU_DIV/gen_div.py --res out/DIV8_p0_NN 0
```

Spectre DIV8 (~4500 T) chay ~2.7 s moi ns mo phong o NN, nen 60 vector duoc chia 3 job.

## Han che

- Chua chay SS/FF. O SS tre co the vuot 12 ns -> can tang `T_NS` trong `gen_div.py`.
- Bo chia mang rat cham (~9.4 ns o NN) so voi ALU_CORE (2 ns): neu ALU co mot chu ky chung
  thi DIV quyet dinh tan so; co the giam bang carry-lookahead moi hang hoac bo chia nhieu chu ky.
- ALU_TOP Spectre chi smoke 12 vector (khoi ~8000 T).
