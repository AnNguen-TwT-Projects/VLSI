# Layout khoi (place & route Encounter EDI 13.1, gpdk090)

Khoi = cell la (A/B/C/D) dat thanh hang + di day tu dong bang Encounter; kiem tra Assura DRC/LVS tren GDS gop.

## Ket qua

| Khoi | Cell + TIE | Dien tich cell | Khoi (um) | Dien tich khoi | DRC Assura | LVS |
|---|---|---|---|---|---|---|
| ALU_CORE | 263 | 1504 um2 | 54.84 x 50.35 | 2761 um2 | 0 | Match |
| MUL8 | 130 | 2343 um2 | 64.24 x 64.15 | 4121 um2 | 0 | Match |
| DIV8 | 230 | 5170 um2 | 93.39 x 91.75 | 8569 um2 | 0 | Match |
| DIV8K (phuong an nhanh) | 718 | 5534 um2 | 96.38 x 94.51 | 9108 um2 | 0 | Match |
| DIV8F (phuong an nho) | 278 | 4121 um2 | 85.74 x 80.71 | 6920 um2 | 0 | Match |
| ALU_TOPK (= CORE + MUL8 + DIV8K) | 1131 | 9381 um2 | 121.99 x 119.35 | 14559 um2 | 0 | Match |
| ALU_TOP (ban goc, DIV8) | 643 | 9017 um2 | 124.89 x 122.11 | 15250 um2 | 0 | Match |

UTIL (mat do loi) 0.7 (ALU_TOPK 0.72, ALU_TOP 0.66), le 3 um cho vong nguon, route Metal2..Metal6. GDS: `out/pnr/<KHOI>/<KHOI>.gds`,
DEF `out/pnr/<KHOI>/<KHOI>.def`, bao cao Assura `out/assura/<KHOI>/{drc,lvs}/`.

## Luong

```
python layout/pnr/prep.py [DIV8F DIV8K ALU_TOPK]   # Windows: Verilog phang, CDL phang, LEF (tech + cell), kiem diem vao chan
python tools/vmjob.py --label pnr -c "bash layout/pnr/run_pnr.sh pnr drc lvs DIV8"   # 1 khoi / job (runner cat job > 30 phut)
#   bien: UTIL=0.7  TOPL=6 (lop route cao nhat)  PAD="BOOTH_SEL" (chua 2 site)
```

1. `layout/pnr/dump_layout.il` (Virtuoso): ghi hinh M1..M3/Via1..2/pin/bien cua 24 cell -> `out/pnr/cells.txt`.
2. `layout/pnr/prep.py`:
   - Verilog: phang khoi xuong cell la; BLK_P/BLK_N/GRY_P/GRY_N phang tiep (cell phan cap, M2 noi PI che chan GK);
     chan tin hieu noi thang VDD/VSS -> cell TIE0/TIE1 (chi la dai M1 noi ray, LVS van khop netlist goc).
   - LEF cell: pin = M1 cua pin + moi M1/Via1/M2/Via2/M3 noi voi no (cung net, router vao truc tiep); con lai OBS.
     Kiem tra tung pin co diem dat Via1+Via2 cach OBS >= 0.14.
   - `tech.lef`: ban sua gpdk090.lef (muc SPACING SAMENET khong hop le o LEF 5.7 -> dua vao tung LAYER).
   - VIA co dinh cho moi cap lop toi Metal9 (NanoRoute bat buoc; PDK chi co VIARULE GENERATE).
3. `layout/pnr/pnr.tcl` (Encounter): floorPlan (hang lat dung chung ray) -> placeDesign (dat IO) -> FILL ->
   vong nguon M2/M3 + sroute ray -> NanoRoute -> fillNotch -> createPGPin VDD/VSS -> verify -> DEF/GDS (gop GDS cell).
4. Assura DRC/LVS tren GDS (`layout/pnr/{drc,lvs}.rsf`), LVS so voi CDL phang `layout/assura/cdl/<KHOI>_flat.cdl`.

## Nhung gi phai sua de dat DRC/LVS sach (dung lai duoc cho lan sau)

| Hien tuong | Nguyen nhan | Sua |
|---|---|---|
| ENCSP-270 khong dat duoc XOR2/CAS | sroute ray truoc khi dat cell -> ray coi la vat can | dat cell truoc, nguon sau |
| NanoRoute "No via in the lib" | gpdk090.lef chi co VIARULE GENERATE | sinh VIA co dinh (prep.vias) |
| ~2800 SHORT o chan cell sinh tu dong | M2 noi bo cell phu kin chan M1 | bo sinh cell giu diem vao chan (route.access), pin gom ca M2 cung net |
| CONT.SP.1 (8331 loi) giua hai hang | tiep xuc tap cach bien 0.06 -> 0.12 qua ray chung | dat tiep xuc tap TREN bien cell (moi cell A/B/C/D, P) |
| METAL2.SP.1.1 giua hai via cung net | tech LEF bo qua SAMENET; NanoRoute de khe | tech.lef sua + fillNotch |
| METAL2.SP.1.1 khac net o BOOTH_SEL | diem vao hai chan ke nhau cung do cao | diem vao cac chan cach nhau >= 0.41 (route.access) |
| LVS "Unbound Pin VDD VSS" | GDS khong co nhan nguon | createPGPin tren vong M3 |
| Nhieu job VM chet giua chung | vm_runner gioi han 1800 s / job | 1 khoi / job |
| LVS ALU_TOP ngan mach Y_11/Y_12 (UTIL 0.72) | placeDesign dat 2 chan IO chong nhau | doi UTIL (0.66 sach). Da thu editPin (vao trai / ra phai, M3): het chong nhung them 7..11 loi METAL2.SP o BOOTH -> khong dung |
| Job bi bo "vm_runner chua chay" du runner song | giua 2 job runner chua tao log moi, chua ghi heartbeat | vmjob.py thu lai 60 s truoc khi bao loi |

## Han che

- Chua trich RC (RCX) va chua mo phong sau layout.
- Khong co thu vien thoi gian (.lib) -> dat/di day khong theo tre.
- FILL1 dung rieng vi pham Nwell/implant (chi dung giua cell khac, DRC khoi sach).
- Ket qua P&R lap lai duoc: chay lai ca 6 khoi (2026-11-11) cho cung kich thuoc, DRC 0, LVS Match.
