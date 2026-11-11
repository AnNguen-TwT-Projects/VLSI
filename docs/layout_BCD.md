# Layout cell B/C/D (gpdk090)

Sinh tu dong tu netlist `.scs` bang `layout/gen_layout_cells.py` -> `layout/gen_layout_BCD.il` (SKILL).
Cung khuon voi cell A (`docs/handoff_layout_A.md`): cao 2.76 um, buoc cot 0.27 um, ray VSS/VDD Metal1,
hang n tam y = 0.64, hang p tam y = 2.00, chan Metal1 (pin + label). Ghep sat duoc voi cell A.

## Ket qua (Assura 4.1, gpdk090 drc.rul / extract.rul)

| Thu vien / cell | T (sau chia finger) | Cot | Rong x cao (um) | Dien tich (um2) | DRC | LVS |
|---|---|---|---|---|---|---|
| ALU_STUB_B/XOR2_X1 | 12 | 17 | 4.86 x 2.76 | 13.41 | 0 loi | Match |
| ALU_STUB_B/XNOR2_X1 | 12 | 17 | 4.86 x 2.76 | 13.41 | 0 loi | Match |
| ALU_CELLS_B/BOOTH_ENC | 28 | 39 | 10.80 x 2.76 | 29.81 | 0 loi | Match |
| ALU_CELLS_B/BOOTH_SEL | 20 | 27 | 7.56 x 2.76 | 20.87 | 0 loi | Match |
| ALU_CELLS_B/CMP42 | 68 (56) | 83 | 22.68 x 2.76 | 62.60 | 0 loi | Match |
| ALU_CELLS_C/FA_X1 | 34 (28) | 41 | 11.34 x 2.76 | 31.30 | 0 loi | Match |
| ALU_CELLS_C/HA_X1 | 18 | 25 | 7.02 x 2.76 | 19.38 | 0 loi | Match |
| ALU_CELLS_C/INV_X4 | 4 (2) | 5 | 1.62 x 2.76 | 4.47 | 0 loi | Match |
| ALU_CELLS_D/CAS_X1 | 48 | 73 | 19.98 x 2.76 | 55.14 | 0 loi | Match |

GDS: `out/gds/ALU_STUB_B.gds`, `ALU_CELLS_B.gds`, `ALU_CELLS_C.gds`, `ALU_CELLS_D.gds` (strmout 0 loi).
Bao cao: `out/assura/<CELL>/{drc,lvs}/`.

## Cach sinh

1. Phang hoa netlist (CAS_X1 = 3 XOR2 + 3 NAND2 -> 48 T phang). Chia finger: nMOS > 0.24 um, pMOS > 0.48 um
   (nMOS 0.36 dat o y = 0.64 thi dau poly cach oxide tap VSS 0.04 < 0.10). Assura LVS gop MOS song song
   (`compare.rul`, `parallelMOS`) nen netlist so sanh van la ban goc.
2. Tach tang: cac transistor noi nhau qua khuech tan (khong tinh ray) ~ mot cong CMOS.
   Moi tang: tim vet Euler ngau nhien cho hang n va hang p, can hai hang bang quy hoach dong
   (cot cong chung poly khi cung tin hieu; neu khong, hang kia de oxide noi tiep "PASS" va poly chi o mot hang,
   hoac dut khuech tan).
3. Xep thu tu tang (1500 mau ngau nhien, lat trai/phai) va chon ban co mat do net it nhat roi it cot nhat.
4. Di day: moi net M1 doc tren cot cua no; ngang tren 7 track (y 0.50..2.24, buoc 0.29) o Metal2,
   hoac Metal3 (Via2 chong len Via1, dem M2 0.54 um) khi Metal2 het cho. Cot ke nhau cung net noi bang cau M1
   (Via1 cach nhau >= 0.15 nen khong dat hai via o hai cot ke nhau).
   Kiem tra so bo trong Python: M1 cung cot khac net cach >= 0.12, M2/M3 cung track cach >= 0.14,
   dien tich M1 >= 0.07 (doan >= 0.48 um), M2/M3 >= 0.08 (>= 0.54 um), M2/M3 cach bien cell 0.07.
   Chon track bang quay lui.

5. Diem vao chan cho P&R khoi (2026-11-11): moi cong phai co mot diem tren M1 cua no ma dem Via1 (M2 0.15x0.27)
   va Via2 (M3 0.27x0.15) cach M2/M3 net khac >= 0.14 (`route.access`); pin ve dung tai diem do. Khong co diem ->
   thu cach di day khac (`tries=20`). Truoc khi them rang buoc nay, Encounter bao ~2800 loi SHORT o chan cell.
6. Khung cell: tiep xuc tap nam tren bien cell (giong `docs/handoff_layout_A.md`), de hai hang lat dung chung ray
   khong vi pham CONT.SP.1.

Mat do net (so net nhieu cot cat qua mot cot) quyet dinh co di day duoc khong: dat theo tang giam FA_X1
tu 8 xuong 7, CMP42 tu 15 xuong 8; CMP42 can Metal3 cho 3 net.

## Lenh

```
python layout/gen_layout_cells.py                # ~5 phut, ghi layout/gen_layout_BCD.il
python layout/gen_layout_cells.py FA_X1 -v       # so do ASCII cua mot cell (khong ghi file)
python layout/scs2cdl.py                         # CDL cho LVS (ca cell A, B, C, D)
python tools/vmjob.py --label lay_bcd --timeout 1800 -c "GEN=layout/gen_layout_BCD.il \
  GDSLIBS='ALU_STUB_B ALU_CELLS_B ALU_CELLS_C ALU_CELLS_D' bash layout/run_layout_A.sh gen drc lvs gds \
  ALU_STUB_B/XOR2_X1 ALU_STUB_B/XNOR2_X1 ALU_CELLS_B/BOOTH_ENC ALU_CELLS_B/BOOTH_SEL ALU_CELLS_B/CMP42 \
  ALU_CELLS_C/FA_X1 ALU_CELLS_C/HA_X1 ALU_CELLS_C/INV_X4 ALU_CELLS_D/CAS_X1"
```

## Han che

- Rong hon layout ve tay: moi tang cach nhau mot cot dut khuech tan, chieu ngang theo so cot cong
  (FA_X1 31.3 um2). DRC/LVS sach nhung chua toi uu dien tich.
- CAS_X1 la layout phang (khong dat instance XOR2/NAND2); LVS so voi CDL phan cap van khop.
- Chua trich RC (RCX) va chua mo phong sau layout.
- O dia VM gan day (Cadence chiem 29/33 GB): `run_layout_A.sh` xoa thu muc chay Assura sau khi chep bao cao
  (dat `KEEP=1` de giu).
