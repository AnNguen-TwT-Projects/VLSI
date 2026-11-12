# ALU 32 bit (so sanh voi ALU 8 bit)

Du an phu de so sanh: ALU 32 bit dung cung kien truc voi ALU_TOPK 8 bit (KSA, Booth co so 4 + cay 4:2, chia mang non-restoring moi hang 1 KSA, boc dau), duoc sinh tu mot bo sinh tham so hoa theo N: alu32/gen_alun.py. Dung lai toan bo cell cua thu vien 8 bit, khong them cell moi.

## Lenh

```
python alu32/gen_alun.py            (ghi alu32/netlist/*.scs va alu32/tb/*)
python alu32/gen_alun.py --check    (kiem chung muc logic)
python alu32/gen_alun.py --count    (transistor + do sau cell, 8 bit va 32 bit)
python alu32/gen_alun.py --res MUL32 out/MUL32_p0_NN 0   (so ket qua Spectre phan 0)
```

## Kiem chung muc logic (da chay, dat)

- ALU4: 4096/4096 to hop (16 ma OP, quet het)
- MUL8 / DIV8 sinh tu bo sinh tong quat: 65536/65536 cap (a, b) moi khoi
- ALU8: 2870/2870 vector; ALU32: 1770/1770 vector (bien x bien + ngau nhien, 8 phep + 2 ma du tru)
- Thu dot bien (doi 1 cell trong MUL32, DIV32, KSA32): bo kiem tra bat duoc ca 3 (17/40, 40/40, 13/40 vector sai)

## So sanh 8 bit / 32 bit (da do: so transistor va do sau cell)

| Khoi | Transistor 8 bit | Transistor 32 bit | Ti le | Do sau cell 8 bit | Do sau cell 32 bit |
|---|---|---|---|---|---|
| KSA8 / KSA32 | 378 | 2086 | 5.5 | 7 | 9 |
| ALU_CORE / CORE32 | 1340 | 5824 | 4.3 | 15 | 23 |
| MUL8 / MUL32 | 2168 | 30956 | 14.3 | 17 | 26 |
| DIV8K / DIV32 | 5020 | 86112 | 17.2 | 102 | 613 |
| ALU_TOPK / ALU32 | 8528 | 122892 | 14.4 | 109 | 622 |

Ghi chu: do sau cell = so cell noi tiep tren duong dai nhat (CMP42 tinh 2 tang); cay nen cua MUL32 giam chieu cao cot 17 -> 9 -> 5 -> 3 -> 2; ALU32 co 1446 INV_X4 lam cay dem cho net nhieu tai (ban 8 bit khong can).

## Tre (UOC LUONG, chua mo phong Spectre)

Uoc luong = do sau cell 32 bit x (tre truoc layout NN da do cua khoi 8 bit / do sau cell 8 bit); chi de dinh huong, phai thay bang so Spectre.

| Khoi | Tre 8 bit da do (NN, truoc layout) | ps moi tang | Tre 32 bit uoc luong |
|---|---|---|---|
| ALU_CORE / CORE32 | 781.9 ps | 52 | khoang 1.2 ns |
| MUL8 / MUL32 | 1427.4 ps | 84 | khoang 2.2 ns |
| DIV8K / DIV32 | 3975.3 ps | 39 | khoang 24 ns |
| ALU_TOPK / ALU32 | 4660.6 ps | - | khoang 24.5 ns (DIV32 + mux ra) |

## Nhan xet

- Cong/tru/logic tang gan tuyen tinh (4.3 lan transistor, tre khoang 1.5 lan): KSA chi them 2 tang prefix.
- Bo nhan tang 14.3 lan transistor nhung tre chi khoang 1.5 lan nho cay 4:2 (them 2 tang nen) va KSA64.
- Bo chia tang 17.2 lan transistor va khoang 6 lan tre; chiem 70% transistor cua ALU32 va quyet dinh tre toan mach. Mang chia to hop khong con hop ly o 32 bit; nen chuyen sang chia tuan tu.
- Chuoi dao dau (neg) la chuoi OR noi tiep 2 tang/bit: 124 tang trong 613 tang cua DIV32; co the thay bang XOR + KSA.

## Chua lam

- Mo phong Spectre (VM dang tat luc viet): testbench da sinh trong alu32/tb (CORE32 10 vector, MUL32 9 vector / 3 phan, DIV32 9 vector / 3 phan, corner NN/SS/FF). Lenh: `python tools/vmjob.py --label a32 --timeout 1700 -c "spectre alu32/tb/tb_MUL32_p0_NN.scs -format psfascii -raw out/MUL32_p0_NN +log out/MUL32_p0_NN.log"`
- DIV32 (86112 transistor, 60 ns moi vector) co the vuot gioi han 30 phut moi job cua runner.
- Layout (Encounter), DRC/LVS/RCX, schematic Virtuoso cho ban 32 bit.
