# So do nop (ke hoach muc 5): tre, cong suat, nang luong, EDP theo phep

Spectre MMSIM 12.1, gpdk090, VDD 1.2 V, moi ngo ra tai 4 INV_X1. `tools/power.py`:
P = VDD * |trung binh I(VVDD)| tren ca mo phong, E/phep = P * chu ky vector, EDP = E * tpd.
Tre: `blocks/check_results.py` (dong "tre theo op"), `gen_mul.py --result`, `gen_div.py --res`.

## Theo phep, corner NN

| Phep | Khoi do | T | tpd xau nhat | P trung binh | E/phep | EDP |
|---|---|---|---|---|---|---|
| ADD | ALU_CORE (2 ns/vector) | 1340 | 782 ps | 291 uW | 0.58 pJ | 0.46 pJ*ns |
| SUB | ALU_CORE | 1340 | 720 ps | 288 uW | 0.58 pJ | 0.41 pJ*ns |
| AND | ALU_CORE | 1340 | 459 ps | 247 uW | 0.49 pJ | 0.23 pJ*ns |
| OR | ALU_CORE | 1340 | 473 ps | 235 uW | 0.47 pJ | 0.22 pJ*ns |
| XOR | ALU_CORE | 1340 | 458 ps | 265 uW | 0.53 pJ | 0.24 pJ*ns |
| NOT | ALU_CORE | 1340 | 356 ps | 236 uW | 0.47 pJ | 0.17 pJ*ns |
| MUL | MUL8 Booth (3 ns/vector) | 2168 | 1.43 ns | 708 uW | 2.13 pJ | 3.03 pJ*ns |
| DIV | DIV8 + INV_X4 (12 ns/vector) | 4498 | 8.44 ns | 1.23 mW (1.53 / 1.09 / 1.06 theo 3 phan) | 14.7 pJ | 124 pJ*ns |

- ADD..NOT: E/phep tach theo cot `op` cua `vectors/alu_core.csv` (`power.py --by-op`). Tre theo op tinh moi vector
  co op do (ke ca chuyen op); TPD_WORST cua ALU_CORE van chi tinh ADD/SUB.
- MUL, DIV: so cua rieng khoi. Trong ALU_CORE, duong MUL/DIV qua bo chon ra them 353 / 497 ps
  (op9 / op11, nguon ly tuong), nen tre MUL qua ALU ~1.8 ns, DIV ~8.9 ns.
- ALU_TOP (8006 T, ca 3 khoi chay song song): 1.86 mW, 22.3 pJ moi phep bat ky (12 ns/vector) vi MUL8 va DIV8
  van chuyen mach khi op la ADD. Chan toan hang (operand isolation) cho MUL/DIV se giam phan lon muc nay; chua lam.

## Theo corner

| Khoi | NN | SS | FF | FS | SF |
|---|---|---|---|---|---|
| ALU_CORE tpd | 782 ps | 1121 ps | 602 ps | 810 ps | 859 ps |
| ALU_CORE P / E | 272 uW / 0.54 pJ | 256 uW / 0.51 pJ | 293 uW / 0.59 pJ | 288 uW / 0.58 pJ | 265 uW / 0.53 pJ |
| MUL8 tpd | 1.43 ns | 2.04 ns | 1.10 ns | 1.49 ns | 1.53 ns |
| MUL8 P / E | 708 uW / 2.13 pJ | 674 uW / 2.02 pJ | 751 uW / 2.25 pJ | 718 uW / 2.15 pJ | 713 uW / 2.14 pJ |
| DIV8 (INV_X4) tpd | 8.44 ns | 12.19 ns | 6.46 ns | - | - |
| DIV8 E (trung binh 3 phan) | 14.7 pJ | 14.0 pJ | 16.2 pJ | - | - |
| ALU_TOP tpd (12 vector) | 5.49 ns | 7.94 ns | 3.45 ns | 4.60 ns | 6.22 ns |
| ALU_TOP P / E | 1.86 mW / 22.3 pJ | 1.32 mW / 21.2 pJ | 2.00 mW / 24.0 pJ | 1.98 mW / 23.7 pJ | 1.85 mW / 22.1 pJ |

Chu ky vector: SS 16 ns cho DIV8 va ALU_TOP, con lai 12 ns (DIV8/ALU_TOP), 3 ns (MUL8), 2 ns (ALU_CORE).
E/phep phu thuoc chu ky (gom dong ro), nen so sanh giua corner chi dung cung chu ky.
FS/SF dung chu ky NN, chi de kiem tra cheo; DIV8 khong chay FS/SF rieng (da nam trong ALU_TOP FS/SF).
ALU_TOP tpd do tren 12 vector smoke (tre DIV trong ALU_TOP 5.49 ns < 8.44 ns cua DIV8 vi khong co cap vector xau nhat).

## Sau layout (RCX)

| Khoi / corner | Vector dung | tpd truoc layout | tpd sau layout | E/phep truoc | E/phep sau |
|---|---|---|---|---|---|
| ALU_CORE NN | 498/498 | 781.9 ps | 692.6 ps | 0.543 pJ | 0.460 pJ |
| MUL8 NN | 80/80 | 1427.4 ps | 1595.2 ps | 2.125 pJ | 2.154 pJ |
| DIV8K phan p0 NN | 20/20 | 3975.3 ps | 3801.7 ps | 15.08 pJ | 13.75 pJ |
| ALU_TOPK NN | 12/12 | 4660.6 ps | 3583.0 ps | 20.27 pJ | 17.92 pJ |
| ALU_TOPK SS (16 ns/vector) | 12/12 | 6723.9 ps | 5143.0 ps | 18.38 pJ | 16.76 pJ |
| ALU_TOPK FF | 12/12 | 3591.7 ps | 2745.8 ps | 21.75 pJ | 19.74 pJ |

Chi tiet va lenh chay lai: `docs/layout_blocks.md`.
