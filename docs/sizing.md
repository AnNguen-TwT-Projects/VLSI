# Dinh kich thuoc duong gang bang Logical Effort (phan cua C)

## Chon duong can toi uu

| Khoi | tpd NN | Ghi chu |
|---|---|---|
| ALU_CORE | 0.78 ns | |
| MUL8 | 1.43 ns | |
| DIV8 | 9.37 ns | quyet dinh chu ky cua ca ALU_TOP |

Toi uu MUL8 khong doi chu ky ALU vi DIV8 cham gap 6 lan, nen Logical Effort ap dung cho DIV8 truoc.

## Mo hinh

- Don vi dien dung: dien dung cong cua INV_X1, Cin = 0.12 + 0.24 = 0.36 um be rong cong.
- Tre mot tang: d = g*h + p (don vi tau). Tau duoc uoc tu FO4 cua INV_X1 o NN (34 ps, `docs/cells_A_results.md`): FO4 = 5 tau, nen tau ~ 7 ps.
- Chan vao cua XOR2_X1 (stub 12T): 0.12 + 0.24 + 0.24 + 0.48 = 1.08 um = 3 Cinv.
- Chan vao cua NAND2_X1: 0.24 + 0.24 = 0.48 um, g = 4/3.

## Duong gang cua mot hang chia

Hang i cua mang non-restoring cho q cua hang truoc (net `qu`). `qu` di vao:
- chan T cua 9 CAS_X1 (XOR2 D^T),
- CI cua CAS bit 0 (XOR2 + NAND2),
- bo dao dau Q.

Tai cua `qu` xap xi 9*1.08 + 1.56 + ~2.4 = 13.9 um. Tai nay do mot INV_X1 (0.36 um) keo:

| Tang | g | h | p | d (tau) |
|---|---|---|---|---|
| XOR2 ra S_8 -> INV_X1 | ~4 | 0.36/1.08 = 0.33 | ~4 | 5.3 |
| INV_X1 -> qu (13.9 um) | 1 | 38.6 | 1 | 39.6 |
| **Tong** | | | | **~45 tau ~ 0.31 ns / hang** |

Tang INV la diem nghen. Phai giu cuc tinh (dung 1 tang dao), nen toi uu 2 tang XOR -> INV:

- F = g_xor * g_inv * H = 4 * 1 * (13.9 / 1.08) = 51.5; f_toi_uu = sqrt(51.5) = 7.2.
- Tang XOR: f = g_xor * Cin_inv / 1.08 = 7.2, nen Cin_inv toi uu = 7.2 * 1.08 / 4 = 1.94 um (~INV_X5).
- Chon INV_X4 (Cin 1.44 um), co san trong ban "buffer" cua C:
  - XOR: h = 1.44/1.08 = 1.33, d = 5.3 + 4 = 9.3 tau.
  - INV_X4: h = 13.9/1.44 = 9.65, d = 10.65 tau.
  - Tong ~ 20 tau (so voi 45 tau). X5 chi tot hon INV_X4 0.6 tau.

Uoc luong loi: ~25 tau * 7 ps * 7 hang (hang cuoi ra Q_0, giu INV_X1) ~ 1.2 ns tren 9.37 ns.

## Chuoi nho (khong doi)

Moi bit cua CAS: CI -> NAND2 (pc_n) -> NAND2 (CO) -> CI bit sau.
- Tai CO = XOR2 + NAND2 = 1.56 um.
- d = (4/3 * 1 + 2) + (4/3 * 3.25 + 2) = 3.3 + 6.3 = 9.6 tau / bit.

Duong nay da gan toi uu cho hai tang NAND (f ~ 1.3 va 4.3). Tang kich thuoc NAND trong CAS chi bot ~1-2 tau/bit nhung lam nang tai cho bit truoc. Muon nhanh hon ro ret phai doi kien truc (carry-lookahead trong moi hang, hoac chia nhieu chu ky), khong phai doi kich thuoc.

## Thuc hien

- `cells/C/INV_X4` do `blocks/ALU_MUL/gen_mul.py` sinh ra.
- Trong `blocks/ALU_DIV/gen_div.py`, q cua hang 0..6 dung INV_X4; Q_0 (hang 7) giu INV_X1.

## Ket qua Spectre

DIV8 NN, cung 60 vector, 12 ns/vector (out/DIV8_pK_NN truoc, out/DIV8X4_pK_NN sau):

| Phan | Truoc (INV_X1) | Sau (INV_X4) |
|---|---|---|
| p0 | 9.37 ns | 8.44 ns |
| p1 | 4.45 ns | 4.26 ns |
| p2 | 6.13 ns | 4.46 ns |
| **Xau nhat** | **9.37 ns** | **8.44 ns (-0.93 ns, -10%)** |

Ca 60/60 vector dung; muc cong 65536/65536. Loi do duoc (0.93 ns) nho hon uoc luong 1.2 ns vi mo hinh bo qua
dien dung day va tang XOR2 cua stub B. So transistor khong doi (4498 T, INV_X4 van 2 T, chi rong hon).
Cong suat NN ban INV_X4 (`tools/power.py`, 12 ns/vector): 1.53 / 1.09 / 1.06 mW cho p0 / p1 / p2,
trung binh ~1.23 mW, ~14.7 pJ/phep. Ban truoc khong luu VVDD:p nen chua co so de so sanh cong suat.
