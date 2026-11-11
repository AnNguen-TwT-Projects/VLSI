# THIẾT KẾ BỘ ALU 8-BIT CÓ NHÂN VÀ CHIA CÓ DẤU MỨC TRANSISTOR SỬ DỤNG CÔNG NGHỆ GPDK 90 NM VÀ BỘ CÔNG CỤ CADENCE

**DESIGN OF AN 8-BIT ALU WITH SIGNED MULTIPLICATION AND DIVISION AT TRANSISTOR LEVEL USING GPDK 90 NM AND CADENCE TOOLS**

Báo cáo đồ án môn học Thiết kế vi mạch VLSI

| | |
|---|---|
| Trường / Khoa | [CẦN ĐIỀN: tên trường, khoa in trên bìa] |
| GVHD | [CẦN ĐIỀN] |
| Nhóm SVTH | [CẦN ĐIỀN: họ tên + MSSV của 4 thành viên A, B, C, D] |
| Thời gian | [CẦN ĐIỀN: tháng/năm nộp] |

## TÓM TẮT

Bộ số học – logic (Arithmetic Logic Unit - ALU) là khối tính toán trung tâm của bộ xử lý, trong đó phép nhân và phép chia quyết định cả diện tích lẫn tốc độ. Trong báo cáo này, nhóm thiết kế một ALU 8 bit tổ hợp ở mức transistor trên công nghệ gpdk090 (VDD = 1,2 V), gồm cộng, trừ, AND, OR, XOR, NOT, nhân có dấu và chia có dấu, với bốn cờ Z, C, V, DZ. Bộ cộng dùng kiến trúc Kogge-Stone; bộ nhân dùng mã hóa Booth cơ số 4, bộ nén 4:2 và bộ cộng cuối lai; bộ chia dùng mảng non-restoring với lớp bọc dấu. Thiết kế được kiểm chứng ở ba mức: mô hình Python (toàn bộ 65 536 cặp ngõ vào cho nhân và chia), mô phỏng Spectre ở 5 corner, và layout được kiểm tra DRC/LVS bằng Assura. Kết quả: ALU hoàn chỉnh gồm 8 528 transistor, chiếm 122 × 119 µm², sạch DRC và khớp LVS; độ trễ xấu nhất ở corner NN là 0,78 ns (cộng), 1,43 ns (nhân) và 3,98 ns (chia). Sau khi trích ký sinh, ALU vẫn đúng ở NN, SS, FF với độ trễ xấu nhất 3,58 / 5,14 / 2,75 ns trên bộ vector kiểm tra. Việc thay chuỗi nhớ của mỗi hàng chia bằng bộ cộng Kogge-Stone giúp bộ chia nhanh hơn 2,1 lần trong khi diện tích chỉ tăng 6 %.

**Từ khóa:** ALU; Booth cơ số 4; bộ chia non-restoring; Kogge-Stone; gpdk090; Cadence Virtuoso.

## ABSTRACT

The Arithmetic Logic Unit (ALU) is the computational core of a processor, where multiplication and division dominate both area and speed. This report presents a combinational 8-bit ALU designed at transistor level in the gpdk090 process (VDD = 1.2 V). It supports addition, subtraction, AND, OR, XOR, NOT, signed multiplication and signed division, with four flags Z, C, V and DZ. The adder is a Kogge-Stone adder; the multiplier uses radix-4 Booth encoding, 4:2 compressors and a hybrid final adder; the divider is a non-restoring array with a sign wrapper. The design is verified at three levels: a Python model (all 65,536 input pairs for multiplication and division), Spectre simulation at 5 corners, and layout checked with Assura DRC/LVS. The complete ALU has 8,528 transistors in 122 × 119 µm², is DRC clean and LVS matched; the worst-case delay at the NN corner is 0.78 ns (add), 1.43 ns (multiply) and 3.98 ns (divide). After parasitic extraction the ALU still passes at NN, SS and FF, with worst-case delays of 3.58 / 5.14 / 2.75 ns on the test vectors. Replacing the ripple carry chain of each divider row with a Kogge-Stone adder makes the divider 2.1 times faster for only 6 % more area.

**Keywords:** ALU; radix-4 Booth; non-restoring divider; Kogge-Stone; gpdk090; Cadence Virtuoso.

---

## CHƯƠNG 1. TỔNG QUAN

### 1.1 Đặt vấn đề

ALU thực hiện các phép số học và logic của bộ xử lý. Với các phép đơn giản (cộng, logic), độ trễ chủ yếu do chuỗi nhớ quyết định; với phép nhân và chia, số lượng tích riêng và số bước trừ làm tăng nhanh cả số transistor lẫn độ trễ [1, 2]. Đồ án môn học yêu cầu thiết kế ở mức transistor (full-custom), nên mỗi lựa chọn kiến trúc đều thể hiện trực tiếp thành diện tích và độ trễ đo được.

### 1.2 Mục tiêu

- Thiết kế ALU 8 bit tổ hợp, CMOS tĩnh, trên gpdk090: ADD, SUB, AND, OR, XOR, NOT, MUL có dấu, DIV có dấu; cờ Z, C, V, DZ.
- Kiểm chứng đúng chức năng ở các corner NN, SS, FF, FS, SF.
- Vẽ layout, đạt DRC/LVS, trích ký sinh và mô phỏng sau layout.
- Đo độ trễ, công suất, năng lượng mỗi phép, EDP, số transistor, diện tích.
- Tìm phương án vừa nhanh vừa ít diện tích cho khối chậm nhất.

### 1.3 Giới hạn

- Mạch tổ hợp, không có thanh ghi và clock.
- Các phép dịch (SLL, SRL, SRA) là phần tùy chọn trong kế hoạch và chưa được thực hiện.
- Place & route không dùng thư viện thời gian (.lib), nên việc đặt và đi dây không tối ưu theo độ trễ.
- RCX chỉ trích tụ ký sinh, chưa trích điện trở dây.

### 1.4 Công cụ

Cadence Virtuoso IC 6.1.5 (schematic, layout cell), Spectre MMSIM 12.1 (mô phỏng), Assura 4.1 (DRC, LVS, RCX), Encounter EDI 13.1 (place & route khối), Python 3 (mô hình chuẩn, sinh netlist và testbench, so kết quả).

### 1.5 Bố cục

Chương 2 trình bày cơ sở lý thuyết. Chương 3 trình bày thiết kế từng khối. Chương 4 trình bày kết quả kiểm chứng, đo đạc và layout. Chương 5 kết luận và nêu hướng phát triển.

## CHƯƠNG 2. CƠ SỞ LÝ THUYẾT

### 2.1 Bộ cộng tiền tố song song Kogge-Stone

Bộ cộng tiền tố tính tín hiệu sinh (generate) g = a·b và lan truyền (propagate) p = a ⊕ b, rồi gộp chúng theo cây với toán tử (G, P) ∘ (G', P') = (G + P·G', P·P'). Kiến trúc Kogge-Stone [3] có số tầng nhỏ nhất, log2(n) tầng (3 tầng với 8 bit), và fan-out mỗi nút bằng 2, đổi lại số ô và số dây nhiều hơn.

### 2.2 Nhân có dấu bằng mã hóa Booth cơ số 4

Mã hóa Booth cơ số 4 [4] xét ba bit chồng nhau (b_{2i+1}, b_{2i}, b_{2i−1}) của số nhân và chọn tích riêng trong tập {0, ±A, ±2A}. Số tích riêng giảm từ n xuống n/2 (4 hàng với 8 bit), và phép nhân số bù 2 được xử lý trực tiếp. Các tích riêng được cộng bằng cây nén carry-save; bộ nén 4:2 giảm 4 hàng còn 2 hàng với độ trễ khoảng 3 cổng XOR [1]. Phương án đối chứng là mảng AND Baugh-Wooley với cây Dadda [5].

### 2.3 Chia non-restoring dạng mảng

Phép chia non-restoring ở mỗi bước cộng hoặc trừ số chia vào phần dư tùy theo dấu của phần dư trước đó, nên mỗi bước chỉ cần một bộ cộng/trừ có điều khiển (Controlled Add/Subtract - CAS) [2]. Dạng mảng trải n bước thành n hàng tổ hợp. Vì hàng sau phải chờ bit dấu của hàng trước, độ trễ tỉ lệ với n × (độ trễ một hàng).

### 2.4 Logical Effort

Phương pháp Logical Effort [6] mô hình độ trễ một tầng là d = g·h + p (g: nỗ lực logic, h: tỉ số tải, p: trễ ký sinh), và cho biết đường có N tầng nhanh nhất khi nỗ lực mỗi tầng bằng nhau, f = F^(1/N).

## CHƯƠNG 3. THIẾT KẾ

### 3.1 Đặc tả

Ngõ vào: A[7:0], B[7:0], OP[3:0]. Ngõ ra: Y[15:0] và các cờ Z, C, V, DZ. Bảng 3.1 liệt kê các lệnh.

Bảng 3.1: Tập lệnh của ALU

| OP | Lệnh | Y[15:0] |
|---|---|---|
| 0000 | ADD | {8'b0, A + B} |
| 0001 | SUB | {8'b0, A − B} |
| 0010 | AND | {8'b0, A & B} |
| 0011 | OR | {8'b0, A \| B} |
| 0100 | XOR | {8'b0, A ^ B} |
| 0101 | NOT | {8'b0, ~A} |
| 1001 | MUL có dấu | A × B (16 bit) |
| 1011 | DIV có dấu | {R, Q}: phần dư ở byte cao, thương ở byte thấp |

Cờ: Z = NOR(Y[15:0]); C = bit nhớ ra của bit 7 (với SUB, C = 1 nghĩa là không mượn); V = c7 ⊕ c8 cho ADD/SUB, và V = 1 khi chia −128 / −1; DZ = 1 khi chia cho 0. Phép chia làm tròn về phía 0, phần dư mang dấu của số bị chia (−7 / 2 cho Q = −3, R = −1).

### 3.2 Thư viện cell

Mọi cell là CMOS tĩnh, L = 0,10 µm, đơn vị nMOS 0,12 µm / pMOS 0,24 µm, cao 2,76 µm, ray nguồn Metal1. Bảng 3.2 liệt kê các cell.

Bảng 3.2: Thư viện cell

| Nhóm | Cell | Số transistor |
|---|---|---|
| Cổng cơ bản | INV_X1, INV_X4, NAND2_X1, NOR2_X1, AOI21_X1, OAI21_X1 | 2 – 6 |
| Ô tiền tố | BLK_P, BLK_N (ô đen), GRY_P, GRY_N (ô xám), hai cực tính xen kẽ để bỏ cổng đảo | 6 – 10 |
| XOR | XOR2_X1, XNOR2_X1 | 12 |
| Bộ nhân | BOOTH_ENC (28), BOOTH_SEL (20), CMP42 (56), FA_X1 gương (28), HA_X1 (18) | |
| Bộ chia | CAS_X1 = 3 XOR2 + 3 NAND2 | 48 |

### 3.3 Khối lõi ALU_CORE

ALU_CORE gồm bộ cộng/trừ ADDSUB8 (B được XOR với tín hiệu sub, cin = sub, bộ cộng KSA8 gồm 17 ô tiền tố trong 3 tầng), khối logic LOGIC8, bộ giải mã lệnh DEC_OP, bộ chọn ngõ ra OUTMUX và khối cờ FLAGS. Kết quả của bộ nhân và bộ chia đi vào OUTMUX qua các ngõ MULP, DIVQ, DIVR. ALU_CORE có 1 340 transistor.

### 3.4 Bộ nhân MUL8

1. 4 BOOTH_ENC và 36 BOOTH_SEL tạo 4 hàng tích riêng 9 bit. Việc mở rộng dấu được loại bỏ bằng cách thêm các bit hằng; bit neg của hàng i được đặt vào chỗ trống của hàng i + 1.
2. Một tầng nén 4:2 (chuỗi 7 CMP42 ở cột 6 đến 12) cùng FA/HA ở các cột thấp.
3. Một tầng FA/HA đưa về 2 hàng.
4. Bộ cộng cuối lai: ripple cho P[7:0] (các cột thấp có kết quả sớm) và KSA8 cho P[15:8].

Tổng cộng 2 168 transistor. Bản đối chứng MUL8_DADDA (mảng AND Baugh-Wooley + cây Dadda + cùng bộ cộng cuối) có 2 036 transistor.

### 3.5 Bộ chia DIV8 và phương án DIV8K

Bộ chia gồm lớp bọc dấu và mảng không dấu. Bộ đảo dấu có điều kiện neg(X, s) = (X ⊕ s) + s lấy trị tuyệt đối của A và B ở ngõ vào và trả dấu cho Q, R ở ngõ ra. Mảng non-restoring gồm 8 hàng × 9 CAS và một hàng sửa phần dư. DZ = NOR(B); V = 1 chỉ ở −128 / −1.

Trong DIV8 (4 498 transistor), mỗi hàng là một chuỗi nhớ ripple 9 bit, nên độ trễ xấp xỉ 8 × 9 tầng nhớ. Áp dụng Logical Effort cho net q của mỗi hàng (tải 13,9 µm bề rộng cổng) cho thấy cổng đảo INV_X1 là điểm nghẽn; đổi sang INV_X4 giảm độ trễ 10 % mà không đổi số transistor.

Để giảm bậc của độ trễ, phương án DIV8K thay mỗi hàng bằng 8 XOR2 (D ⊕ T), một bộ cộng KSA8 đã có sẵn (CIN = T) và 2 XOR2 cho bit dấu; hàng sửa phần dư cũng dùng KSA8. DIV8K có 5 020 transistor. Phương án DIV8F (CAS = XOR2 + FA gương, 3 666 transistor) nhằm giảm diện tích.

### 3.6 Ghép ALU

ALU_TOP = ALU_CORE + MUL8 + DIV8 (8 006 transistor). ALU_TOPK = ALU_CORE + MUL8 + DIV8K (8 528 transistor) là bản được chọn.

### 3.7 Luồng thiết kế

Netlist Spectre, testbench, schematic Virtuoso (qua SKILL) và layout cell đều được sinh bằng script Python từ một mô tả duy nhất, nên mô hình mức cổng dùng để kiểm tra 65 536 cặp chính là netlist được mô phỏng và layout. Layout khối dùng Encounter: đặt cell theo hàng, vòng nguồn Metal2/Metal3, đi dây Metal2 đến Metal6, xuất GDS; sau đó Assura kiểm DRC và LVS trên GDS, và RCX trích tụ ký sinh để mô phỏng lại.

## CHƯƠNG 4. KẾT QUẢ

### 4.1 Kiểm chứng chức năng

Bảng 4.1 tổng hợp kết quả kiểm chứng. Mọi vector đều đúng.

Bảng 4.1: Kết quả kiểm chứng chức năng

| Khối | Mức cổng (Python) | Spectre |
|---|---|---|
| KSA8 | | 148/148 ở NN, SS, FF |
| ALU_CORE | | 498/498 ở NN, SS, FF, FS, SF |
| MUL8 | 65 536/65 536 | 80/80 ở 5 corner |
| DIV8, DIV8K, DIV8F | 65 536/65 536 | 60/60 (DIV8, DIV8K ở NN, SS, FF; DIV8F ở NN) |
| ALU_TOP, ALU_TOPK | 524 288/524 288 (8 phép × 65 536 cặp) | 12/12 vector ở NN, SS, FF (ALU_TOP thêm FS, SF) |

Vector Spectre gồm các giá trị biên (0, ±1, 127, −128, −128 × −128, −128 / −1, chia cho 0) và giá trị ngẫu nhiên. Mẫu được lấy ở cuối chu kỳ với ngưỡng 0,6 V; mỗi ngõ ra tải 4 cổng INV_X1.

### 4.2 Độ trễ, công suất, năng lượng theo phép

Bảng 4.2 trình bày số đo ở corner NN (trước layout).

Bảng 4.2: Số đo theo phép, corner NN

| Phép | Khối đo | tpd xấu nhất | P trung bình | E/phép | EDP |
|---|---|---|---|---|---|
| ADD | ALU_CORE | 782 ps | 291 µW | 0,58 pJ | 0,46 pJ·ns |
| SUB | ALU_CORE | 720 ps | 288 µW | 0,58 pJ | 0,41 pJ·ns |
| AND | ALU_CORE | 459 ps | 247 µW | 0,49 pJ | 0,23 pJ·ns |
| OR | ALU_CORE | 473 ps | 235 µW | 0,47 pJ | 0,22 pJ·ns |
| XOR | ALU_CORE | 458 ps | 265 µW | 0,53 pJ | 0,24 pJ·ns |
| NOT | ALU_CORE | 356 ps | 236 µW | 0,47 pJ | 0,17 pJ·ns |
| MUL | MUL8 | 1,43 ns | 708 µW | 2,13 pJ | 3,03 pJ·ns |
| DIV | DIV8 | 8,44 ns | 1,23 mW | 14,7 pJ | 124 pJ·ns |
| DIV | DIV8K | 3,98 ns | 1,16 mW | 13,9 pJ | 55 pJ·ns |

Chu kỳ vector: 2 ns (ALU_CORE), 3 ns (MUL8), 12 ns (DIV). Năng lượng mỗi phép phụ thuộc chu kỳ vì gồm cả dòng rò, nên chỉ so sánh các khối có cùng chu kỳ.

Bảng 4.3: Độ trễ xấu nhất theo corner

| Khối | NN | SS | FF | FS | SF |
|---|---|---|---|---|---|
| KSA8 | 363 ps | 525 ps | 278 ps | | |
| ALU_CORE | 782 ps | 1 121 ps | 602 ps | 810 ps | 859 ps |
| MUL8 | 1,43 ns | 2,04 ns | 1,10 ns | 1,49 ns | 1,53 ns |
| DIV8 | 8,44 ns | 12,19 ns | 6,46 ns | | |
| DIV8K | 3,98 ns | 5,75 ns | 3,04 ns | | |
| ALU_TOP (12 vector) | 5,49 ns | 7,94 ns | 3,45 ns | 4,60 ns | 6,22 ns |
| ALU_TOPK (12 vector) | 4,66 ns | 6,72 ns | 3,59 ns | | |

Nhận xét: bộ chia quyết định độ trễ của cả ALU. Bộ 12 vector của ALU_TOP/ALU_TOPK không chứa cặp chia xấu nhất, nên độ trễ chia thực của ALU lấy theo số đo của riêng khối chia.

### 4.3 So sánh Booth với bản đối chứng Dadda

Bảng 4.4: So sánh hai bộ nhân (NN, 80 vector, 3 ns/vector)

| | MUL8 (Booth cơ số 4 + 4:2) | MUL8_DADDA |
|---|---|---|
| Transistor | 2 168 | 2 036 |
| tpd | 1 427 ps | 1 169 ps |
| P trung bình | 708 µW | 470 µW |
| E/phép | 2,13 pJ | 1,41 pJ |

Nhận xét: ở 8 bit, Booth cơ số 4 không có lợi. Số hàng chỉ giảm từ 8 xuống 5, trong khi BOOTH_SEL và CMP42 lớn và sâu hơn FA; bản Dadda nhanh hơn 18 % và tốn ít công suất hơn 34 %. Lợi ích của Booth rõ hơn khi số bit lớn (từ 16 bit). Thiết kế vẫn giữ Booth theo yêu cầu đề bài.

### 4.4 Tối ưu bộ chia

Bảng 4.5: Ba phương án bộ chia

| | DIV8 | DIV8F | DIV8K |
|---|---|---|---|
| Transistor | 4 498 | 3 666 (−18 %) | 5 020 (+12 %) |
| Diện tích khối sau P&R | 8 569 µm² | 6 920 µm² (−19 %) | 9 108 µm² (+6 %) |
| tpd NN xấu nhất | 8,44 ns | 10,16 ns (+20 %) | 3,98 ns (−53 %) |
| E/phép | 14,7 pJ | 11,3 pJ | 13,9 pJ |
| Diện tích × trễ | 72,3 | 70,3 | 36,2 (nghìn µm²·ns) |

Nhận xét: DIV8K nhanh hơn DIV8 2,1 lần ở cả ba corner, diện tích chỉ tăng 6 %, năng lượng mỗi phép giảm nhẹ; tích diện tích × trễ giảm 50 %. DIV8F chỉ có lợi về diện tích và chậm hơn 20 %. Vì bộ chia là đường tới hạn của ALU, DIV8K được chọn cho bản cuối ALU_TOPK.

### 4.5 Layout

Layout 18 cell đạt DRC 0 lỗi và LVS khớp. Bảng 4.6 trình bày kết quả layout khối.

Bảng 4.6: Layout khối (Encounter, kiểm tra bằng Assura)

| Khối | Kích thước (µm) | Diện tích | DRC | LVS |
|---|---|---|---|---|
| ALU_CORE | 54,84 × 50,35 | 2 761 µm² | 0 | Khớp |
| MUL8 | 64,24 × 64,15 | 4 121 µm² | 0 | Khớp |
| DIV8 | 93,39 × 91,75 | 8 569 µm² | 0 | Khớp |
| DIV8K | 96,38 × 94,51 | 9 108 µm² | 0 | Khớp |
| DIV8F | 85,74 × 80,71 | 6 920 µm² | 0 | Khớp |
| ALU_TOP | 124,89 × 122,11 | 15 250 µm² | 0 | Khớp |
| **ALU_TOPK** | **121,99 × 119,35** | **14 559 µm²** | **0** | **Khớp** |

Mật độ lõi 0,70 (ALU_TOPK 0,72; ALU_TOP 0,66). ALU_TOP phải hạ mật độ xuống 0,66 mới đi dây sạch, nên dù ít transistor hơn nó lại lớn hơn ALU_TOPK 4,5 %.

### 4.6 Mô phỏng sau layout

Quá trình trích ký sinh dùng Assura RCX ở chế độ chỉ tụ (C) và chế độ decoupled (mỗi tụ nối về VSS) trên GDS đã khớp LVS. Netlist sau trích chứa diện tích và chu vi khuếch tán thật (AD, AS, PD, PS) của từng transistor, nên không còn phải dùng giá trị mặc định của mô hình. Tổng tụ ký sinh (không kể VDD-VSS) là 718 fF với ALU_CORE, 1 365 fF với MUL8, 2 706 fF với DIV8K và 4 819 fF với ALU_TOPK. Mô phỏng Spectre dùng cùng testbench và cùng bộ vector với trước layout.

Bảng 4.7 so sánh độ trễ và năng lượng trước và sau layout.

Bảng 4.7: Kết quả mô phỏng sau layout

| Khối / corner | Vector đúng | tpd trước layout | tpd sau layout | E/phép trước | E/phép sau |
|---|---|---|---|---|---|
| ALU_CORE NN | 498/498 | 782 ps | 693 ps | 0,543 pJ | 0,460 pJ |
| MUL8 NN | 80/80 | 1,43 ns | 1,60 ns | 2,125 pJ | 2,154 pJ |
| DIV8K phần p0 NN | 20/20 | 3,98 ns | 3,80 ns | 15,08 pJ | 13,75 pJ |
| ALU_TOPK NN | 12/12 | 4,66 ns | 3,58 ns | 20,27 pJ | 17,92 pJ |
| ALU_TOPK SS (16 ns/vector) | 12/12 | 6,72 ns | 5,14 ns | 18,38 pJ | 16,76 pJ |
| ALU_TOPK FF | 12/12 | 3,59 ns | 2,75 ns | 21,75 pJ | 19,74 pJ |

Nhận xét: sau layout, ALU_CORE, DIV8K và ALU_TOPK nhanh hơn lần lượt 11 %, 4 % và 23 % ở NN, còn MUL8 chậm hơn 12 %. Nguyên nhân là netlist trước layout không khai báo AD, AS, PD, PS, nên mô hình gpdk090 dùng giá trị mặc định cho mọi transistor (AS = AD = 1 µm², PS = PD = 1 µm), trong khi khuếch tán thật của layout chỉ khoảng từ 0,04 đến 0,26 µm², trung vị 0,08 µm². Vì vậy số trước layout bi quan về tụ tiếp giáp, còn số sau layout dùng giá trị thật cộng thêm tụ ký sinh của dây. MUL8 có nhiều dây hơn nên tụ dây làm nó chậm hơn. Hạn chế: RCX chưa trích điện trở dây; tụ ghép giữa các net được quy về VSS (decoupled); DIV8K chỉ chạy phần p0 (phần xấu nhất trước layout) và chỉ ở NN; ALU_CORE và MUL8 chỉ chạy NN.

## CHƯƠNG 5. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

### 5.1 Kết luận

Đề tài đã thiết kế và kiểm chứng một ALU 8 bit mức transistor trên gpdk090 với 8 phép, trong đó nhân và chia có dấu:

- Đúng 100 % ở mức cổng (524 288 trường hợp) và trong mọi mô phỏng Spectre ở các corner đã chạy.
- Layout hoàn chỉnh 8 528 transistor trong 121,99 × 119,35 µm², DRC 0 lỗi, LVS khớp.
- Độ trễ xấu nhất ở NN: 0,78 ns (cộng), 1,43 ns (nhân), 3,98 ns (chia).
- Mô phỏng sau layout (Assura RCX) đúng 100 % ở NN, SS, FF; độ trễ xấu nhất của ALU trên bộ vector kiểm tra là 3,58 / 5,14 / 2,75 ns.
- Phương án DIV8K giảm độ trễ chia 53 % với 6 % diện tích tăng thêm.

Ưu điểm: toàn bộ luồng từ mô hình đến layout được sinh tự động và lặp lại được; mỗi số liệu đều có lệnh chạy lại. Nhược điểm: MUL8 và DIV8K vẫn chuyển mạch khi lệnh là ADD, nên năng lượng mỗi phép của cả ALU (khoảng 20 pJ) lớn hơn nhiều so với riêng ALU_CORE (0,5 pJ); place & route chưa tối ưu theo độ trễ.

### 5.2 Hướng phát triển

- Chặn toán hạng (operand isolation) cho MUL8 và DIV8K để giảm công suất khi không dùng.
- Thay XOR2 12 transistor bằng cell nhỏ hơn và nén layout cell sinh tự động.
- Bổ sung các phép dịch SLL, SRL, SRA.
- Dựng thư viện thời gian (.lib) để place & route theo độ trễ.

## TÀI LIỆU THAM KHẢO

[1] N. H. E. Weste, D. M. Harris, *CMOS VLSI Design: A Circuits and Systems Perspective*, 4th ed., Addison-Wesley, 2011.

[2] B. Parhami, *Computer Arithmetic: Algorithms and Hardware Designs*, 2nd ed., Oxford University Press, 2010.

[3] P. M. Kogge, H. S. Stone, "A parallel algorithm for the efficient solution of a general class of recurrence equations," *IEEE Transactions on Computers*, vol. C-22, no. 8, pp. 786-793, 1973.

[4] A. D. Booth, "A signed binary multiplication technique," *The Quarterly Journal of Mechanics and Applied Mathematics*, vol. 4, no. 2, pp. 236-240, 1951.

[5] L. Dadda, "Some schemes for parallel multipliers," *Alta Frequenza*, vol. 34, pp. 349-356, 1965.

[6] I. Sutherland, B. Sproull, D. Harris, *Logical Effort: Designing Fast CMOS Circuits*, Morgan Kaufmann, 1999.

## PHỤ LỤC: Chạy lại kết quả

Lệnh chạy lại từng số liệu nằm trong các ghi chú kỹ thuật: `docs/so_do.md` (số đo), `docs/mul.md`, `docs/div.md`, `docs/sizing.md`, `docs/huong_toi_uu.md`, `docs/layout_BCD.md`, `docs/layout_blocks.md`.
