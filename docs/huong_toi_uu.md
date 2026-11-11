# Huong toi uu: vua nhanh vua it dien tich

## Khoi nao dang ganh ca hai

| Khoi | Transistor | Dien tich cell | Dien tich khoi (P&R, UTIL 0.7) | tpd NN |
|---|---|---|---|---|
| ALU_CORE | 1340 | 1504 um2 | 2761 um2 (54.8 x 50.4) | 0.78 ns |
| MUL8 (Booth) | 2168 | 2343 um2 | 4121 um2 (64.2 x 64.2) | 1.43 ns |
| DIV8 | 4498 | 5170 um2 | 8569 um2 (93.4 x 91.8) | 8.44 ns |

DIV8 chiem 57% dien tich cell va quyet dinh tre cua ca ALU. Rieng 80 CAS_X1 (55.1 um2 moi cai) la 85% DIV8.
Toi uu o dau khac (MUL8, ALU_CORE) khong doi duoc ket qua chung -> tap trung DIV8.

## Vi sao DIV8 cham

Mang non-restoring 8 hang x 9 CAS. T cua hang i+1 la dau (S8) cua hang i, ma S8 chi xong khi carry
gon het 9 bit; hang i+1 lai bat dau carry tu T. Tre ~ 8 x 9 tang carry (~117 ps / CAS) = O(n^2).
Chi lam nhanh rieng bit dau (lookahead cho S8) KHONG giup: hang i+1 van can moi bit tong cua hang i,
ma cac bit nay van gon carry. Phai lam moi hang thanh bo cong log.

## Hai phuong an da dung va do (cung kien truc, cung sign wrapper)

`python blocks/ALU_DIV/gen_div.py --variant fa|ksa` -> `blocks/ALU_DIV/DIV8F.scs`, `DIV8K.scs`, tb.

- DIV8F (nho): CAS = XOR2(D, T) + FA_X1 guong (40 T thay 48 T); hang sua phan du = FA_X1.
- DIV8K (nhanh): moi hang = 8 XOR2 (D ^ T) + KSA8 (Kogge-Stone san co cua ALU_CORE, CIN = T)
  + bit 8 = x8 ^ T ^ C8 (2 XOR2); hang sua phan du = KSA8.

Ca hai: 65536/65536 cap (a, b) dung o muc cong; Spectre NN 60/60 vector dung; P&R Encounter DRC 0, LVS Match.

| | DIV8 | DIV8F | DIV8K |
|---|---|---|---|
| Transistor | 4498 | 3666 (-18%) | 5020 (+12%) |
| Dien tich cell | 5170 um2 | 4121 um2 (-20%) | 5534 um2 (+7%) |
| Dien tich khoi P&R | 8569 um2 | 6920 um2 (-19%) | 9108 um2 (+6%) |
| tpd NN (p0 / p1 / p2) | 8.44 / 4.26 / 4.46 ns | 10.16 / 8.89 / 7.70 ns | 3.98 / 3.96 / 3.93 ns |
| **tpd NN xau nhat** | **8.44 ns** | **10.16 ns (+20%)** | **3.98 ns (-53%)** |
| E/phep (12 ns/vector, tb 3 phan) | 14.7 pJ | 11.3 pJ | 13.9 pJ |
| EDP | 124 pJ*ns | 115 pJ*ns | 55 pJ*ns |
| Dien tich x tre (khoi) | 72.3 nghin um2*ns | 70.3 | 36.2 |

Ghi chu do: tre = lan cat 0.6 V cuoi cung cua ngo ra trong chu ky (gen_div.check_res), NN, 12 ns/vector,
tai 4 INV_X1. DIV8F p0 cham hon vi FA_X1 guong co cong carry phuc (LE ~2) + INV o moi bit, dai hon
NAND2-NAND2 cua CAS_X1. DIV8K: tre gan nhu khong phu thuoc du lieu (3.93..3.98 ns) vi moi hang co
cung so tang (XOR + KSA 3 tang + XOR).

Theo corner (tre xau nhat 3 phan, 60 vector moi corner, SS 16 ns/vector):

| Corner | DIV8 (INV_X4) | DIV8K | Ty le |
|---|---|---|---|
| NN | 8.44 ns | 3.98 ns | 2.12x |
| SS | 12.19 ns | 5.75 ns | 2.12x |
| FF | 6.46 ns | 3.04 ns | 2.13x |

DIV8K E/phep: SS 13.2 pJ (16 ns/vector), FF 14.9 pJ (DIV8: 14.0 / 16.2 pJ).

ALU_TOPK (= ALU_CORE + MUL8 + DIV8K, 8528 T): muc logic 595/595 dong `vectors/alu_full.csv`; Spectre 12 vector
smoke NN / FF dung het, tre xau nhat 4.66 / 3.59 ns (ALU_TOP: 5.49 / 3.45 ns), E/phep NN 20.3 pJ (ALU_TOP 22.3 pJ).
Smoke 12 vector khong chua cap DIV xau nhat; tre DIV that cua ALU_TOPK theo DIV8K: ~4 ns (ALU_TOP: ~8.4 ns).
SS (16 ns/vector): 12/12 dung, tre xau nhat 6.72 ns (ALU_TOP: 7.94 ns), E/phep 18.4 pJ. Layout ALU_TOPK: 121.99 x 119.35 um, DRC 0, LVS Match (`docs/layout_blocks.md`).
`python blocks/ALU_TOP/gen_top.py --div ksa [--check | --res out/ALU_TOPK_NN]`.

## Ket luan

- DIV8K: nhanh gap 2.1 lan, dien tich khoi chi +6%, E/phep giam nhe -> dien tich x tre giam 50%,
  EDP giam 56%. Day la huong "vua nhanh vua it dien tich" tot nhat: khong tang dien tich dang ke ma
  cat duoc nua tre cua ca ALU (DIV la duong toi).
- DIV8F: chi co loi khi chi can dien tich (-19%), nhung cham hon 20% -> khong chon.
- Huong tiep (chua lam): ket hop DIV8K voi CAS/XOR nho hon (XOR2 12 T dang la 1/4 dien tich hang), va
  nen cell do bo sinh tu dong (bo cot ngat giua cac tang, ~10-15%). Chan toan hang (operand isolation)
  cho MUL8/DIV8 giam cong suat ALU_TOP (hien moi phep ~22 pJ vi ca 3 khoi cung chuyen mach).
