# Tien trinh phan viec cua A (truong nhom)

Cap nhat: 2026-11-09 ~15:50. Tam dung vi han muc su dung 5 gio da dung 90%, reset luc ~18:20.

## Da xong va da kiem tra
- Nhanh `feat/A-cells-alu-core` (chua commit gi, moi thu dang o working tree).
- `docs/CONVENTIONS.md`: quy uoc cell, chan, kich thuoc, duong dan VM, vector, git hook.
- `tools/vmjob.py` + `tools/vm_runner.sh`: gui job sang VM qua Share.
  - Da sua: dong bo qua ten tam + rename (hgfs cache noi dung cu), cho 2 s sau khi dong bo.
  - Runner chay job voi stdin=/dev/null, toi da 30 phut moi job.
- `model/` + `vectors/`: mo hinh tham chieu, 20 test dat (KSA8 va MUL/DIV co dau kiem tra toan bo to hop).
  - `ksa8.csv` 148 dong, `alu_core.csv` 498 dong, `alu_full.csv` 595 dong.
- `.githooks/pre-commit` + `tools/check_compat.py`: 23 test dat, da bat `core.hooksPath=.githooks`.
- Do moi truong VM: Virtuoso 6.1.5 `-nograph` chay duoc; Spectre 12.1; Assura rules o `~/cadence/gpdk090_v4.6/assura/`; RAM 3.9 GB.
  - Ten model Spectre: `gpdk090_nmos1v` / `gpdk090_pmos1v`.
  - Tham so pcell layout: `fw`, `l` (float, met).

## Dang lam do (xem tung file handoff neu co)
- Cell A (netlist, mo phong NN/FF/SS, schematic/symbol bang SKILL): `cells/A/`, `skill/`, `docs/handoff_cells_A.md`.
  - Van de: buoc `si -batch` xuat netlist bi treo trong VM, PHAI bo.
  - Script SKILL dung lai sau AOI21_X1: can errset cho tung cell + exit() vo dieu kien.
- KSA8 / logic / MUX / co, ALU_CORE: `blocks/`, `docs/handoff_alu_core_A.md`.
- Layout 9 cell + Assura DRC/LVS: `layout/`, `docs/handoff_layout_A.md`.

## Quy tac chay job trong VM (rut ra hom nay)
- Moi job < 10 phut. Virtuoso: `timeout 300 virtuoso -nograph -restore x.il < /dev/null`, script co errset + exit().
- Khong dung `si -batch` (treo). Kiem tra ket noi schematic bang dump SB_NET.
- Chay thu 1 cell truoc khi chay het. Khong xep trung job.
- Neu runner treo: Ctrl+C trong VM, `pkill -f "si -batch"; pkill -f "virtuoso.*-nograph"`, chay lai `bash /mnt/hgfs/Share/vm_runner.sh`.

## Van de lon nhat (phai sua dau tien khi lam lai)
- hgfs tron noi dung file: job A_lay2 chay nhầm noi dung drc.rsf, log a_cells_sim 15:44 chua output cua job layout.
  Nghi ngo: doi ten tmp->rename lam hgfs lan file handle, hoac co 2 vm_runner cung chay.
- Viec can lam:
  1. Trong VM kiem tra chi 1 runner: `ps aux | grep vm_runner`.
  2. Bo rename cho file job; dong dau ten job o dong 1 cua file, runner kiem tra truoc khi chay.
  3. Moi job dong goi nguon inline (heredoc) + kiem tra md5, hoac chuyen sang kenh HTTP qua mang NAT (curl tu VM toi may Windows) de bo han hgfs.

## Ket qua da kiem chung (tom tat tu cac agent)
- Spectre: INV_X1, XOR2_X1, XNOR2_X1 dat NN/FF/SS. 8 cell con lai chua chay lai sau khi sua.
- Schematic: AOI21_X1 schCheck 0 loi, netcmp khop. 10 schematic con lai chua tao (schViewToView mo hop thoai -> da thay bang code ve symbol, chua chay).
- Layout: 9 cell da ve (cao 2.76 um), chua DRC/LVS. Assura 4.1 khong co avDRC().
- ALU_CORE: dung logic 100% (Python, 498/498 vector, KSA8 131072/131072); chua chay Spectre.

## Buoc tiep theo khi lam lai
1. Doc 3 file `docs/handoff_*.md`.
2. Trong VM chay lai runner neu da tat.
3. Hoan thanh cell (schematic + mo phong) -> ALU_CORE qua 100% vector -> layout DRC/LVS sach.
4. `git add` -> hook kiem tra -> commit tren nhanh `feat/A-cells-alu-core` -> push.
