# Tien trinh du an ALU (cap nhat 2026-11-10)

Nhanh: `feat/A-cells-alu-core`. Tat ca so lieu duoi day da chay that trong VM (Spectre/Virtuoso/Assura) hoac mo phong muc cong (Python).

## Ket qua da kiem chung

| Phan | Kiem chung | Ket qua |
|---|---|---|
| 11 cell A + stub XOR/XNOR | Spectre NN/FF/SS, bang chan tri + tre FO4 | Dat het (`docs/cells_A_results.md`) |
| 11 schematic + symbol cell | schCheck + so khop ket noi voi netlist | 0 loi, khop het |
| 9 layout cell A | Assura DRC + LVS | DRC 0 loi, LVS "Schematic and Layout Match" ca 9; GDS `out/gds/ALU_CELLS_A.gds` |
| KSA8 | Spectre NN/SS/FF 148 vector | 148/148 ca 3 corner, tre xau nhat 363 / 525 / 278 ps |
| ALU_CORE (1340 T) | Spectre NN/SS/FF/FS/SF 498 vector | 498/498 ca 5 corner, tre xau nhat 782 / 1121 / 602 / 810 / 859 ps (duong toi co Z) |
| 7 schematic khoi (KSA8, ADDSUB8, LOGIC8, DEC_OP, OUTMUX, FLAGS, ALU_CORE) | schCheck | 0 loi |
| 5 cell B/C (FA, HA, BOOTH_ENC, BOOTH_SEL, CMP42) | Spectre NN/FF/SS | Dat het |
| MUL8 co dau (2168 T) | 65536 cap muc cong; Spectre 80 vector NN/SS/FF/FS/SF | Dung het; tre 1.43 / 2.04 / 1.10 / 1.49 / 1.53 ns |
| DIV8 co dau (4498 T, q dung INV_X4) | 65536 cap muc cong; Spectre 60 vector NN/SS/FF | Dung het; tre xau nhat 8.44 / 12.19 / 6.46 ns (SS chay 16 ns/vector; ban INV_X1 9.37 / 13.47 / 7.20) |
| ALU_TOP (8006 T) | 595 dong alu_full muc cong; Spectre 12 vector NN/SS/FF/FS/SF | Dung het; tre xau nhat 5.49 / 7.94 / 3.45 / 4.60 / 6.22 ns (ban INV_X4) |

## Chua lam
- Layout khoi (MUL8, DIV8, ALU_TOP) cho giang vien quyet dinh. RCX / mo phong sau layout chua lam.

## Da xong them (dot nay)
- Schematic Virtuoso: BOOTH_ENC, BOOTH_SEL, CMP42, FA_X1, HA_X1, CAS_X1, MUL8, MUL8_DADDA, DIV8, ALU_TOP: 0 loi.
- Ban co so Dadda: 80/80 o NN/SS/FF, nhanh hon Booth 18%, EDP 54% (`docs/mul.md`).
- Cong suat NN (`tools/power.py`): KSA8 106 uW, MUL8 708 uW, MUL8_DADDA 470 uW.
- CAS_X1 Spectre NN/FF/SS 130/130.
- Layout 9 cell B/C/D (XOR2, XNOR2, BOOTH_ENC, BOOTH_SEL, CMP42, FA, HA, INV_X4, CAS) sinh tu dong: DRC 0 loi, LVS Match, GDS (`docs/layout_BCD.md`).
- INV_X4: Spectre NN/FF/SS dat, schematic 0 loi.
- Logical Effort: q cua DIV8 dung INV_X4, tre NN 9.37 -> 8.44 ns, 60/60 (`docs/sizing.md`); SS/FF chay lai voi INV_X4.
- So do nop theo phep (tpd, P, E/phep, EDP) va theo corner: `docs/so_do.md`. Tre theo op: `check_results.py` in dong "tre theo op".
- Layout cac khoi lon (cho quyet dinh cua giang vien ve layout).

## Quy tac chay job trong VM
- `python tools/vmjob.py --label X -c "..."`: moi job chep repo vao thu muc moi `stage/<job>` + kiem md5 (hgfs tung tra noi dung cu/nham file).
- VM: `bash /mnt/hgfs/Share/vm_runner.sh`. coreutils 8.4: khong co `timeout -k`. Khong dung `si -batch` (treo).
- Virtuoso: `timeout 300 virtuoso -nograph -restore x.il < /dev/null`, script co errset + exit().
- Assura can `cds.lib` trong thu muc chay (`INCLUDE ~/ALU_PROJ/cds.lib`).
