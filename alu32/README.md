# ALU 32 bit (so sanh voi ALU 8 bit)

Du an phu de so sanh: ALU 32 bit dung cung kien truc voi ALU_TOPK 8 bit (KSA, Booth co so 4 + cay 4:2, chia mang non-restoring moi hang 1 KSA, boc dau), duoc sinh tu mot bo sinh tham so hoa theo N: alu32/gen_alun.py. Dung lai toan bo cell cua thu vien 8 bit, khong them cell moi.

## Lenh

```
python alu32/gen_alun.py            (ghi alu32/netlist/*.scs va alu32/tb/*)
python alu32/gen_alun.py --check    (kiem chung muc logic)
python alu32/gen_alun.py --count    (transistor + do sau cell, 8 bit va 32 bit)
python alu32/gen_alun.py --res MUL32 out/MUL32_p0_NN 0   (so ket qua Spectre phan 0)
```

## Kiem chung muc logic (da chay, dat)

- ALU4: 4096/4096 to hop (16 ma OP, quet het)
- MUL8 / DIV8 sinh tu bo sinh tong quat: 65536/65536 cap (a, b) moi khoi
- ALU8: 2870/2870 vector; ALU32: 1770/1770 vector (bien x bien + ngau nhien, 8 phep + 2 ma du tru)
- Thu dot bien (doi 1 cell trong MUL32, DIV32, KSA32): bo kiem tra bat duoc ca 3 (17/40, 40/40, 13/40 vector sai)

## So sanh 8 bit / 32 bit (da do: so transistor va do sau cell)

| Khoi | Transistor 8 bit | Transistor 32 bit | Ti le | Do sau cell 8 bit | Do sau cell 32 bit |
|---|---|---|---|---|---|
| KSA8 / KSA32 | 378 | 2086 | 5.5 | 7 | 9 |
| ALU_CORE / CORE32 | 1340 | 5824 | 4.3 | 15 | 23 |
| MUL8 / MUL32 | 2168 | 30956 | 14.3 | 17 | 26 |
| DIV8K / DIV32 | 5020 | 86112 | 17.2 | 102 | 613 |
| ALU_TOPK / ALU32 | 8528 | 122892 | 14.4 | 109 | 622 |

Ghi chu: do sau cell = so cell noi tiep tren duong dai nhat (CMP42 tinh 2 tang); cay nen cua MUL32 giam chieu cao cot 17 -> 9 -> 5 -> 3 -> 2; ALU32 co 1446 INV_X4 lam cay dem cho net nhieu tai (ban 8 bit khong can).

## Tre va nang luong (Spectre, NN, 27 do C, truoc layout)

Mo phong bang Spectre APS (8 luong); APS cho ket qua trung voi Spectre thuong tren MUL32 phan 0 (1907.5 ps ca hai). Moi vector deu dung gia tri: CORE32 10/10, MUL32 9/9, DIV32 8/8. DIV32 phai dung skipdc=yes vi diem lam viec DC khong hoi tu sau 25 phut.

| Khoi | Tre 8 bit | Tre 32 bit | Ti le | Uoc luong truoc do | E/phep 8 bit | E/phep 32 bit |
|---|---|---|---|---|---|---|
| ALU_CORE / CORE32 | 781.9 ps | 1070.7 ps | 1.4 | 1.2 ns | 0.543 pJ | 4.20 pJ |
| MUL8 / MUL32 | 1427.4 ps | 1907.5 ps | 1.3 | 2.2 ns | 2.125 pJ | 23.8 pJ |
| DIV8K / DIV32 | 3975.3 ps | 20803.7 ps | 5.2 | 24 ns | 15.08 pJ | 2111 pJ |
| ALU_TOPK / ALU32 | 4660.6 ps | chua mo phong (khoang DIV32 + mux ra) | - | 24.5 ns | 20.27 pJ | chua mo phong |

- Tre 32 bit la gia tri lon nhat tren it vector (CORE32 9, MUL32 6, DIV32 4 lan chuyen) nen chua chac la truong hop xau nhat.
- E/phep 32 bit la trung binh cac phan (MUL32: 30.65, 17.99, 22.62 pJ; DIV32: 2206, 2122, 2462, 1655 pJ); bo vector khac ban 8 bit nen chi so sanh duoc bac do lon. DIV32 gom ca nang luong khoi dong tu 0 V (skipdc).
- Thoi gian mo phong: MUL32 21 ns mat 522 s (Spectre thuong) / 29 s (APS); DIV32 80 ns mat 614 den 933 s (APS).

## Layout (Encounter + Assura) va mo phong sau layout

Dung lai luong P&R cua ban 8 bit (docs/layout_blocks.md), UTIL 0.7, cung 24 cell. Ca 4 khoi dat Assura DRC 0 loi va LVS Match.

| Khoi | Cell + TIE | Dien tich cell | Khoi (um) | Dien tich khoi | Tong day | DRC Assura | LVS |
|---|---|---|---|---|---|---|---|
| CORE32 | 1219 | 6667 um2 | 104.78 x 102.79 | 10770 um2 | 17.4 mm | 0 | Match |
| MUL32 | 2506 | 35224 um2 | 231.80 x 229.75 | 53256 um2 | 96.7 mm | 0 | Match |
| DIV32 | 13352 | 94786 um2 | 375.66 x 373.27 | 140221 um2 | 312.4 mm | 0 | Match |
| ALU32 (= CORE32 + MUL32 + DIV32) | 17077 | 136677 um2 | 449.09 x 447.79 | 201098 um2 | 449.7 mm | 0 | Match |

So voi ALU_TOPK 8 bit (121.99 x 119.35 um, 14559 um2): ALU32 lon gap 13.8 lan dien tich.

Lenh chay lai (moi lenh mot job VM):

```bash
python layout/pnr/prep.py DIV8F DIV8K ALU_TOPK CORE32 MUL32 DIV32 ALU32
python tools/vmjob.py --label pnr -c "PINL=4 RETRY=3 bash layout/pnr/run_pnr.sh pnr MUL32"
python tools/vmjob.py --label drc -c "bash layout/pnr/run_pnr.sh drc lvs MUL32"
python tools/vmjob.py --label rcx -c "bash layout/pnr/run_pnr.sh rcx MUL32"
python layout/rcx2scs.py MUL32
python tools/vmjob.py --label post -c "SPOPT=+aps bash layout/run_post.sh MUL32_p0_post_NN"
python alu32/gen_alun.py --res MUL32 out/MUL32_p0_post_NN 0
```

Ba dieu phai sua so voi ban 8 bit:

- Chan IO: khoi nhieu chan (CORE32 co 270) bi placeIoPins dat len toi Metal9, via xuong sat bien gay 22 loi METAL6/7.SP va LVS ngan mach. Sua: PINL=4 (setPinAssignMode -maxLayer 4).
- NanoRoute tu dung: MUL32 (528 BOOTH_SEL) con 971 loi sau 2 vong toi uu thi NanoRoute dung (309/311 loi nam tren BOOTH_SEL). Sua: -drouteAutoStop false (con 25 loi) roi RETRY=3 (them 3 luot detailRoute, con 0).
- PAD="BOOTH_SEL BOOTH_ENC" khong giup ma con them 459 loi NW.SP.1 (khe giua cac cell) nen khong dung.

Mo phong sau layout (Assura RCX che do C, Spectre APS, NN, cung testbench va vector nhu truoc layout):

| Khoi | Vector dung | Tong tu ky sinh | tpd truoc layout | tpd sau layout | E/phep truoc | E/phep sau |
|---|---|---|---|---|---|---|
| CORE32 | 10/10 | 3518 fF (2959 net) | 1070.7 ps | 1270.3 ps | 4.20 pJ | 4.24 pJ |
| MUL32 | 9/9 | 25212 fF (15335 net) | 1907.5 ps | 2249.1 ps | 23.8 pJ | 27.2 pJ |

- MUL32 sau layout tung phan: tpd 2249.1, 1877.9, 2065.0 ps; E/phep 37.97, 18.51, 25.25 pJ.
- Tre tang 18 den 19% sau layout (ban 8 bit: ALU_CORE giam 11%, MUL8 tang 12%): day dai hon nhieu (MUL32 96.7 mm so voi khoi 8 bit), tu day lan at phan giam do dien tich khuech tan that nho hon mac dinh.
- DIV32 va ALU32 chua trich RCX / mo phong sau layout (moi phan DIV32 truoc layout da mat 10 den 16 phut).

## Nhan xet

- Cong/tru/logic tang gan tuyen tinh (4.3 lan transistor, tre do duoc 1.4 lan): KSA chi them 2 tang prefix.
- Bo nhan tang 14.3 lan transistor nhung tre do duoc chi 1.3 lan nho cay 4:2 (them 2 tang nen) va KSA64.
- Bo chia tang 17.2 lan transistor va 5.2 lan tre, 140 lan nang luong moi phep (nhieu glitch); chiem 70% transistor cua ALU32 va quyet dinh tre toan mach. Mang chia to hop khong con hop ly o 32 bit; nen chuyen sang chia tuan tu.
- Chuoi dao dau (neg) la chuoi OR noi tiep 2 tang/bit: 124 tang trong 613 tang cua DIV32; co the thay bang XOR + KSA.

## Chua lam

- Corner SS/FF va ca khoi ALU32 chua mo phong (testbench SS/FF da co trong alu32/tb). Lenh mau: `python tools/vmjob.py --label a32 --timeout 1790 -c "spectre +aps alu32/tb/tb_DIV32_p0_NN.scs -format psfascii -raw out/DIV32_p0_NN +log out/DIV32_p0_NN.log"` roi `python alu32/gen_alun.py --res DIV32 out/DIV32_p0_NN 0`.
- Moi phan DIV32 (2 vector, 80 ns) mat 10 den 16 phut; khong gop nhieu phan vao mot job (gioi han 30 phut).
- RCX va mo phong sau layout cho DIV32 va ALU32; corner SS/FF sau layout; schematic Virtuoso cho ban 32 bit.
