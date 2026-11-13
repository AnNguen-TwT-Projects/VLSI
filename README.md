# ALU 8 bit và ALU 32 bit ở mức transistor (gpdk090, Cadence)

ALU tổ hợp CMOS tĩnh, nguồn 1,2 V, có ADD, SUB, AND, OR, XOR, NOT, nhân có dấu, chia có dấu và bốn cờ Z, C, V, DZ.
Kho này chứa toàn bộ thiết kế từ cell đến layout, xếp theo từng tầng, cùng các script shell để kiểm tra lại mọi kết quả
trong máy ảo Cadence. Không cần Python: chỉ dùng `bash`, `awk`, `sed` và các công cụ Cadence.

Tổng quan đề tài: [TONG_QUAN_DE_TAI.docx](TONG_QUAN_DE_TAI.docx).

## Tập lệnh

| OP[3:0] | Lệnh | Y (8 bit: Y[15:0], 32 bit: Y[63:0]) |
|---|---|---|
| 0000 | ADD | A + B |
| 0001 | SUB | A − B |
| 0010 | AND | A & B |
| 0011 | OR | A \| B |
| 0100 | XOR | A ^ B |
| 0101 | NOT | ~A |
| 1001 | MUL có dấu | A × B |
| 1011 | DIV có dấu | {phần dư, thương}, làm tròn về 0, phần dư mang dấu số bị chia |

Cờ: Z = kết quả bằng 0; C = nhớ ra (SUB: C = 1 là không mượn); V = tràn có dấu của ADD/SUB, hoặc chia số nhỏ nhất cho −1;
DZ = chia cho 0.

## Cấu trúc thư mục theo tầng

```
tang1_cell/                 Tầng 1: 18 cell dùng chung cho cả hai bản
  cells.scs                   include một lần là có đủ 18 cell
  <CELL>/<CELL>.scs           netlist transistor của cell
  <CELL>/tb_<CELL>.scs        testbench: duyệt mọi cạnh của khối lập phương ngõ vào, tải FO4
  <CELL>/tb_<CELL>.exp        bảng chân trị mong đợi
ALU_8bit/
  ALU_8bit.scs                include mọi khối tầng 2, 3, 4
  tang2_khoi_con/             KSA8, ADDSUB8, LOGIC8, DEC_OP, OUTMUX, FLAGS
  tang3_khoi/                 ALU_CORE, MUL8, DIV8K
  tang4_top/                  ALU_TOPK  (= ALU_CORE + MUL8 + DIV8K)
  tb/                         tb_<KHOI>[_pK].scs  thân testbench (vector, nguồn, tải)
                              tb_<KHOI>[_pK]_NN|SS|FF.scs  file chạy theo corner
                              tb_<KHOI>[_pK].exp  giá trị mong đợi của từng ngõ ra ở cuối từng vector
                              demo/  testbench demo A, B, OP thập phân + file kích thích cho ADE
  layout/verilog/             netlist phẳng cho Encounter
  layout/cdl/                 netlist phẳng cho Assura LVS
  layout/gds/                 GDS của ALU_CORE, MUL8, DIV8K, ALU_TOPK (đã DRC 0 lỗi, LVS khớp)
  layout/rcx/                 netlist sau layout (tụ ký sinh) + testbench sau layout theo corner
ALU_32bit/                  cùng bố cục: KSA32, KSA64, ADDSUB32, LOGIC32, DEC_OP, OUTMUX32, FLAGS32 |
                            CORE32, MUL32, DIV32 | ALU32
virtuoso/                   SKILL vẽ schematic + symbol (sch_*.il) và layout cell (layout_cells_*.il),
                            run file Assura cho từng cell, CDL từng cell
pnr/                        Encounter (pnr.tcl), LEF, GDS các thư viện cell, run file Assura cho khối
scripts/                    run_cells.sh, run_sim.sh, check.awk, final_value.awk, rcx2scs.sh
```

Thư viện Virtuoso tạo ra: `ALU_CELLS_A` (cổng cơ bản, ô tiền tố), `ALU_CELLS_X` (XOR2, XNOR2), `ALU_CELLS_B` (BOOTH_ENC,
BOOTH_SEL, CMP42), `ALU_CELLS_C` (FA, HA, INV_X4), `ALU_CELLS_D` (CAS), `ALU_CELLS_P` (FILL, TIE cho P&R);
`ALU_ADD`, `ALU_CORE`, `ALU_MUL`, `ALU_DIV`, `ALU_TOP` (8 bit); `ALU_32BIT` (32 bit).

## Chuẩn bị (trong máy ảo Cadence)

1. Chép thư mục kho vào máy ảo (hoặc mở qua thư mục chia sẻ), `cd` vào thư mục gốc của kho.
2. Nạp môi trường Cadence như thường lệ (để có `spectre`, `virtuoso`, `assura`, `encounter`, `strmout` trong PATH).
3. Đường dẫn PDK được dùng cố định: `/home/buet/cadence/gpdk090_v4.6`. Nếu máy khác, đổi một lần:
   ```bash
   grep -rl /home/buet/cadence/gpdk090_v4.6 . | xargs sed -i 's|/home/buet/cadence/gpdk090_v4.6|<PDK cua ban>|g'
   ```

Mọi kết quả ghi vào thư mục `out/` (không đưa lên git). Mỗi script trả mã thoát 0 khi mọi kiểm tra đạt.

## Bước 1. Kiểm tra 18 cell (tầng 1)

```bash
bash scripts/run_cells.sh NN SS FF
```

Mỗi dòng in kết quả một cell ở một corner, ví dụ `NN FA_X1  PASS: 25/25 vector dung, 0 sai;tre lon nhat 170.6 ps;`.
Cuối cùng phải là `TAT CA CELL: PASS`. Mỗi vector được lấy mẫu ở cuối chu kỳ và phải cách ray nguồn không quá 10% VDD.
Chạy vài cell: `ONLY="INV_X1 FA_X1" bash scripts/run_cells.sh NN`. Thời gian: khoảng 6 phút cho 3 corner.

## Bước 2. Mô phỏng các khối và cả ALU (tầng 2 đến 4)

```bash
bash scripts/run_sim.sh ALU_8bit/tb/tb_*_NN.scs
```

Mỗi testbench in ra:

```
== tb_ALU_TOPK_NN
spectre completes with 0 errors, 5 warnings, and 5 notices.
PASS: 12/12 vector dung, 0 sai
  tre lon nhat  4653.7 ps  (vector 9 [op=11 a=128 b=255], truoc do [op=9 a=255 b=127], ngo ra Y_15)
  cong suat TB  1678.1 uW   nang luong/phep  20.137 pJ
```

- Đúng/sai: mỗi ngõ ra được lấy mẫu 20 ps trước cuối chu kỳ, ngưỡng 0,6 V, so với file `.exp`.
- Trễ: từ giữa sườn vào đến lần cắt 0,6 V cuối cùng của bất kỳ ngõ ra nào trong chu kỳ.
- Năng lượng mỗi phép = VDD × |dòng nguồn trung bình| × chu kỳ.
- Corner khác: thay `_NN` bằng `_SS` hoặc `_FF` (corner SS dùng chu kỳ dài hơn, có file `.exp` riêng `_slow`).
- Khối lớn nên dùng Spectre APS (nhiều luồng, kết quả trùng Spectre thường): thêm `APS=1` trước lệnh.

ALU 32 bit:

```bash
APS=1 bash scripts/run_sim.sh ALU_32bit/tb/tb_CORE32_p0_NN.scs ALU_32bit/tb/tb_MUL32_p*_NN.scs
APS=1 bash scripts/run_sim.sh ALU_32bit/tb/tb_DIV32_p0_NN.scs      # mỗi phần DIV32 mất 10 đến 16 phút
```

Bộ chia 32 bit (86 nghìn transistor) không tìm được điểm làm việc DC, nên testbench của nó bỏ bước DC (`skipdc=yes`);
vector đầu mỗi phần chỉ để mạch ổn định.

### Demo một phép tính

```bash
bash scripts/run_sim.sh ALU_8bit/tb/demo/tb_demo_ALU_TOPK.scs
```

In giá trị cuối của các ngõ ra, ví dụ −7 / 2 cho `Y[15:0] = 0xFFFD` (phần dư −1 ở byte cao, thương −3 ở byte thấp).
Đổi phép tính: sửa dòng `parameters A=-7 B=2 OP=11` trong file demo (A, B thập phân có dấu, OP thập phân theo bảng trên).

Trong Virtuoso ADE L: mở schematic `ALU_TOP/ALU_TOPK` (sau bước 4), Setup → Model Libraries chọn gpdk090.scs section NN,
Setup → Simulation Files → Stimulus File chọn `ALU_8bit/tb/demo/demo_stim.scs`, thêm biến thiết kế A, B, OP,
phân tích tran 8 ns, vẽ Y_0..Y_15, Z, C, V, DZ.

## Bước 3. Mô phỏng sau layout

Netlist sau layout (trích tụ ký sinh bằng Assura RCX) đã có trong `layout/rcx/`, dùng lại đúng testbench trước layout:

```bash
bash scripts/run_sim.sh ALU_8bit/layout/rcx/tb_ALU_TOPK_post_NN.scs
APS=1 bash scripts/run_sim.sh ALU_32bit/layout/rcx/tb_CORE32_p0_post_NN.scs
```

Tự trích lại ký sinh từ GDS rồi đổi sang Spectre:

```bash
bash pnr/run_pnr.sh rcx ALU_TOPK          # -> out/assura/ALU_TOPK/rcx/ALU_TOPK_rcx.sp
bash scripts/rcx2scs.sh ALU_TOPK          # -> ALU_8bit/layout/rcx/ALU_TOPK_rcx.scs
```

## Bước 4. Schematic trong Virtuoso

```bash
bash virtuoso/run_schematic.sh                       # 18 cell + ALU 8 bit
bash virtuoso/run_schematic.sh sch_ALU_32bit.il      # ALU 32 bit (sau lệnh trên)
```

Thư viện được tạo trong `~/ALU_PROJ` (đổi bằng biến `ALU_PROJ`). Mở bằng `cd ~/ALU_PROJ && virtuoso &`.
Thành công khi log in `SB_SUMMARY cells=... errors=0`.

## Bước 5. Layout cell, DRC, LVS

```bash
bash virtuoso/run_layout_cell.sh                     # vẽ layout 18 cell + FILL/TIE, DRC, LVS từng cell, xuất GDS
bash virtuoso/run_layout_cell.sh drc lvs FA_X1       # chỉ vài bước, vài cell
```

Mỗi cell phải có `DRC <CELL>: 0 luat vi pham` và `LVS <CELL>: Schematic and Layout Match`.

## Bước 6. Layout khối (place & route), DRC, LVS

Kiểm tra GDS có sẵn:

```bash
bash pnr/run_pnr.sh drc lvs ALU_TOPK
bash pnr/run_pnr.sh drc lvs ALU32                    # khoảng 2 phút
```

Chạy lại place & route bằng Encounter rồi kiểm tra GDS mới:

```bash
bash pnr/run_pnr.sh pnr drc lvs ALU_CORE
UTIL=0.72 bash pnr/run_pnr.sh pnr drc lvs ALU_TOPK
PINL=4 RETRY=3 bash pnr/run_pnr.sh pnr drc lvs MUL32
```

| Biến | Ý nghĩa |
|---|---|
| UTIL | mật độ lõi, mặc định 0.7 (ALU_TOPK dùng 0.72) |
| PINL | lớp kim loại cao nhất cho chân IO; các khối 32 bit dùng 4 |
| RETRY | số lượt `detailRoute` thêm; các khối 32 bit dùng 3 |

Kết quả đạt: `DRC <KHOI>: 0 luat vi pham` và `LVS <KHOI>: Schematic and Layout Match`.

## Kết quả tham chiếu (corner NN, 27 °C)

| Khối | Vector đúng | Trễ trước layout | Trễ sau layout | Năng lượng mỗi phép | Kích thước layout (µm) |
|---|---|---|---|---|---|
| KSA8 | 148/148 | 363,1 ps | | 0,21 pJ | |
| ALU_CORE | 498/498 | 781,9 ps | 692,6 ps | 0,54 pJ | 54,84 × 50,35 |
| MUL8 | 80/80 | 1 427,4 ps | 1 595,2 ps | 2,13 pJ | 64,24 × 64,15 |
| DIV8K (3 phần) | 60/60 | 3 975,2 ps | 3 801,7 ps | 13,3 – 15,1 pJ | 96,38 × 94,51 |
| ALU_TOPK | 12/12 | 4 653,7 ps | 3 582,8 ps | 20,1 pJ | 121,99 × 119,35 |
| CORE32 | 10/10 | 1 070,7 ps | 1 270,3 ps | 4,20 pJ | 104,78 × 102,79 |
| MUL32 (3 phần) | 9/9 | 1 907,5 ps | 2 249,1 ps | 18,0 – 30,7 pJ | 231,80 × 229,75 |
| DIV32 (4 phần) | 8/8 | 20 803,7 ps | chưa trích | 1 655 – 2 462 pJ | 375,66 × 373,27 |
| ALU32 | chưa mô phỏng | | | | 449,09 × 447,79 |

Mọi khối có layout đều đạt DRC 0 lỗi và LVS khớp. Trễ đo trên một số ít vector nên chưa chắc là trường hợp xấu nhất;
năng lượng của DIV32 gồm cả phần khởi động từ 0 V do bỏ bước DC.

## Giới hạn

- Mạch thuần tổ hợp, chưa có phép dịch.
- Place & route không dùng thư viện thời gian; RCX chỉ trích tụ, chưa trích điện trở dây.
- DIV32 và ALU32 chưa mô phỏng sau layout; ALU32 chưa mô phỏng Spectre toàn khối.
