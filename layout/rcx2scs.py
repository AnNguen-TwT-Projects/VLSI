#!/usr/bin/env python3
"""Netlist Assura RCX (HSPICE, phang) -> Spectre + testbench sau layout. Chay tren Windows.

    python tools/vmjob.py --label rcx -c "bash layout/pnr/run_pnr.sh rcx ALU_TOPK"   # VM: LVS + RCX
    python layout/rcx2scs.py ALU_TOPK                                                # Windows
    python tools/vmjob.py --label post -c "bash layout/run_post.sh ALU_TOPK NN"      # VM: Spectre

Vao: out/assura/<BLK>/rcx/<BLK>_rcx.sp (thu muc Share) va dong XDUT cua blocks/*/tb/tb_<BLK>.scs (thu tu chan).
Ra:  layout/rcx/<BLK>_rcx.scs (subckt <BLK>, cung chan voi ban truoc layout -> dung lai tb cu)
     layout/rcx/tb_<BLK>_post_<NN|SS|FF>.scs
"""
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SHARE = Path(os.environ.get("VLSI_SHARE", r"D:\Hoc\VLSI_Design\Share"))
OUT = REPO / "layout" / "rcx"
MODEL = "/home/buet/cadence/gpdk090_v4.6/models/spectre/gpdk090.scs"
DEV = {"nmos1v": "gpdk090_nmos1v", "pmos1v": "gpdk090_pmos1v"}
KEEP = ("w", "l", "ad", "as", "pd", "ps")   # simW / fw la tham so rieng cua Assura


def cards(text):
    """Noi dong tiep '+', bo chu thich."""
    out = []
    for ln in text.splitlines():
        if ln.startswith("+"):
            out[-1] += " " + ln[1:]
        elif ln.strip() and not ln.startswith("*"):
            out.append(ln)
    return [c.split() for c in out]


def convert(blk, sp, ports):
    names = {}

    def nm(s):   # ten Spectre: chi chu, so, '_'; hai ten khac nhau khong duoc trung sau khi doi
        t = re.sub(r"\W", "_", s)
        assert names.setdefault(t, s) == s, f"trung ten sau khi doi: {s} / {names[t]}"
        return t

    L = [f"// {blk} sau layout: Assura RCX -> layout/rcx2scs.py - khong sua tay", "simulator lang=spectre",
         f"subckt {blk} {' '.join(ports)}"]
    n_m = n_c = 0
    sub_pins = None
    for c in cards(sp):
        k = c[0][0].upper()
        if c[0].upper() == ".SUBCKT":
            sub_pins = set(c[2:])
        elif k == "M":
            par = dict(p.lower().split("=") for p in c[6:])   # 0.12U -> 0.12u, 0.0696P -> 0.0696p
            kv = " ".join(f"{p}={par[p]}" for p in KEEP if p in par)
            L.append(f"    {nm('I_' + c[0])} ({' '.join(nm(n) for n in c[1:5])}) {DEV[c[5]]} {kv}")
            n_m += 1
        elif k == "C":
            L.append(f"    {nm('I_' + c[0])} ({nm(c[1])} {nm(c[2])}) capacitor c={c[3]}")
            n_c += 1
        elif k == "R":
            L.append(f"    {nm('I_' + c[0])} ({nm(c[1])} {nm(c[2])}) resistor r={c[3]}")
        elif k != ".":
            raise SystemExit(f"dong la: {' '.join(c)[:80]}")
    miss = set(ports) - sub_pins - {"VDD", "VSS"}
    assert not miss and sub_pins <= set(ports), f"chan khong khop: thieu {miss}, thua {sub_pins - set(ports)}"
    L.append(f"ends {blk}")
    return "\n".join(L) + "\n", n_m, n_c


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for blk in sys.argv[1:]:
        # tb_<BLK>.scs, hoac tb_<BLK>_p0.scs ... khi tb chia phan (DIV8K)
        tbs = sorted(REPO.glob(f"blocks/*/tb/tb_{blk}.scs")) + sorted(REPO.glob(f"blocks/*/tb/tb_{blk}_p[0-9].scs"))
        ports = re.search(r"^XDUT \((.*)\) " + blk + "$", tbs[0].read_text(), re.M).group(1).split()
        sp = (SHARE / "VLSI_work" / "out" / "assura" / blk / "rcx" / f"{blk}_rcx.sp").read_text()
        scs, m, c = convert(blk, sp, ports)
        (OUT / f"{blk}_rcx.scs").write_text(scs, encoding="ascii", newline="\n")
        for tb in tbs:
            rel = os.path.relpath(tb.parent, OUT).replace("\\", "/")
            for cn in ("NN", "SS", "FF"):
                slow = tb.with_name(tb.stem + "_slow.scs")
                body = slow.name if cn == "SS" and slow.exists() else tb.name
                (OUT / f"{tb.stem}_post_{cn}.scs").write_text(
                    f"// {blk} sau layout (RCX), corner {cn}\nsimulator lang=spectre\n"
                    f'include "{MODEL}" section={cn}\n'
                    'include "../../cells/A/cells_A.scs"\n'          # INV_X1 lam tai
                    f'include "{blk}_rcx.scs"\ninclude "{rel}/{body}"\n', encoding="ascii", newline="\n")
        print(f"ghi layout/rcx/{blk}_rcx.scs ({m} transistor, {c} tu) + {len(tbs)} x tb_*_post_NN/SS/FF.scs")


if __name__ == "__main__":
    main()
