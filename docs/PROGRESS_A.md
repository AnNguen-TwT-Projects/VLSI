# Tien trinh du an ALU (cap nhat 2026-11-10)

Nhanh: `feat/A-cells-alu-core`. Tat ca so lieu duoi day da chay that trong VM (Spectre/Virtuoso/Assura) hoac mo phong muc cong (Python).

## Ket qua da kiem chung

| Phan | Kiem chung | Ket qua |
|---|---|---|
| 11 cell A + stub XOR/XNOR | Spectre NN/FF/SS, bang chan tri + tre FO4 | Dat het (`docs/cells_A_results.md`) |
| 11 schematic + symbol cell | schCheck + so khop ket noi voi netlist | 0 loi, khop het |
| 9 layout cell A | Assura DRC + LVS | DRC 0 loi, LVS "Schematic and Layout Match" ca 9; GDS `out/gds/ALU_CELLS_A.gds` |
| KSA8 | Spectre NN/SS/FF 148 vector | 148/148 ca 3 corner, tre xau nhat 363 / 525 / 278 ps |
| ALU_CORE (1340 T) | Spectre NN/SS/FF 498 vector | 498/498 ca 3 corner, tre xau nhat 782 / 1121 / 602 ps (duong toi co Z) |
| 7 schematic khoi (KSA8, ADDSUB8, LOGIC8, DEC_OP, OUTMUX, FLAGS, ALU_CORE) | schCheck | 0 loi |
| 5 cell B/C (FA, HA, BOOTH_ENC, BOOTH_SEL, CMP42) | Spectre NN/FF/SS | Dat het |
| MUL8 co dau (2168 T) | 65536 cap muc cong; Spectre 80 vector NN/SS/FF | Dung het; tre 1.43 / 2.04 / 1.10 ns |
| DIV8 co dau (4498 T) | 65536 cap muc cong; Spectre 60 vector NN | Dung het; tre xau nhat 9.37 ns |
| ALU_TOP (8006 T) | 595 dong alu_full muc cong; Spectre 12 vector NN | Dung het; tre xau nhat 5.2 ns |

## Chua lam
- SS/FF cho DIV8, ALU_TOP.
- Schematic/layout cho cell B/C/D va khoi MUL8/DIV8/ALU_TOP.
- Ban co so AND-array + Dadda de so sanh; dinh kich thuoc duong gang (Logical Effort); do cong suat.
- Layout cac khoi lon (cho quyet dinh cua giang vien ve layout).

## Quy tac chay job trong VM
- `python tools/vmjob.py --label X -c "..."`: moi job chep repo vao thu muc moi `stage/<job>` + kiem md5 (hgfs tung tra noi dung cu/nham file).
- VM: `bash /mnt/hgfs/Share/vm_runner.sh`. coreutils 8.4: khong co `timeout -k`. Khong dung `si -batch` (treo).
- Virtuoso: `timeout 300 virtuoso -nograph -restore x.il < /dev/null`, script co errset + exit().
- Assura can `cds.lib` trong thu muc chay (`INCLUDE ~/ALU_PROJ/cds.lib`).
