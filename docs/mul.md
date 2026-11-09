# MUL8: bo nhan co dau 8x8 -> 16 bit (phan B + C)

Moi thu duoc sinh tu `blocks/ALU_MUL/gen_mul.py` (dung lai `Block`/`FUNC` cua `blocks/gen_blocks.py`,
`pwl`/`col_bit` cua `blocks/gen_tb.py`, `check_results.py`).

```
python blocks/ALU_MUL/gen_mul.py              # ghi cell B/C, MUL8.scs, tb (80 vector, 3 ns/vector)
python blocks/ALU_MUL/gen_mul.py --check      # muc logic: ca 65536 cap (a, b)
python blocks/ALU_MUL/gen_mul.py --count      # so transistor, chieu cao cot, do sau
python cells/A/check_cells.py gen             # tb cell (CELLS da them FA/HA/BOOTH_*/CMP42)
spectre blocks/ALU_MUL/tb/tb_MUL8_NN.scs -format psfascii -raw out/MUL8_NN   # trong VM
python blocks/ALU_MUL/gen_mul.py --result out/MUL8_NN
```

## Chan

`subckt MUL8 A_0..A_7 B_0..B_7 P_0..P_15 VDD VSS`, P = (A x B co dau) & 0xFFFF. Noi vao `MULP_15..0` cua ALU_CORE.

## Cell moi (static CMOS, gpdk090, L = 0.1u, don vi n 0.12u / p 0.24u nhan so tang noi tiep)

| Cell | Chu | Chan | Ham | T |
|---|---|---|---|---|
| `FA_X1` | C | `A B CI S CO` | mirror adder 28T | 28 |
| `HA_X1` | C | `A B S CO` | XOR2 + NAND2 + INV | 18 |
| `BOOTH_ENC` | B | `X2 X1 X0 ONE TWO` | ONE = X1^X0, TWO = !(XNOR(X2,X1) + ONE); NEG = X2 (day) | 28 |
| `BOOTH_SEL` | B | `AJ AJM ONE TWO NEG PP` | PP = (ONE.AJ + TWO.AJM) ^ NEG = XNOR(AOI22, NEG) | 20 |
| `CMP42` | B | `X1 X2 X3 X4 CI S C CO` | 2 FA phang: FA(X1,X2,X3)->s1,CO; FA(s1,X4,CI)->S,C | 56 |

Cell phang (khong goi subckt khac) nen tb cua `check_cells.py` dung duoc nguyen ven. Khong can MUX2.

## Kien truc

1. 4 `BOOTH_ENC` + 36 `BOOTH_SEL` (9 bit/hang, a_-1 = 0, a_8 = a_7) + 4 INV (~s_i).
   Hang dung y het `model/alu_ref.booth_pp_rows` (loai bo mo rong dau, neg_i o hang i+1, neg_3 o cot 6;
   hang so 1 noi VDD, bit 16 bo).
   Chieu cao cot: `2 1 3 2 4 3 5 4 4 4 4 4 3 2 2 1`.
2. Tang 4:2: chuoi 7 `CMP42` (cot 6..12, CO -> CI cot ben trai), FA/HA o cac cot thap ->
   `2 1 1 2 3 2 2 ... 2`. Mot tang 4:2 khong dua duoc moi cot ve 2 (cot 6 cao 5 nen cot 5 khong duoc phat CO,
   keo theo cot 2..4 luon con mot cot cao 3).
3. Tang FA/HA (carry-save, 1 FA o cot 4 + HA o cot 5..15) -> 2 hang.
   Can dung 2 hang: neu cot 0..7 cao hon 2 thi phan thap co the sinh 2 nho vao bit 8.
4. Cong cuoi lai: ripple HA/FA cho P_0..7 (cot thap xong som), `KSA8` cua A cho P_8..15, CIN = nho cua ripple.

Tong: 4 BOOTH_ENC, 36 BOOTH_SEL, 4 INV, 7 CMP42, 9 FA, 17 HA, 1 KSA8.

## Ket qua

- Muc logic (`--check`): **65536/65536** cap (a, b) dung, so voi `model/alu_ref` (s8(a)*s8(b)) & 0xFFFF.
- So transistor: **2168** (KSA8 chiem 378). Do sau theo cell (KSA8 tinh ca cell con): 17 tren P_14.
- Spectre MUL8, 80 vector (cac dong MUL cua `vectors/alu_full.csv` + -128*-128, -128*127, 0*0, -1*-1, ...),
  3 ns/vector, tai FO4, mau o cuoi chu ky, nguong 0.6 V:

| Corner | Dung | Tre xau nhat | Vector (truoc -> sau), ngo ra |
|---|---|---|---|
| NN | 80/80 | 1427 ps | a=1 b=128 -> a=1 b=255, P_12 |
| SS | 80/80 | 2036 ps | nhu tren |
| FF | 80/80 | 1104 ps | nhu tren |

  Thoi gian Spectre: khoang 6 phut moi corner.
- Cell (`check_cells.py check`, Euler qua moi canh, FO4): moi cell dung bang chan tri o NN/FF/SS.
  Tre xau nhat o NN: FA S 171 ps, CO 105 ps; HA 77 ps; BOOTH_ENC TWO 147 ps; BOOTH_SEL 157 ps; CMP42 S 352 ps
  (SS: 506 ps). CMP42 dung chu ky 1 ns (`T_CELL` trong check_cells.py) vi 2 FA noi tiep o SS ~500 ps;
  voi 500 ps thi ngo ra S chua kip on dinh khi lay mau.

## Chua lam / chua kiem tra
- Do tre chi lay tren 80 vector, khong phai duong gang toi xau nhat. Chua do cong suat.
- Chua co schematic/layout Virtuoso cho cell moi va MUL8. Ban co so AND-array + Dadda chua lam.
- MUL8 chua duoc ghep vao ALU_CORE (MULP) o muc transistor.
