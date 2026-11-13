#!/usr/bin/env python3
"""Gui mot job sang may ao Cadence va cho ket qua. Chay tren may Windows.

Vi du:
    python tools/vmjob.py --label inv -c "bash cells/A/run_cells.sh NN"
    python tools/vmjob.py --label drc script.sh

Moi job duoc chep repo vao mot thu muc MOI: Share/VLSI_work/stage/<job>/
(trong VM: /mnt/hgfs/Share/VLSI_work/stage/<job>). Thu muc moi + kiem tra md5
truoc khi chay, vi hgfs trong VM tung tra ve noi dung cu/lan file khi dung chung ten.
Job chay trong thu muc stage; sau khi chay, out/ cua stage duoc chep vao
Share/VLSI_work/out/ (ghi de theo file).
"""
import argparse
import hashlib
import os
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SHARE = Path(os.environ.get("VLSI_SHARE", r"D:\Hoc\VLSI_Design\Share"))
WORK = SHARE / "VLSI_work"
JOBS = SHARE / "jobs"
VM_WORK = "/mnt/hgfs/Share/VLSI_work"
SKIP = {".git", "__pycache__", "out", "stage"}


def stage(name):
    """Chep repo vao WORK/stage/<name>, tra ve noi dung manifest md5 (dinh dang md5sum)."""
    dst_root = WORK / "stage" / name
    lines = []
    for src in sorted(REPO.rglob("*")):
        rel = src.relative_to(REPO)
        if src.is_dir() or any(p in SKIP for p in rel.parts):
            continue
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        data = src.read_bytes()
        dst.write_bytes(data)  # ghi thang, khong doi ten (doi ten lam hgfs lan file)
        lines.append(f"{hashlib.md5(data).hexdigest()}  {rel.as_posix()}")
    shutil.copyfile(REPO.parent / "VLSI" / "tools" / "vm_runner.sh", SHARE / "vm_runner.sh")
    return "\n".join(lines) + "\n"


def runner_alive(wait=6.0):
    # Runner cu chi cap nhat heartbeat khi ranh: job dang chay (log moi ghi, chua .done) cung tinh la song
    now = time.time()
    for log in JOBS.glob("*.log"):
        # 2000 s: runner cat job o 1800 s; Spectre chi ghi log khi xong -> 900 s lam bo job hop le
        if not log.with_suffix(".done").exists() and now - log.stat().st_mtime < 2000:
            return True
    # So noi dung heartbeat qua thoi gian (khong dung mtime vi dong ho VM co the lech)
    hb = JOBS / ".heartbeat"
    first = hb.read_text() if hb.exists() else None
    time.sleep(wait)
    second = hb.read_text() if hb.exists() else None
    return second is not None and second != first


def job_text(name, manifest, body):
    return (f"# JOB {name}\n"
            "set -o pipefail\n"
            f"cd {VM_WORK}/stage/{name} || exit 90\n"
            "cat > /tmp/manifest_$$.md5 <<'__MANIFEST__'\n"
            f"{manifest}__MANIFEST__\n"
            "ok=0; for i in 1 2 3 4 5 6 7 8 9 10; do\n"
            "  md5sum -c --quiet /tmp/manifest_$$.md5 >/dev/null 2>&1 && { ok=1; break; }; sleep 3\n"
            "done\n"
            "[ $ok = 1 ] || { echo 'LOI: file trong stage khac md5 (hgfs)'; md5sum -c --quiet /tmp/manifest_$$.md5; exit 91; }\n"
            "rm -f /tmp/manifest_$$.md5\n"
            "( " + body.replace("\r\n", "\n").strip() + "\n)\nrc=$?\n"
            f"[ -d out ] && mkdir -p {VM_WORK}/out && cp -rf out/. {VM_WORK}/out/\n"
            "exit $rc\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script", nargs="?", help="file .sh (duong dan tren Windows) de chay")
    ap.add_argument("-c", "--command", help="lenh bash chay trong VM")
    ap.add_argument("--label", default="job")
    ap.add_argument("--timeout", type=int, default=1800, help="giay")
    a = ap.parse_args()
    if not (a.script or a.command):
        ap.error("can file script hoac -c")

    JOBS.mkdir(parents=True, exist_ok=True)
    name = f"{time.strftime('%Y%m%d_%H%M%S')}_{os.getpid()}_{a.label}"
    manifest = stage(name)
    # thu lai 60 s: giua hai job runner chua tao log moi va chua kip ghi heartbeat
    if not any(runner_alive() for _ in range(10)):
        print("LOI: vm_runner chua chay trong VM. Trong VM chay: bash /mnt/hgfs/Share/vm_runner.sh",
              file=sys.stderr)
        return 3

    body = a.command if a.command else Path(a.script).read_text(encoding="utf-8")
    (JOBS / (name + ".sh")).write_text(job_text(name, manifest, body), encoding="utf-8", newline="\n")

    done, log = JOBS / (name + ".done"), JOBS / (name + ".log")
    t0 = time.time()
    while not done.exists():
        if time.time() - t0 > a.timeout:
            print(f"LOI: het thoi gian cho job {name}", file=sys.stderr)
            return 4
        time.sleep(2)
    text = log.read_text(encoding="utf-8", errors="replace")
    sys.stdout.write(text)
    print(f"[stage: {WORK / 'stage' / name}]", file=sys.stderr)
    last = [l for l in text.splitlines() if l.startswith("exit=")]
    return int(last[-1][5:]) if last else 1


if __name__ == "__main__":
    sys.exit(main())
