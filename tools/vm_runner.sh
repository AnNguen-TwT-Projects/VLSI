#!/bin/bash
# Chay trong VM (terminal cua buet):  bash /mnt/hgfs/Share/vm_runner.sh
# Thuc thi lan luot cac job *.sh do may Windows dat vao /mnt/hgfs/Share/jobs.
# Dung bang Ctrl+C. Moi job chay voi quyen cua user hien tai, toi da 1 gio.
JOBS=/mnt/hgfs/Share/jobs
mkdir -p "$JOBS"
echo "vm_runner: dang cho job trong $JOBS (Ctrl+C de dung)"
# heartbeat chay rieng de may Windows biet runner con song ca khi dang chay job dai
( while true; do date +%s%N > "$JOBS/.heartbeat"; sleep 2; done ) &
trap 'kill $! 2>/dev/null' EXIT
while true; do
  for j in $(ls "$JOBS"/*.sh 2>/dev/null | sort); do
    b="${j%.sh}"
    [ -e "$b.done" ] && continue
    # hgfs tung tra ve noi dung cua file khac: chi chay khi dong 1 dung ten job
    n=0; until [ "$(head -1 "$j")" = "# JOB $(basename "$b")" ] || [ $n -ge 10 ]; do sleep 2; n=$((n+1)); done
    if [ $n -ge 10 ]; then { echo "LOI: noi dung job sai (hgfs)"; head -3 "$j"; echo "exit=92"; } > "$b.log"; touch "$b.done"; continue; fi
    echo "[$(date +%T)] chay $(basename "$j")"
    # stdin = /dev/null: virtuoso -nograph gap loi SKILL se thoat ngay thay vi cho nhap lenh
    ( cd /mnt/hgfs/Share/VLSI_work 2>/dev/null || cd ~; timeout 1800 bash "$j" ) < /dev/null > "$b.log" 2>&1
    echo "exit=$?" >> "$b.log"
    touch "$b.done"
    echo "[$(date +%T)] xong  $(basename "$j")"
  done
  date +%s%N > "$JOBS/.heartbeat"
  sleep 2
done
