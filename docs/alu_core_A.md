# ALU lõi của A: KSA8, ADDSUB8, LOGIC8, DEC_OP, OUTMUX, FLAGS, ALU_CORE

Netlist Spectre mức transistor (CMOS tĩnh), chỉ ghép từ cell của A (`cells/A/`) và hai cell tạm của B
(`cells/_stub_B/XOR2_X1`, `XNOR2_X1`). Mọi cell đang ở cỡ X1, chưa định kích thước theo Logical Effort.
Tất cả `.scs` trong `blocks/ALU_ADD/` và `blocks/ALU_CORE/` do script sinh ra: **không sửa tay**.

| File | Nội dung |
|---|---|
| `blocks/gen_blocks.py` | Sinh netlist các khối; `--check` mô phỏng mức logic; `--count` đếm transistor |
| `blocks/gen_tb.py` | Sinh testbench từ `vectors/ksa8.csv`, `vectors/alu_core.csv` (corner NN, SS, FF) |
| `blocks/check_results.py` | Đọc kết quả psfascii, so với vector, đo độ trễ |
| `blocks/run_sims.sh` | Chạy Spectre trong VM (gọi qua `tools/vmjob.py`) |
| `blocks/ALU_ADD/KSA8.scs`, `ADDSUB8.scs` | Bộ cộng Kogge-Stone 8 bit, bộ cộng/trừ |
| `blocks/ALU_CORE/{LOGIC8,DEC_OP,OUTMUX,FLAGS,ALU_CORE}.scs` | Khối logic, giải mã OP, MUX ngõ ra, cờ, khối tổng |
| `blocks/*/tb/tb_<TOP>.scs`, `tb_<TOP>_<NN/SS/FF>.scs` | Testbench (sinh tự động) |

## 1. Chân

Thứ tự chân (Spectre nối theo vị trí), bus luôn từ bit 0 lên:

```
KSA8     A_0..A_7 B_0..B_7 CIN S_0..S_7 C7 C8 VDD VSS
ADDSUB8  A_0..A_7 B_0..B_7 SUB S_0..S_7 C7 C8 VDD VSS
ALU_CORE A_0..A_7 B_0..B_7 OP_0..OP_3 MULP_0..MULP_15 DIVQ_0..DIVQ_7 DIVR_0..DIVR_7 DIVV DIVDZ
         Y_0..Y_15 Z C V DZ VDD VSS
```

`C7` là nhớ vào bit 7, `C8` là nhớ ra của bit 7.

## 2. KSA8: Kogge-Stone, cực tính xen kẽ

Tầng 0 cho `gn = NAND(A,B)` và `pn = XNOR(A,B)` (tích cực thấp). CIN được gộp vào bit 0 bằng một gray
cell: `G0 = g0 + p0·CIN = GRY_N(gn0, pn0, !CIN)`. Sau đó ba tầng prefix đổi cực tính luân phiên nên
trên chuỗi cell prefix không có inverter:

```
            bit:  7      6      5      4      3      2      1      0
tầng 0   (thấp)  gn,pn  gn,pn  gn,pn  gn,pn  gn,pn  gn,pn  gn,pn  gn,pn  + INV(CIN)
                                                                  GRY_N -> G0 (cao)
                                                                  INV   -> G0n (thấp)
tầng 1 _N        BLK_N  BLK_N  BLK_N  BLK_N  BLK_N  BLK_N  GRY_N    .      vào thấp -> ra cao
  khoảng 1        7:6    6:5    5:4    4:3    3:2    2:1    1:0
tầng 2 _P        BLK_P  BLK_P  BLK_P  BLK_P  GRY_P  GRY_P    .      .      vào cao -> ra thấp
  khoảng 2        7:4    6:3    5:2    4:1    3:0    2:0    INV->1:0n
tầng 3 _N        GRY_N  GRY_N  GRY_N  GRY_N    .      .      .      .      vào thấp -> ra cao
                  C8=7:0 C7=6:0  5:0    4:0
tổng        S_i = pn_i XNOR c_i (c_i cao: bit 0,1,2,5,6,7)  hoặc  pn_i XOR c_i_n (c_i thấp: bit 3,4)
```

Số cell: 17 cell prefix (tầng 1: 1 gray + 6 black, tầng 2: 2 gray + 4 black, tầng 3: 4 gray)
+ 1 gray gộp CIN. Hai nhóm đã xong mà phải đi tắt qua một tầng sang tầng khác cực tính
(`G0` dùng ở tầng 1 và tầng 3, `G1:0` dùng ở tầng 3) cần INV trên nhánh rẽ đó: tổng 3 INV
(`!CIN`, `G0n`, `G1:0n`), không INV nào nằm giữa hai cell prefix nối tiếp trên cùng một bit.

`ADDSUB8`: `B_i XOR SUB` (8 XOR2) rồi vào KSA8 với `CIN = SUB`.

## 3. ALU_CORE

```
OP_3..0 ─► DEC_OP ─► SEL_AS SEL_AND SEL_OR SEL_XOR SEL_NOT SEL_MUL SEL_DIV
A,B ─► ADDSUB8 (SUB = OP_0) ─► S_7..0, C7, C8 ─┐
A,B ─► LOGIC8 ─► AND, OR, XOR, NOT ────────────┼─► OUTMUX ─► Y_15..0 ─► FLAGS ─► Z C V DZ
MULP_15..0, DIVQ_7..0, DIVR_7..0 ──────────────┘
```

- **DEC_OP**: 4 INV + 7 NAND2 (cặp OP_3/OP_2 và OP_1/OP_0) + 7 NOR2. ADD (0000) và SUB (0001) chung
  `SEL_AS`. Mã dự trữ (0110–1000, 1010, 11xx) cho mọi select = 0, nên Y = 0, Z = 1, C = V = DZ = 0
  (giống `model/alu_ref.py`).
- **LOGIC8**: mỗi bit AND = INV(NAND2), OR = INV(NOR2), XOR = XOR2, NOT = INV(A).
- **OUTMUX** (AND-OR bằng NAND-NAND): byte thấp có 7 nguồn. 6 nguồn (AND, OR, XOR, NOT, MULP_lo, DIVQ)
  đi `NAND2(sel,x)` → `NAND2` từng cặp → `NOR2`; tổng của bộ cộng (đến muộn nhất) vào thẳng
  `AOI21(SEL_AS, S_i, ·)` ở tầng 3, rồi `NAND2` ra `Y_i`. Byte cao: `NAND2(NAND2(SEL_MUL,MULP_i),
  NAND2(SEL_DIV,DIVR_i-8))`, các phép khác cho 0.
- **FLAGS**: `Z` = cây NOR2 → NAND2 → NOR2 → NAND2 → INV trên Y_15..0; `C = C8·SEL_AS`;
  `V = SEL_AS·(C7 xor C8) + SEL_DIV·DIVV`; `DZ = SEL_DIV·DIVDZ`.

## 4. Số transistor

(`python blocks/gen_blocks.py --count`, đọc từ file cell hiện tại; XOR2/XNOR2 là stub 12 transistor)

RESULTS_COUNT

## 5. Kiểm chứng

Mức logic (Python, `gen_blocks.py --check`): KSA8 vét cạn 131 072 tổ hợp (a, b, cin) đúng; ALU_CORE
6 400 vector ngẫu nhiên trên cả 16 mã OP đúng với hàm tham chiếu riêng; 498/498 dòng
`vectors/alu_core.csv` đúng.

Mô phỏng Spectre (2 ns/vector, sườn 20 ps, tải 4×INV_X1 mỗi ngõ ra, lấy mẫu ở cuối chu kỳ − 20 ps,
ngưỡng 0.6 V):

RESULTS_SIM

## 6. Chạy lại

Trên Windows, từ thư mục repo:

```
python blocks/gen_blocks.py            # sinh netlist khối
python blocks/gen_blocks.py --check    # kiểm tra mức logic (vài giây)
python blocks/gen_tb.py                # sinh testbench từ vectors/*.csv
python tools/vmjob.py --label A_sims -c "CORNERS='NN SS FF' bash blocks/run_sims.sh"
python blocks/check_results.py KSA8 out/KSA8_NN
python blocks/check_results.py ALU_CORE out/ALU_CORE_NN     # tương tự _SS, _FF
```

Trong VM có thể chạy trực tiếp:
`spectre blocks/ALU_ADD/tb/tb_KSA8_NN.scs -format psfascii -raw out/KSA8_NN`
(include trong testbench là đường dẫn tương đối theo file testbench).

## 7. Đường găng (cho bước định kích thước sau)

Độ sâu tính theo số tầng cổng (XOR2/XNOR2 stub = 2 tầng):

- KSA8: `C8` 7 tầng, `S_6` 9 tầng (sâu nhất). Đường dài nhất đi qua bit 0:
  `XNOR(pn0) → GRY_N(G0) → INV(G0n) → GRY_N(G1:0) → GRY_P(G3:0n) → GRY_N(C8)`; nhánh gộp CIN
  thêm 1 tầng so với bit khác. `S_5/S_6` thêm INV `G1:0n` trước tầng 3.
- ALU_CORE: `B → XOR(SUB) → KSA8 → S_6 → AOI21 → NAND2 → Y_6 → cây Z (5 tầng) → Z`, 18 tầng.
  Sau đó là `V` (13 tầng) và `Y_6` (13 tầng).
- Tải lớn ở cỡ X1: `SEL_*` (NOR2_X1) kéo 8–16 cổng NAND2/AOI21; `SUB = OP_0` kéo 8 XOR2 + INV + XNOR;
  `pn_i`, `gn_i` kéo 2 cell prefix + 1 XOR.

## 8. Hạn chế đã biết

- Mọi cell cỡ X1: độ trễ ở trên là của bản chưa tối ưu. Chưa định kích thước theo Logical Effort.
- XOR2/XNOR2 là stub của A (12 transistor); khi B giao cell thật cùng tên, cùng chân thì chạy lại.
- Độ trễ đo bằng nội suy tuyến tính giữa các điểm tran (`maxstep=10p`), từ 50% sườn vào chung của
  vector đến lần cắt 0.6 V cuối cùng của mọi ngõ ra trong chu kỳ; chỉ trên các cặp vector có trong
  file, không phải tìm kiếm tệ nhất vét cạn.
- Chưa có ký sinh (chưa layout), chưa đo công suất.
- Testbench include `cells/A/cells_A.scs` đúng một lần (Spectre 12.1 báo lỗi SFE-3 nếu một subckt được
  định nghĩa hai lần và không nhận `#ifndef`) cùng hai file stub XOR2/XNOR2. Include trong Spectre tính
  tương đối theo file chứa lệnh include, nên các đường dẫn `../../..` trong testbench đúng với mọi cwd.
