# Handoff: ALU lõi của A (tạm dừng 2026-11-09 ~15:50 vì giới hạn usage)

## Đã xong và đã kiểm chứng (có bằng chứng)

- `blocks/gen_blocks.py` sinh 7 netlist: `blocks/ALU_ADD/{KSA8,ADDSUB8}.scs`,
  `blocks/ALU_CORE/{LOGIC8,DEC_OP,OUTMUX,FLAGS,ALU_CORE}.scs`. Chỉ dùng cell A + stub XOR2/XNOR2.
  KSA8 = Kogge-Stone 3 tầng xen kẽ N/P/N: 17 cell prefix + 1 GRY_N gộp CIN + 3 INV trên nhánh rẽ.
- Kiểm tra **mức logic** (Python, mô phỏng đúng netlist sinh ra với hàm của từng cell):
  `python blocks/gen_blocks.py --check` →
  `KSA8: 131072/131072`, `ALU_CORE: 6400/6400 (16 ma OP)`, `vectors/alu_core.csv: 498/498`;
  thêm kiểm riêng `vectors/ksa8.csv`: 148/148.
- Số transistor (`--count`): KSA8 378, ADDSUB8 474, LOGIC8 208, DEC_OP 64, OUTMUX 496, FLAGS 98,
  ALU_CORE 1340 (XOR2/XNOR2 stub 12T mỗi cái).
- Độ sâu logic (tầng cổng, XOR stub = 2): KSA8 C8 = 7, S_6 = 9; ALU_CORE Z = 18 (đường găng), V = 13.
- Spectre include tính tương đối theo file chứa include (xác nhận trong VM).

## Chưa kiểm chứng

- **Chưa có lần mô phỏng Spectre nào chạy được** (KSA8, ALU_CORE ở NN/SS/FF): chưa có số pass, chưa có
  độ trễ. `blocks/check_results.py` chưa được chạy trên dữ liệu thật (parser psfascii chưa thử).
- `docs/alu_core_A.md` đã viết phần kiến trúc; còn 2 chỗ giữ chỗ `RESULTS_COUNT`, `RESULTS_SIM`
  cần điền (bảng số transistor ở trên, kết quả mô phỏng).

## Lý do các lần chạy VM thất bại (không phải lỗi khối của A)

1. Cell dùng `nmos1v/pmos1v` (mô hình định nghĩa `gpdk090_nmos1v/pmos1v`) → đã được agent cell sửa.
2. `BLK_*`/`GRY_*` include lẫn nhau → SFE-3 redefined → agent cell đã sửa; testbench nay include
   `cells/A/cells_A.scs` một lần + 2 stub.
3. **hgfs trả nội dung cũ/trộn** sau khi file bị ghi đè trên Windows (VM thấy `ALU_CORE.scs` dòng 4
   "redefine KSA8", `tb_KSA8_FF.scs` cụt). Vẫn xảy ra sau bản sửa rename của `tools/vmjob.py`.
   Cách tránh đang thử: chép `blocks/` + `cells/` vào thư mục mới chưa từng đọc trong VM
   (`Share/VLSI_work/stage/A_<giờ>/`) rồi chạy từ đó. Lần cuối đã tạo `stage/A_15xxxx` (tên trong
   `Share/VLSI_work/stage/`); job có thể đã vào hàng đợi với nhãn `A_sims_stage` — xem `Share/jobs/*A_sims_stage.log`.
4. `vmjob.py` sync có lúc lỗi `PermissionError` khi `os.replace` file `skill/run_cells_A.sh` đang bị khóa;
   chạy lại là qua.

## Lệnh chạy tiếp (từ thư mục repo trên Windows)

```
python blocks/gen_blocks.py && python blocks/gen_blocks.py --check
python blocks/gen_tb.py
# Cách thường:
python tools/vmjob.py --label A_sims -c "CORNERS='NN SS FF' bash blocks/run_sims.sh"
python blocks/check_results.py KSA8 out/KSA8_NN        # và ALU_CORE, _SS, _FF
# Nếu VM vẫn đọc file cũ: chạy từ bản chép mới
S=A_$(date +%H%M%S); D=/d/Hoc/VLSI_Design/Share/VLSI_work/stage/$S; mkdir -p $D; cp -r blocks cells $D/
python tools/vmjob.py --no-sync --label A_sims_stage -c "cd stage/$S && CORNERS='NN SS FF' bash blocks/run_sims.sh"
python blocks/check_results.py KSA8 stage/$S/out/KSA8_NN
```

Trước khi tin kết quả: so `md5sum` file trong VM với trên Windows (đã gắn sẵn trong lệnh job `A_sims_stage`).

## Việc còn lại

- Chạy NN đến 100% cả hai khối, rồi SS, FF; sửa lỗi khối nếu có; ghi số pass/độ trễ vào `docs/alu_core_A.md`.
- Nếu `check_results.py` lỗi parse: xem đầu file `out/<TOP>_<C>/tran.tran` (định dạng psfascii).
- Bug mở: không có bug logic đã biết trong khối của A.
