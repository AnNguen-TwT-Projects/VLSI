# Quy ước chung (chốt ở tuần 1)

Mọi người trong nhóm làm theo file này. Sửa file này phải được trưởng nhóm (A) đồng ý.

## 1. Thư mục trong repo

| Thư mục | Nội dung | Ai sửa |
|---|---|---|
| `docs/` | Kế hoạch, quy ước, báo cáo | A |
| `model/` | Mô hình tham chiếu Python, sinh vector | D (phần ALU lõi do A dùng chung) |
| `vectors/` | Vector test sinh từ `model/` (CSV) | sinh tự động |
| `cells/<người>/<CELL>/` | Netlist Spectre của cell + testbench | chủ cell |
| `blocks/<khối>/` | Netlist khối (ALU_ADD, ALU_MUL, ...) + testbench | chủ khối |
| `skill/` | Script SKILL tạo schematic, symbol, layout trong Virtuoso | chủ của phần tương ứng |
| `tools/` | Công cụ chung (chạy job trong VM, kiểm tra tương thích) | A |
| `out/` | Kết quả mô phỏng, log. **Không commit** | — |

Tên file và thư mục: chỉ dùng chữ ASCII, số, `_`, `-`, `.`. Không dấu cách, không tiếng Việt có dấu (VM Linux và Cadence không đọc tốt).

## 2. Máy chạy gì

- **Máy Windows:** Python 3 (mô hình, sinh vector, so sánh kết quả), git.
- **VM CentOS:** chỉ chạy bash, SKILL (`virtuoso -nograph`), `spectre`, `assura`. **Không viết Python chạy trong VM**, vì Python ở đó rất cũ.
- Gửi việc sang VM bằng `python tools/vmjob.py` (xem đầu file đó). Trong VM phải có `vm_runner.sh` đang chạy.

| | Đường dẫn |
|---|---|
| Share trên Windows | `D:\Hoc\VLSI_Design\Share` |
| Share trong VM | `/mnt/hgfs/Share` |
| Bản sao repo trong VM | `/mnt/hgfs/Share/VLSI_work` (job chạy ở đây) |
| Thư viện Virtuoso (OA) | `~/ALU_PROJ` trên **đĩa của VM** (không để OA trên hgfs) |
| Mô hình transistor | `/home/buet/cadence/gpdk090_v4.6/models/spectre/gpdk090.scs`, `section=NN` |

## 3. Transistor và kích thước

- Linh kiện: `nmos1v`, `pmos1v`. Bulk của nMOS nối `VSS`, bulk của pMOS nối `VDD`. VDD = 1.2 V.
- L = 0.1 µm cho mọi transistor.
- Đơn vị: nMOS 0.12 µm, pMOS 0.24 µm (Wp/Wn ≈ 2). Transistor nối tiếp k cái thì nhân độ rộng lên k lần.

## 4. Cell của A (thư viện `ALU_CELLS_A`)

Thứ tự chân trong `subckt`: **ngõ vào theo thứ tự trong bảng, rồi ngõ ra, rồi `VDD VSS`**.

| Cell | Chân | Hàm | nMOS W (µm) | pMOS W (µm) |
|---|---|---|---|---|
| `INV_X1` | `A Y VDD VSS` | Y = !A | 0.12 | 0.24 |
| `NAND2_X1` | `A B Y VDD VSS` | Y = !(A·B) | 0.24, 0.24 (nối tiếp) | 0.24, 0.24 (song song) |
| `NOR2_X1` | `A B Y VDD VSS` | Y = !(A+B) | 0.12, 0.12 | 0.48, 0.48 (nối tiếp) |
| `AOI21_X1` | `A1 A2 B Y VDD VSS` | Y = !(A1·A2 + B) | A1, A2: 0.24; B: 0.12 | 0.48 cả ba |
| `OAI21_X1` | `A1 A2 B Y VDD VSS` | Y = !((A1+A2)·B) | 0.24 cả ba | A1, A2: 0.48; B: 0.24 |
| `BLK_P` | `GI PI GK PK GON PON VDD VSS` | GON = !(GI + PI·GK), PON = !(PI·PK) | AOI21(A1=PI, A2=GK, B=GI) + NAND2 | |
| `BLK_N` | `GIN PIN GKN PKN GO PO VDD VSS` | GO = !(GIN·(PIN+GKN)), PO = !(PIN+PKN) | OAI21(A1=PIN, A2=GKN, B=GIN) + NOR2 | |
| `GRY_P` | `GI PI GK GON VDD VSS` | GON = !(GI + PI·GK) | AOI21 | |
| `GRY_N` | `GIN PIN GKN GO VDD VSS` | GO = !(GIN·(PIN+GKN)) | OAI21 | |

Hậu tố `N` ở tên chân nghĩa là **tín hiệu đảo** (active-low). Trong KSA, các tầng prefix xen kẽ `_P` và `_N` để không cần inverter giữa các tầng.

**Cell tạm (thuộc B, A dùng trước):** `XOR2_X1 (A B Y VDD VSS)`, `XNOR2_X1 (A B Y VDD VSS)`. Đặt ở `cells/_stub_B/`. Khi B giao cell thật cùng tên và cùng thứ tự chân thì thay vào, không phải sửa khối của A.

## 5. Tên tín hiệu

- Spectre: bus viết `A_0 ... A_7` (bit 0 là LSB).
- Virtuoso schematic: `A<7:0>`.
- Nguồn: `VDD`, `VSS`.

## 6. ALU lõi của A (`blocks/ALU_ADD`, khối tổng `ALU_CORE`)

Ngõ vào: `A_7..0`, `B_7..0`, `OP_3..0`, cùng các ngõ vào chờ ghép từ khối khác:
`MULP_15..0` (từ bộ nhân), `DIVQ_7..0`, `DIVR_7..0`, `DIVV`, `DIVDZ` (từ bộ chia).

Ngõ ra: `Y_15..0`, `Z`, `C`, `V`, `DZ`. Bảng OP, cờ và trường hợp đặc biệt xem `docs/KE_HOACH_ALU.md`, mục 1.

## 7. Vector test

File CSV trong `vectors/`, dòng đầu là tên cột, giá trị là **số nguyên thập phân không dấu** (dạng bit), ví dụ `a=255` nghĩa là `0xFF`, tức −1 khi hiểu có dấu.

```
op,a,b,y,z,c,v,dz
0,1,2,3,0,0,0,0
```

Các cột của khối nào không dùng thì bỏ qua khi so sánh (ví dụ `c`, `v` cho phép AND).

## 8. Mô phỏng

- Sườn tín hiệu vào 20 ps. Độ trễ đo ở mức 50% VDD.
- Tải chuẩn khi đo cell: 4 cổng `INV_X1` (FO4).
- Thời gian mỗi vector khi kiểm tra chức năng: 2 ns (đủ cho ALU lõi).

## 9. Git

- Không commit thẳng lên `main`. Mỗi người làm trên nhánh `feat/<người>-<việc>`, rồi mở pull request.
- Bật hook kiểm tra trước commit (chạy một lần sau khi clone): `git config core.hooksPath .githooks`

### Hook kiểm tra tương thích (`.githooks/pre-commit` → `tools/check_compat.py`)

Hook kiểm tra **nội dung đã `git add`** (không phải thư mục làm việc). Có LỖI thì chặn commit; CẢNH BÁO thì vẫn cho commit. Chạy tay: `python tools/check_compat.py` (file đã stage) hoặc `python tools/check_compat.py <file>...`. Test của hook: `python -m unittest tools/test_check_compat.py`.

- Nhánh `main`/`master`: chặn, phải tạo nhánh `feat/...` trước.
- Tên file: chỉ `[A-Za-z0-9._/-]`, không dấu cách, không tiếng Việt có dấu.
- Không commit: `out/`, `*.vmdk *.vmx *.nvram *.rar *.iso *.lck`, khóa Cadence `*.cdslck*`, file > 20 MB.
- `*.sh *.il *.scs *.vec *.py *.csv *.rsf *.cdl *.md`: không CRLF, phải UTF-8. Riêng `*.sh *.il *.scs *.vec *.rsf *.cdl`: chỉ ASCII.
- `*.sh`: dòng đầu `#!/bin/bash` hoặc `#!/bin/sh` (lỗi nếu ở `tools/`, nơi khác chỉ cảnh báo).
- `*.il`: ngoặc `() [] {}` cân bằng (bỏ qua chuỗi và chú thích `;`, `/* */`).
- `*.scs`: mỗi `subckt X` có `ends X` (hoặc `ends`); `include` dùng đường dẫn tương đối hoặc `/home/buet/...`, không dùng `D:\...`.
- `*.py`: phải biên dịch được.
- Có file trong `model/` và có `model/test_alu_ref.py`: chạy `python -m unittest discover -s model`, lỗi thì chặn.
