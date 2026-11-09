# Handoff: layout of ALU_CELLS_A (paused 2026-11-09 ~15:50 for usage limit)

## Status
| Item | State |
|---|---|
| `layout/gen_layout_A.il`, 9 layout views | **Done and run in the VM**: `LA_SUMMARY errors=0`; all 9 cells created in `~/ALU_PROJ/ALU_CELLS_A/<cell>/layout` |
| Assura DRC | **Not verified yet**. The first run failed only because `avDRC()` is not a function in Assura 4.1; it was removed from `layout/assura/drc.rsf`. A re-run of INV_X1 (job `A_lay3`) was in the queue at the pause. Result still unknown |
| Assura LVS | Not run yet (rsf and CDL are ready) |
| GDS (`strmout`) | Not run yet. The layer map exists: `/home/buet/cadence/gpdk090_v4.6/libs.oa22/gpdk090/gpdk090.layermap` (add `-layerMap` if strmout complains) |
| RCX | Not started (optional) |
| `docs/CONVENTIONS.md` "Layout template" section, `docs/layout_A.md` | Not written yet. Do this after DRC/LVS pass, because DRC may change the numbers below |

Areas from the generator log (W x H, um):
INV_X1 1.08x2.76 = 2.98; NAND2_X1, NOR2_X1 1.62x2.76 = 4.47; AOI21_X1, OAI21_X1, GRY_P, GRY_N 2.16x2.76 = 5.96; BLK_P, BLK_N 3.78x2.76 = 10.43 um^2.

## Template (encoded in gen_layout_A.il; values in um)
- Cell height 2.76. Columns at x = 0.27*(k+1). Cell width = 0.27*(ncols+1). Even columns hold diffusion contacts, odd columns hold poly gates (gate-to-contact distance 0.27 fits a dogbone pad for W = 0.12).
- VSS rail: Metal1, y 0..0.24, over a continuous P+ tap (Oxide 0..0.24, Pimp -0.02..0.26, one Cont per column).
- VDD rail: Metal1, y 2.52..2.76, over an N+ tap (Nimp 2.42..2.78).
- Nwell: x -0.12..W+0.12, y 1.38..2.88. Implants and Nwell extend past the cell box so that abutted cells merge.
- nMOS row centred at y 0.64, inside Nimp 0..W x 0.26..1.00. pMOS row centred at y 2.00, inside Pimp 0..W x 1.50..2.42. Poly runs from y 0.34 to 2.42.
- Input pins: Metal1 pad 0.18x0.40 on the gate column, y 1.12..1.52 (area 0.072 >= 0.07), with a poly contact at y 1.32.
- Output pins: Metal1 0.12 wide on a contact column, y 1.12..1.52.
- Pins use Metal1 "pin" + terminal + label on Metal1 "label" (falls back to Metal1 "pin"). In extract.rul, `pinText("Metal1")` and `textToPin("Metal1" type("label"))` read these.
- Horizontal Metal1 tracks: Tn at y 0.94 and Tp at y 1.70. OAI21 joins n1 on Metal2 (Via1 0.14, M1 landing 0.26x0.28). BLK_P/BLK_N join PI/PIN on Metal2 at y 1.32.
- DRC numbers were taken from `drc.rul` (copy: `Share/VLSI_work/out/assura_ref/`): NIMP/PIMP.E.1 0.14, gate-end enclosure 0.18, tie enclosure 0.02, Pimp-to-N+ oxide 0.16, Poly-to-Oxide 0.10, Cont-to-gate 0.10, M1 area 0.07, wide-M1 (>0.18) spacing 0.18, VIA1 0.14 with enclosure 0.005 / 0.06 on opposite sides. CHECK_DFM is off by default; density and antenna are separate rule sets and are not run.

## Files (all new)
- `layout/gen_layout_A.il`: SKILL generator. It creates ALU_CELLS_A with `ddCreateLib` + `techBindTechFile` only if the library is missing.
- `layout/run_layout_A.sh`: VM driver, steps `gen drc lvs gds` plus an optional cell list. Uses `skill/setup_alu_proj.sh`. Assura runs in `~/ALU_PROJ/assura_run/<cell>/{drc,lvs}` and copies reports to `out/assura/<cell>/`.
- `layout/assura/drc.rsf`, `layout/assura/lvs.rsf`: templates with @CELL@ @RUN@ @CDL@. LVS source is CDL plus PDK `compare.rul` and `bind.rul`.
- `layout/scs2cdl.py` (Windows): `cells/A/<CELL>/<CELL>.scs` -> `layout/assura/cdl/<CELL>.cdl`. Device names become nmos1v/pmos1v (taken from PRIM[...][1] in tools/scs2skill.py). Generated CDL is in `layout/assura/cdl/`.

## Next commands (repo dir on Windows)
```
python layout/scs2cdl.py
python tools/vmjob.py --label layA_drc -c "bash layout/run_layout_A.sh drc INV_X1; ls -la ~/ALU_PROJ/assura_run/INV_X1/drc; tail -40 ~/ALU_PROJ/assura_run/INV_X1/drc/assura.log"
```
1. From the INV run, learn Assura's DRC output names (the `.err` / summary format). Then fix the pass/fail grep in `run_layout_A.sh` (the `drc)` branch is still a guess).
2. Fix any DRC violations in `gen_layout_A.il` (geometry constants are at the top and in `laFrame`/`laStrip`/`laGate`). Then run `bash layout/run_layout_A.sh gen drc` for all cells.
3. Run LVS: `bash layout/run_layout_A.sh lvs INV_X1`. Things that may need fixing: (a) the CDL top cell may need to be named explicitly; (b) if `netlist( cdl ...)` syntax is rejected, check the Assura docs; (c) hierarchical BLK/GRY may need flattening.
4. Run `gds`, then write the docs (CONVENTIONS "Layout template" + `docs/layout_A.md`).

## Open problems
- hgfs served wrong content once. Job `A_lay2` ran `drc.rsf` text as the job script ("line 1: syntax error near `;`"), even after the vmjob rename fix. A retry is the workaround.
- `vmjob.py` sync fails with PermissionError when a synced file is open/locked in the VM (`skill/run_cells_A.sh` while it was running). My local retry wrapper retries on rc 3 and on PermissionError.
- The `a_gen_cells` job (other agent) ran close to the 1-hour runner limit and blocked the queue from 14:47 to about 15:47.
