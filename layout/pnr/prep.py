#!/usr/bin/env python3
"""Chuan bi place & route khoi bang Encounter (EDI 13.1). Chay tren Windows.

    python layout/pnr/prep.py cells     # ghi layout/pnr/gen_layout_P.il (FILL1/2/4/8, TIE0, TIE1)
    python layout/pnr/prep.py           # Verilog phang + CDL phang + LEF (can out/pnr/cells.txt tu dump)

- Verilog: moi khoi (ALU_CORE, MUL8, DIV8, ALU_TOP) phang xuong cell la; chan tin hieu noi thang VDD/VSS
  di qua cell TIE1/TIE0 (chi la M1 noi ray, khong transistor -> LVS van khop netlist goc).
- CDL phang cho Assura LVS: cung cach phang hoa, TIE bo qua (chan noi thang VDD/VSS nhu netlist goc).
- LEF: tu hinh hoc dump trong Virtuoso (layout/pnr/dump_layout.il). M1 cham vao pin -> them vao pin
  (cung net); con lai (M1, Via1, M2, Via2, M3) -> OBS.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "layout"))
from scs2skill import PRIM, collect, parse, directions  # noqa: E402
import gen_layout_cells as gc  # noqa: E402
from scs2cdl import subckt  # noqa: E402

WORK = Path(r"D:\Hoc\VLSI_Design\Share\VLSI_work")
PNR = REPO / "layout" / "pnr"
BLOCKS = ("ALU_CORE", "MUL8", "DIV8", "ALU_TOP") + tuple(a for a in sys.argv[1:] if a != "cells")  # + phuong an: DIV8F DIV8K ALU_TOPK, ban 32 bit: CORE32 MUL32 DIV32 ALU32
SUP = ("VDD", "VSS")
FILLS = (1, 2, 4, 8)
LIBS = gc.LIBS + (("ALU_CELLS_P", None),)


def load():
    cells = {}
    for lib, d in gc.LIBS:
        cells.update(collect(f"{lib}={REPO / d}"))
    # BLK_P/BLK_N/GRY_P/GRY_N la cell phan cap (AOI21/OAI21 + NAND2/NOR2): phang tiep xuong cell
    # nguyen thuy (layout phang, chan vao duoc; M2 noi PI cua BLK_P che chan GK).
    leaf = set(cells) - {"BLK_P", "BLK_N", "GRY_P", "GRY_N"}
    for f in sorted((REPO / "blocks").glob("*/*.scs")) + sorted((REPO / "alu32" / "netlist").glob("*.scs")):
        for k, v in parse(f).items():
            cells.setdefault(k, v)
    return cells, leaf


def flat(cells, leaf, top):
    """-> [(inst, master, {pin: net})] cell la; net VDD/VSS giu nguyen ten."""
    out = []

    def walk(name, amap, path):
        for inst, m, nodes, _ in cells[name]["insts"]:
            nn = [amap.get(n, path + n) for n in nodes]
            if m in leaf:
                out.append((path + inst, m, dict(zip(cells[m]["pins"], nn))))
            elif m in PRIM:
                sys.exit(f"{name}/{inst}: transistor o muc khoi, khong P&R duoc")
            else:
                walk(m, dict(zip(cells[m]["pins"], nn)), path + inst + "_")
    walk(top, {p: p for p in cells[top]["pins"]}, "")
    return out


def verilog(cells, leaf, top, dirs):
    insts, ties, lines = flat(cells, leaf, top), 0, []
    ports = [p for p in cells[top]["pins"] if p not in SUP]
    body = []
    for inst, m, conn in insts:
        cs = []
        for p, n in conn.items():
            if p in SUP:
                continue
            if n in SUP:
                t = f"tie{ties}"
                ties += 1
                body.append(f"  {'TIE1' if n == 'VDD' else 'TIE0'} I{t} (.Y({t}));")
                n = t
            cs.append(f".{p}({n})")
        body.append(f"  {m} {inst} ({', '.join(cs)});")
    nets = sorted({n for _, _, c in insts for n in c.values()} - set(ports) - set(SUP))
    nets += [f"tie{i}" for i in range(ties)]
    lines.append(f"// {top}: sinh boi layout/pnr/prep.py -- khong sua tay")
    lines.append(f"module {top} ({', '.join(ports)});")
    for p in ports:
        lines.append(f"  {'output' if dirs[top][p] == 'output' else 'input'} {p};")
    lines += [f"  wire {n};" for n in nets]
    lines += body + ["endmodule", ""]
    return "\n".join(lines), len(insts), ties


def cdl(cells, leaf, top):
    insts = flat(cells, leaf, top)
    used = sorted({m for _, m, _ in insts})
    text = [f"* {top} phang xuong cell la: sinh boi layout/pnr/prep.py", ""]
    seen = {}
    for m in used:
        for d in gc_deps(cells, m, seen):
            pass
    for d in seen:
        text += subckt(d, cells[d])
    text.append(f".SUBCKT {top} {' '.join(cells[top]['pins'])}")
    for inst, m, conn in insts:
        text.append(f"X{inst} {' '.join(conn[p] for p in cells[m]['pins'])} {m}")
    text += [f".ENDS {top}", ""]
    return "\n".join(text)


def gc_deps(cells, name, seen):
    for _, master, _, _ in cells[name]["insts"]:
        if master not in PRIM and master not in seen:
            gc_deps(cells, master, seen)
    seen.setdefault(name, None)
    return seen


# ---------- cell P&R: FILL, TIE (khung giong gen_layout_cells.geometry) ----------
def pcell(name, ncols, fixed=None, port=None):
    c = SimpleNamespace(name=name, ncols=ncols, devs=[], contacts=[], item={"n": {}, "p": {}},
                        node={"n": {}, "p": {}}, fixed=fixed or {}, routes={},
                        ports=[port[0]] if port else [], term={}, dirs={})
    if port:
        c.term[port[0]] = {0: [port[1]]}
        c.dirs[port[0]] = "output"
    return c


def pcells():
    out = []
    for n in FILLS:
        c = pcell(f"FILL{n}", n - 1)
        out.append(("ALU_CELLS_P", c) + gc.geometry(c))
    # TIE0: M1 cot 0 tu ray VSS len y 1.52; TIE1: tu ray VDD xuong y 1.12. Pin Y doan y 1.12..1.52.
    for name, lo, hi in (("TIE0", 0.0, 1.52), ("TIE1", 1.12, gc.H)):
        c = pcell(name, 1, {0: [("Y", lo, hi)]}, ("Y", (1.12, 1.52)))
        out.append(("ALU_CELLS_P", c) + gc.geometry(c))
    return out


# ---------- LEF ----------
def read_dump(path):
    cells, cur = {}, None
    for line in Path(path).read_text().splitlines():
        t = line.split()
        if not t:
            continue
        if t[0] == "CELL":
            cur = cells[t[2]] = {"lib": t[1], "rects": [], "pins": [], "bnd": None, "ninst": 0}
        elif t[0] == "NINST":
            cur["ninst"] = int(t[1])
        elif t[0] == "RECT":
            r = (t[1],) + tuple(float(v) for v in t[3:7])
            if t[1] == "prBoundary":
                cur["bnd"] = r[1:]
            else:
                cur["rects"].append(r)
        elif t[0] == "PIN":
            cur["pins"].append((t[1], t[2]) + tuple(float(v) for v in t[3:7]))
    return cells


def touch(a, b):
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def lef_macro(name, c, dirs):
    x0, y0, x1, y1 = c["bnd"]
    assert (x0, y0) == (0, 0) and abs(y1 - gc.H) < 1e-6, (name, c["bnd"])
    L = [f"MACRO {name}", "  CLASS CORE ;", "  ORIGIN 0 0 ;", f"  SIZE {x1:g} BY {y1:g} ;",
         "  SYMMETRY X Y ;", "  SITE CoreSite ;"]
    rails = [p[2:] for p in c["pins"] if p[0] in SUP]
    inside = [r[1:] for r in c["rects"] if r[0] == "Metal1"]
    # bo M1 nam tron trong ray; cat phan M1 tin hieu lan vao ray (TIE: dai M1 noi ray)
    m1 = [(a, max(b, 0.24), cc, min(d, gc.H - 0.24)) for a, b, cc, d in inside
          if not any(a >= s[0] and b >= s[1] and cc <= s[2] and d <= s[3] for s in rails)]
    m1 = [r for r in m1 if r[3] - r[1] > 1e-6]     # ray M1 loi ra ngoai bien (-0.06..0.24) -> rong sau khi cat
    # hinh co the thuoc pin: M1 (tru M1 cham ray) + Via1/M2/Via2/M3; noi qua cham cung lop
    # hoac lop ke nhau (Metal k - Via k - Metal k+1) -> pin gom ca M2/M3 cung net (router vao truc tiep).
    sig = [p[2:] for p in c["pins"] if p[0] not in SUP]
    geo, m1b = [], []
    for r in m1:
        railish = r[1] <= 0.24 + 1e-9 or r[3] >= gc.H - 0.24 - 1e-9
        if not railish:
            geo.append(("Metal1", r))
            m1b.append(r)
        elif any(touch(r, s) for s in sig):      # TIE: dai M1 tu ray toi pin -> tach: doan sat ray de OBS
            lo, hi = (r[1], 0.30) if r[1] <= 0.24 + 1e-9 else (gc.H - 0.30, r[3])
            m1b.append((r[0], lo, r[2], hi))
            geo.append(("Metal1", (r[0], max(r[1], 0.30), r[2], min(r[3], gc.H - 0.30))))
        else:
            m1b.append(r)
    m1 = m1b + [g[1] for g in geo if g[1] not in m1b]
    geo += [(r[0], r[1:]) for r in c["rects"] if r[0] in ("Via1", "Metal2", "Via2", "Metal3")]
    rank = {"Metal1": 0, "Via1": 1, "Metal2": 2, "Via2": 3, "Metal3": 4}
    used = set()
    for pname in dict.fromkeys(p[0] for p in c["pins"]):
        shapes = [("Metal1", p[2:]) for p in c["pins"] if p[0] == pname]
        if pname not in SUP:
            grow = True
            while grow:
                grow = False
                for i, (lyr, r) in enumerate(geo):
                    if i not in used and any(abs(rank[lyr] - rank[l2]) <= 1 and touch(r, s) for l2, s in shapes):
                        used.add(i)
                        shapes.append((lyr, r))
                        grow = True
        d = "INOUT" if pname in SUP else "OUTPUT" if dirs.get(pname) == "output" else "INPUT"
        L += [f"  PIN {pname}", f"    DIRECTION {d} ;"]
        if pname in SUP:
            L += [f"    USE {'POWER' if pname == 'VDD' else 'GROUND'} ;", "    SHAPE ABUTMENT ;"]
        L.append("    PORT")
        for lyr in rank:
            rs = [r for l_, r in shapes if l_ == lyr]
            if rs:
                L.append(f"      LAYER {lyr} ;")
                L += [f"        RECT {a:g} {b:g} {cc:g} {dd:g} ;" for a, b, cc, dd in rs]
        L += ["    END", f"  END {pname}"]
    pin_m1 = {r for i, (l_, r) in enumerate(geo) if i in used and l_ == "Metal1"}
    obs = [("Metal1", r) for r in m1 if r not in pin_m1]
    obs += [(l_, r) for i, (l_, r) in enumerate(geo) if l_ != "Metal1" and i not in used]
    if obs:
        L.append("  OBS")
        for lyr in ("Metal1", "Via1", "Metal2", "Via2", "Metal3"):
            rs = [r for l_, r in obs if l_ == lyr]
            if rs:
                L.append(f"    LAYER {lyr} ;")
                L += [f"      RECT {a:g} {b:g} {cc:g} {dd:g} ;" for a, b, cc, dd in rs]
        L.append("  END")
    return L + [f"END {name}", ""]


def tech_lef(src):
    """Ban sua gpdk090.lef: muc 'SPACING SAMENET ... END SPACING' khong hop le o LEF 5.7 (Encounter bo qua
    -> NanoRoute coi khoang cach cung net = 0 -> loi METAL2.SP.1.1 giua hai via cung net). Chuyen thanh
    'SPACING x SAMENET ;' trong tung LAYER."""
    import re
    t = Path(src).read_text()
    blk = re.search(r"\nSPACING\n(.*?)\nEND SPACING\n", t, re.S)
    same = {m.group(1): m.group(3) for m in re.finditer(r"SAMENET (\S+) (\S+) (\S+) ;", blk.group(1))}
    t = t.replace(blk.group(0), "\n")
    for lyr, v in same.items():
        if not re.search(rf"\nLAYER {lyr}\n\s+TYPE (ROUTING|CUT) ;", t):
            continue                         # Poly (MASTERSLICE): LEF khong cho SPACING
        t, n = re.subn(rf"(\nLAYER {lyr}\n.*?)(\nEND {lyr}\n)", rf"\1\n  SPACING {v} SAMENET ;\2", t, count=1,
                       flags=re.S)
        assert n == 1, lyr
    return t


def vias(top=9):
    """VIA co dinh cho NanoRoute (gpdk090.lef chi co VIARULE GENERATE; NanoRoute can VIA DEFAULT cho
    MOI cap lop toi Metal9). Via1..6: cat 0.14, bao 0.005/0.06; Via7/8: cat 0.36, bao duoi 0.03/0.08,
    tren 0.05/0.10 (Via8 duoi 0.03/0.08). Moi Via k bon bien the _HV..; DEFAULT dai theo huong uu tien."""
    L = []
    for k in range(1, top):
        c = 0.07 if k <= 6 else 0.18
        enc = ((0.005, 0.06), (0.005, 0.06)) if k <= 6 else ((0.03, 0.08), (0.05, 0.10))
        pref = ("H" if k % 2 else "V", "H" if (k + 1) % 2 else "V")   # Metal k, Metal k+1
        for lo in "HV":
            for hi in "HV":
                name = f"M{k + 1}_M{k}_{lo}{hi}"
                L.append(f"VIA {name}" + (" DEFAULT" if (lo, hi) == pref else ""))
                for lyr, o, (es, el) in ((f"Metal{k}", lo, enc[0]), (f"Via{k}", None, (0, 0)),
                                         (f"Metal{k + 1}", hi, enc[1])):
                    x, y = (c + el, c + es) if o == "H" else (c + es, c + el) if o == "V" else (c, c)
                    L += [f"  LAYER {lyr} ;", f"    RECT {-x:g} {-y:g} {x:g} {y:g} ;"]
                L += [f"END {name}", ""]
    return L


def write_lef(dump, dirs):
    cells = read_dump(dump)
    L = ["VERSION 5.7 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', "",
         "SITE CoreSite", "  CLASS CORE ;", "  SYMMETRY Y ;", f"  SIZE {gc.G:g} BY {gc.H:g} ;",
         "END CoreSite", ""] + vias()
    for name, c in cells.items():
        L += lef_macro(name, c, dirs.get(name, {"Y": "output"}))
    L.append("END LIBRARY")
    (PNR / "lef").mkdir(exist_ok=True)
    (PNR / "lef" / "cells.lef").write_text("\n".join(L) + "\n", encoding="ascii", newline="\n")
    return cells


def access_report(lef_text):
    """Moi pin tin hieu cua moi macro: co diem dat Via1 (dem M2 0.15x0.27) + Via2 (dem M3 0.27x0.15)
    cach OBS M2/M3 >= 0.14 va cat Via1 OBS >= 0.15 khong. -> {macro: [pin khong vao duoc]}."""
    import re
    bad = {}
    for m in re.finditer(r"MACRO (\S+)\n(.*?)\nEND \1\n", lef_text, re.S):
        name, body = m.group(1), m.group(2)
        w = float(re.search(r"SIZE (\S+) BY", body).group(1))
        obs = {}
        if "  OBS" in body:
            cur = None
            for line in body.split("  OBS")[1].splitlines():
                t = line.split()
                if t[:1] == ["LAYER"]:
                    cur = t[1]
                elif t[:1] == ["RECT"]:
                    obs.setdefault(cur, []).append(tuple(float(v) for v in t[1:5]))
        for pm in re.finditer(r"  PIN (\S+)\n(.*?)\n  END \1", body, re.S):
            pin = pm.group(1)
            if pin in SUP:
                continue
            prs, cur = {}, None
            for line in pm.group(2).splitlines():
                t = line.split()
                if t[:1] == ["LAYER"]:
                    cur = t[1]
                elif t[:1] == ["RECT"]:
                    prs.setdefault(cur, []).append(tuple(float(v) for v in t[1:5]))

            def ok(x, y, checks):
                if x - 0.075 < 0.07 or x + 0.075 > w - 0.07:
                    return False
                for lyr, (hx, hy), sp in checks:
                    for a, b, cc, d in obs.get(lyr, []):
                        if not (a >= x + hx + sp - 1e-9 or cc <= x - hx - sp + 1e-9 or
                                b >= y + hy + sp - 1e-9 or d <= y - hy - sp + 1e-9):
                            return False
                return True
            up2 = (("Metal3", (0.135, 0.075), 0.14), ("Via2", (0.07, 0.07), 0.15))
            up1 = (("Metal2", (0.075, 0.135), 0.14), ("Via1", (0.07, 0.07), 0.15)) + up2
            # M1: Via1 + Via2 tai cho; M2: Via2 len M3; M3 trong pin: vao thang tu tren
            p1 = [((a + cc) / 2, b + 0.135 + 0.01 * k) for a, b, cc, d in prs.get("Metal1", []) if cc - a >= 0.119
                  for k in range(max(int((d - b - 0.27) / 0.01) + 1, 0))]
            p2 = [(a + 0.135 + 0.01 * k, (b + d) / 2) for a, b, cc, d in prs.get("Metal2", [])
                  for k in range(max(int((cc - a - 0.27) / 0.01) + 1, 0))]
            if not ("Metal3" in prs or any(ok(x, y, up1) for x, y in p1) or any(ok(x, y, up2) for x, y in p2)):
                bad.setdefault(name, []).append(pin)
    return bad


def selftest():
    c = {"bnd": (0, 0, 0.54, 2.76), "rects": [("Metal1", 0.195, 0.0, 0.345, 1.52), ("Metal2", 0, 0, 1, 1)],
         "pins": [("VSS", "Metal1", 0, 0, 0.54, 0.24), ("Y", "Metal1", 0.195, 1.12, 0.345, 1.52)]}
    t = "\n".join(lef_macro("T", c, {"Y": "output"}))
    y = t.split("PIN Y")[1].split("END Y")[0]
    obs = t.split("OBS")[1]
    assert "RECT 0.195 0.3 0.345 1.52" in y and "RECT 0.195 0.24 0.345 0.3" in obs, t
    assert "RECT 0 0" not in y and "LAYER Metal2" in obs, t


def main():
    selftest()
    if sys.argv[1:] == ["cells"]:
        il = gc.skill(pcells()).replace("gen_layout_BCD.il", "pnr/gen_layout_P.il")
        (PNR / "gen_layout_P.il").write_text(il, encoding="ascii", newline="\n")
        print("wrote layout/pnr/gen_layout_P.il")
        return
    cells, leaf = load()
    _, dirs = directions(cells)
    (PNR / "v").mkdir(exist_ok=True)
    for b in BLOCKS:
        v, n, t = verilog(cells, leaf, b, dirs)
        (PNR / "v" / f"{b}.v").write_text(v, encoding="ascii", newline="\n")
        (REPO / "layout" / "assura" / "cdl" / f"{b}_flat.cdl").write_text(cdl(cells, leaf, b), encoding="ascii",
                                                                         newline="\n")
        print(f"{b}: {n} cell + {t} TIE")
    (PNR / "lef").mkdir(exist_ok=True)       # ban sao gpdk090.lef (chep tu VM vao Share/VLSI_work/ref)
    (PNR / "lef" / "tech.lef").write_text(tech_lef(WORK / "ref" / "gpdk090.lef"), encoding="ascii", newline="\n")
    dump = WORK / "out" / "pnr" / "cells.txt"
    got = write_lef(dump, dirs)
    area = {k: c["bnd"][2] * gc.H for k, c in got.items()}
    used = {m for b in BLOCKS for _, m, _ in flat(cells, leaf, b)} | {"TIE0", "TIE1"}
    hier = [m for m in used if got[m]["ninst"]]
    assert not hier, f"cell dung trong khoi co instance con (LEF thieu hinh): {hier}"
    for b in BLOCKS:
        a = sum(area[m] for _, m, _ in flat(cells, leaf, b))
        print(f"{b}: tong dien tich cell {a:.0f} um2")
    print(f"LEF {len(got)} macro -> layout/pnr/lef/cells.lef")
    bad = {m: p for m, p in access_report((PNR / "lef" / "cells.lef").read_text()).items() if m in used}
    print("pin khong vao duoc (M2/M3 trong cell che):", bad or "khong co")


if __name__ == "__main__":
    main()
