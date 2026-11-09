# Kế hoạch: ALU 8-bit có nhân và chia có dấu (gpdk090)

| | |
|---|---|
| **Nhóm** | 4 người (A, B, C, D) |
| **Thời gian** | 7 tuần |
| **Công nghệ** | gpdk090 v4.6, `nmos1v` / `pmos1v`, VDD = 1.2 V |
| **Công cụ** | Virtuoso IC 6.1.5, Spectre MMSIM 12.1, Assura 4.1 (DRC/LVS/RCX), Incisive 10.2 |
| **Kiểu mạch** | Mức transistor, CMOS tĩnh, tổ hợp (không clock) |
| **Layout** | ⏳ **Chưa chốt**, chờ gặp giảng viên. Quyết định trước **cuối tuần 4** |

---

## 1. Đặc tả

**Ngõ vào:** `A[7:0]`, `B[7:0]`, `OP[3:0]`
**Ngõ ra:** `Y[15:0]`, các cờ `Z`, `C`, `V`, `DZ`

| OP | Lệnh | Y[15:0] | Ghi chú |
|---|---|---|---|
| `0000` | ADD | `{8'b0, A+B}` | |
| `0001` | SUB | `{8'b0, A−B}` | Đảo B bằng XOR, cin = 1 |
| `0010` | AND | `{8'b0, A&B}` | |
| `0011` | OR | `{8'b0, A\|B}` | |
| `0100` | XOR | `{8'b0, A^B}` | |
| `0101` | NOT | `{8'b0, ~A}` | |
| `1001` | **MUL** (có dấu) | `A × B` (16 bit) | Booth radix-4 |
| `1011` | **DIV** (có dấu) | `{R, Q}` | R ở byte cao, Q ở byte thấp |
| `0110`–`1000` | SLL / SRL / SRA | `{8'b0, kết quả}` | *Chỉ làm nếu kịp*, lượng dịch là `B[2:0]` |

**Cờ**
- `Z` = NOR(Y[15:0])
- `C` = c8 (bit nhớ ra của bit 7). Với SUB, C = 1 nghĩa là không mượn.
- `V` = c7 ⊕ c8 cho ADD/SUB. Với DIV: V = 1 khi thực hiện −128 / −1.
- `DZ` = 1 khi OP = DIV và B = 0

**Phép chia có dấu: quy ước**
- Làm tròn **về phía 0** (giống C, Verilog, RISC-V). Phần dư R mang dấu của số bị chia A.
  - Ví dụ: −7 / 2 cho Q = −3, R = −1
- −128 / −1 cho kết quả tràn, nên `V = 1`
- B = 0: `DZ = 1`, Q và R không xác định

### Kiến trúc

**Cộng/trừ:** Kogge-Stone 8-bit (17 cell prefix, 3 tầng), B được XOR với `sub`, cin = `sub`.

**Nhân có dấu:**
1. Booth radix-4 cho **4 hàng** tích riêng, mỗi hàng 9 bit
   - Loại bỏ mở rộng dấu: thêm `~s s s` vào hàng 0, thêm `1 ~s` vào hàng 1–3
   - Bit `neg_i` đặt vào chỗ trống của hàng i+1, nên cột cao nhất là 5
2. **1 tầng nén 4:2** + vài FA/HA để còn 2 hàng
   - Nối tín hiệu đến muộn vào `Cin` của FA
3. Bộ cộng cuối **lai**: ripple cho các bit thấp (có kết quả sớm), KSA cho phần trên
4. Bản cơ sở để so sánh: AND-array + Dadda + KSA16 (chỉ làm schematic)

**Chia có dấu:**
```
A ─► |A| ─┐                         ┌─► Q (đảo dấu nếu sA ≠ sB) ─► Y[7:0]
          ├─► Mảng chia không dấu ──┤
B ─► |B| ─┘   non-restoring 8×8 CAS └─► R (đảo dấu nếu sA = 1)  ─► Y[15:8]
```
- Bộ đảo dấu có điều kiện: `(X XOR s) + s`. Cần 4 bộ (2 ở ngõ vào, 2 ở ngõ ra).
- Làm mảng không dấu trước, lớp bọc dấu là khối riêng.

### Thông số thiết kế

| Thông số | Giá trị |
|---|---|
| nMOS mặc định | W = 0.12 µm, L = 0.10 µm |
| pMOS mặc định | W = 0.24 µm, L = 0.10 µm (Wp/Wn ≈ 2) |
| Corner | NN, FF, SS, FS, SF (`models/spectre/gpdk090.scs`) |
| Linh kiện Vt cao (rò ít) | `nmos1v_hvt` / `pmos1v_hvt`, dùng cho các nhánh không găng nếu cần |

**Quy tắc layout chính (DRM gpdk090)**

| Quy tắc | Giá trị |
|---|---|
| L tối thiểu (`POLY.W.1`) | 0.10 µm |
| W tối thiểu nMOS / pMOS | 0.12 µm |
| Khoảng cách giữa hai cổng poly | 0.12 µm |
| Poly kéo dài ra ngoài active | 0.18 µm |
| Contact: kích thước / khoảng cách | 0.12 / 0.14 µm |
| Contact tới cổng | 0.10 µm |
| Metal1: độ rộng / khoảng cách | 0.12 / 0.12 µm (bước 0.24 µm) |
| Nwell: độ rộng / bao quanh vùng P+ | 0.6 / 0.12 µm |
| N+ tới P+ (active) | 0.15 µm |
| Bước poly khi có contact ở giữa | 0.42 µm |
| **Không được đặt contact lên trên cổng** (`CONT.X.1`) | |

---

## 2. Phân công

| Người | Vai trò | Khối phụ trách | Cell phải vẽ (tuần 1–2) |
|---|---|---|---|
| **A** | Trưởng nhóm, tích hợp | KSA8 + khối logic + MUX ngõ ra + cờ, ghép `ALU_TOP`, tổng hợp báo cáo | INV, NAND2, NOR2, AOI21, OAI21, black cell, gray cell |
| **B** | Bộ nhân, phần trước | Booth encoder/selector, mở rộng dấu, cây nén 4:2, bản cơ sở AND-array + Dadda | XOR2, XNOR2, MUX2 (TG), Booth selector, bộ nén 4:2 |
| **C** | Bộ nhân, phần sau, tối ưu tốc độ | Bộ cộng cuối lai, ghép bộ nhân, định kích thước đường găng bằng Logical Effort, trích ký sinh RCX | FA (mirror), HA, buffer |
| **D** | Kiểm chứng + chia | Mô hình Python, vector test, testbench Spectre, script so sánh; mảng chia + lớp bọc dấu; shifter nếu kịp | CAS, bộ đảo dấu có điều kiện |

Dùng lại:
- KSA của C dùng black cell và gray cell của A.
- Mảng chia của D dùng FA của C.

---

## 3. Lịch 7 tuần

| Tuần | A | B | C | D | Mốc kiểm tra cuối tuần |
|---|---|---|---|---|---|
| **1** | Họp chốt quy ước (2 ngày), schematic + symbol + mô phỏng cell | như A | như A | như A + mô hình Python | Mọi cell đã có schematic và mô phỏng đúng |
| **2** | Layout cell, DRC/LVS; schematic KSA8 | Layout cell; khối sinh tích riêng Booth | Layout cell; bộ cộng cuối | Layout CAS; vector, `.vec`, script so sánh | Cell sạch DRC/LVS (nếu làm layout); có bộ vector |
| **3** | Xong KSA8 + logic + MUX + cờ | Xong cây 4:2 | Ghép bộ cộng cuối vào cây | Kiểm tra từng khối; schematic mảng chia không dấu | MUL qua 100% vector |
| **4** | Ghép `ALU_TOP`, kiểm tra cả ALU | Bản cơ sở AND-array + Dadda | Định kích thước đường găng | Mảng chia qua vector; schematic lớp bọc dấu | ALU qua vector ở NN/FF/SS. **Chốt có layout hay không** |
| **5** | Nhánh **có layout**: layout ALU lõi | Layout phần tích riêng + cây | Layout bộ cộng cuối | Ghép lớp bọc dấu, DIV qua vector | Nếu làm layout mà chưa xong 50% thì chỉ làm cell + KSA8 + bộ nhân |
| **6** | Ghép layout tổng, DRC/LVS | Sửa lỗi DRC/LVS | RCX + mô phỏng sau layout | Chạy lại vector sau layout | Toàn bộ sạch DRC/LVS, kết quả sau PEX đúng |
| **7** | Báo cáo, slide | So sánh Booth với bản cơ sở | Đo độ trễ, công suất, EDP | Đo các corner, tổng hợp số liệu | Nộp bài (nửa đầu tuần là dự phòng) |

**Nhánh không làm layout (tuần 5–6):** dùng thời gian để tối ưu sâu bộ nhân (kích thước, so sánh nhiều phương án), làm shifter, quét các corner và nhiệt độ.

**Ước lượng:** khoảng 290 giờ, tức khoảng 10 giờ mỗi người mỗi tuần.

---

## 4. Quy ước chung (chốt ở tuần 1)

- **Thư viện Virtuoso** mỗi thư viện chỉ một người sửa: `ALU_CELLS_A/B/C/D`, `ALU_ADD`, `ALU_MUL`, `ALU_DIV`, `ALU_TOP`
- **Tên chân:** `A`, `B`, `Y`, `CI`, `CO`, `S`, `VDD`, `GND`. Bus viết dạng `A<7:0>`
- **Cell (nếu làm layout):** cùng chiều cao, thanh nguồn VDD ở trên và GND ở dưới với cùng độ rộng, chân trên Metal1/Metal2
- **Trao đổi:** nén thư viện kèm ngày, ví dụ `tar czf ALU_MUL_2026-11-20.tgz ALU_MUL`, đưa lên repo hoặc qua thư mục Share. A ghép trên máy chính mỗi tuần
- **Máy ảo:** tăng RAM lên 2–4 GB

---

## 5. Kiểm chứng và số đo nộp

- Mô hình Python là chuẩn để so: kiểm tra toàn bộ 65 536 tổ hợp cho MUL và DIV ở mức mô hình
- Mô phỏng Spectre: khoảng 100 vector mỗi phép (giá trị biên + ngẫu nhiên)
  - Giá trị biên: 0, ±1, 127, −128, −128 × −128, −128 / −1, chia cho 0
- Số đo cho từng phép:
  - Độ trễ tệ nhất (`tpd`)
  - Công suất trung bình
  - Năng lượng mỗi phép, EDP
  - Số transistor, diện tích (nếu có layout)

---

## 6. Rủi ro

| Rủi ro | Mức | Cách giảm |
|---|---|---|
| 4 máy ảo riêng nên ghép thư viện dễ bị ghi đè | Cao | Mỗi thư viện một người sửa; A ghép hằng tuần; nén kèm ngày |
| Sai mở rộng dấu trong Booth | Cao | Kiểm tra từng hàng tích riêng với mô hình Python trước khi làm cây |
| Chưa biết có phải layout không | Cao | Layout cell vẫn làm ở tuần 2; quyết định phần còn lại ở cuối tuần 4 |
| Layout toàn bộ không kịp | Cao | Chỉ ghép từ cell; mốc kiểm tra cuối tuần 5 để cắt bớt |
| Hiệu chỉnh dấu của phép chia sai ở trường hợp biên | Trung bình | Dùng lớp bọc dấu thay vì non-restoring có dấu trực tiếp; kiểm tra riêng −128 và chia cho 0 |
| VM chỉ có 956 MB RAM | Trung bình | Tăng RAM ở tuần 1 |
| Mảng chia chậm (8 tầng trừ nối tiếp) | Thấp | Chấp nhận và ghi rõ trong báo cáo |

---

## 7. Việc còn mở

- [ ] Hỏi giảng viên: có bắt buộc layout toàn bộ thiết kế không (hạn: cuối tuần 4)
- [ ] Chốt người cụ thể cho các vai A, B, C, D
