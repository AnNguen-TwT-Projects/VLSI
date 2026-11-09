# Cell của A (`ALU_CELLS_A`) và cell tạm của B (`ALU_STUB_B`)

Quy ước chân, kích thước, linh kiện: `docs/CONVENTIONS.md` mục 3-4. L = 0.1 um cho mọi transistor.

## 1. Danh sách cell

| Cell | Chân (thứ tự subckt) | Số transistor | nMOS W (um) | pMOS W (um) | Netlist |
|---|---|---|---|---|---|
| INV_X1 | A Y VDD VSS | 2 | 0.12 | 0.24 | `cells/A/INV_X1/INV_X1.scs` |
| NAND2_X1 | A B Y VDD VSS | 4 | 0.24, 0.24 (nối tiếp) | 0.24, 0.24 | `cells/A/NAND2_X1/NAND2_X1.scs` |
| NOR2_X1 | A B Y VDD VSS | 4 | 0.12, 0.12 | 0.48, 0.48 (nối tiếp) | `cells/A/NOR2_X1/NOR2_X1.scs` |
| AOI21_X1 | A1 A2 B Y VDD VSS | 6 | A1, A2: 0.24; B: 0.12 | 0.48 x3 | `cells/A/AOI21_X1/AOI21_X1.scs` |
| OAI21_X1 | A1 A2 B Y VDD VSS | 6 | 0.24 x3 | A1, A2: 0.48; B: 0.24 | `cells/A/OAI21_X1/OAI21_X1.scs` |
| BLK_P | GI PI GK PK GON PON VDD VSS | 10 | AOI21(A1=PI, A2=GK, B=GI) + NAND2 | | `cells/A/BLK_P/BLK_P.scs` |
| BLK_N | GIN PIN GKN PKN GO PO VDD VSS | 10 | OAI21(A1=PIN, A2=GKN, B=GIN) + NOR2 | | `cells/A/BLK_N/BLK_N.scs` |
| GRY_P | GI PI GK GON VDD VSS | 6 | AOI21 | | `cells/A/GRY_P/GRY_P.scs` |
| GRY_N | GIN PIN GKN GO VDD VSS | 6 | OAI21 | | `cells/A/GRY_N/GRY_N.scs` |
| XOR2_X1 (STUB, của B) | A B Y VDD VSS | 12 | đảo 0.12; nhánh 0.24 | đảo 0.24; nhánh 0.48 | `cells/_stub_B/XOR2_X1/XOR2_X1.scs` |
| XNOR2_X1 (STUB, của B) | A B Y VDD VSS | 12 | đảo 0.12; nhánh 0.24 | đảo 0.24; nhánh 0.48 | `cells/_stub_B/XNOR2_X1/XNOR2_X1.scs` |

BLK/GRY là cell phân cấp: netlist `include` AOI21/OAI21/NAND2/NOR2 (đường dẫn tương đối theo file,
Spectre tự tìm đúng). Cell XOR2/XNOR2 là **cell tạm**: khi B giao cell thật cùng tên, cùng thứ tự chân
thì thay thế, không phải sửa gì ở phía A.

## 2. Kết quả mô phỏng

RESULTS_PLACEHOLDER

## 3. Schematic và symbol trong Virtuoso

SCH_PLACEHOLDER

## 4. Chạy lại (từ thư mục repo trên Windows)

```
# 1) Testbench (sinh lại tb_<CELL>.scs từ netlist; chỉ cần khi sửa cell)
python cells/A/check_cells.py gen
# 2) Mô phỏng 3 corner trong VM, rồi kiểm tra bảng chân lý + đo trễ trên Windows
python tools/vmjob.py --label cells -c "bash cells/A/run_cells.sh NN FF SS"
python cells/A/check_cells.py check
# 3) Sinh SKILL từ netlist, vẽ schematic + symbol trong VM, netlist lại bằng si, xuất tgz
python tools/scs2skill.py -o skill/gen_cells_A.il ALU_CELLS_A=cells/A ALU_STUB_B=cells/_stub_B
python tools/vmjob.py --label gen_cells -c "bash skill/run_cells_A.sh"
python cells/A/check_cells.py netcmp
```

Kết quả: `D:\Hoc\VLSI_Design\Share\VLSI_work\out\cells\<corner>\<CELL>\` (dạng sóng psfascii),
`...\out\sch\gen.log` (log Virtuoso), `...\out\sch\netlist\<CELL>\netlist` (netlist Spectre sinh từ schematic),
`...\out\libs\ALU_CELLS_A.tgz`, `...\out\libs\ALU_STUB_B.tgz`.

Dùng lại cho khối lớn (KSA8 ...): viết netlist Spectre của khối, rồi
`python tools/scs2skill.py -o skill/gen_ksa.il --ref ALU_CELLS_A=cells/A ALU_ADD=blocks/ALU_ADD/KSA8.scs`
(`--ref` = thư viện đã có trong Virtuoso, chỉ đọc chân, không vẽ lại).

## 5. Mở trong Virtuoso (trong VM)

```
cd ~/ALU_PROJ && virtuoso &
```

Library Manager -> thư viện `ALU_CELLS_A` (hoặc `ALU_STUB_B`) -> chọn cell -> mở view `schematic`
hoặc `symbol`. Thư mục dự án `~/ALU_PROJ` nằm trên đĩa của VM; `cds.lib` trong đó do
`skill/setup_alu_proj.sh` tạo (DEFINE gpdk090, basic, analogLib).

Nhận thư viện ở máy khác: chép `ALU_CELLS_A.tgz` vào thư mục dự án, `tar xzf ALU_CELLS_A.tgz`, rồi
thêm dòng `DEFINE ALU_CELLS_A ./ALU_CELLS_A` vào `cds.lib`.
