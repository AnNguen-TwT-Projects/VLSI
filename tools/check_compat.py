#!/usr/bin/env python3
"""Kiem tra tuong thich truoc commit (Windows -> VM CentOS). Chay tren may Windows.

Duoc goi tu .githooks/pre-commit. Kiem tra noi dung DA STAGE (git show :path),
khong phai thu muc lam viec. Quy tac: xem docs/CONVENTIONS.md muc 9.

    python tools/check_compat.py              # kiem tra file da stage (nhu hook)
    python tools/check_compat.py a.sh b.scs   # kiem tra file trong thu muc lam viec

Thoat 1 neu co LOI. CANH BAO khong chan commit.
"""
import os
import re
import subprocess
import sys

MAX_SIZE = 20 * 1024 * 1024
PROTECTED_BRANCHES = {"main", "master"}
BLOCKED_EXT = (".vmdk", ".vmx", ".nvram", ".rar", ".iso", ".lck")
TEXT_EXT = (".sh", ".il", ".scs", ".vec", ".py", ".csv", ".rsf", ".cdl", ".md")
ASCII_EXT = (".sh", ".il", ".scs", ".vec", ".rsf", ".cdl")
PATH_OK = re.compile(r"^[A-Za-z0-9._/-]+$")
SHEBANGS = (b"#!/bin/bash", b"#!/bin/sh")

ERR, WARN = "LOI", "CANH BAO"


def check_branch(branch):
    if branch in PROTECTED_BRANCHES:
        return [(ERR, "dang o nhanh '%s'. Tao nhanh truoc: git switch -c feat/<nguoi>-<viec>" % branch)]
    return []


def check_path(path, size):
    out = []
    if not path.isascii():
        out.append((ERR, "ten file co ky tu khong phai ASCII (vd tieng Viet co dau)"))
    elif " " in path:
        out.append((ERR, "ten file co dau cach"))
    elif not PATH_OK.match(path):
        out.append((ERR, "ten file chi duoc dung [A-Za-z0-9._/-]"))
    if path.startswith("out/"):
        out.append((ERR, "thu muc out/ la ket qua mo phong, khong commit"))
    for part in path.lower().split("/"):
        if part.endswith(BLOCKED_EXT) or ".cdslck" in part:
            out.append((ERR, "file rac cua VM/Cadence/nen (%s), khong commit" % part))
            break
    if size > MAX_SIZE:
        out.append((ERR, "file qua lon (%.1f MB > 20 MB)" % (size / 1048576.0)))
    return out


def _lines_with(data, pred, limit=5):
    bad = [i + 1 for i, ln in enumerate(data.split(b"\n")) if pred(ln)]
    s = ", ".join(map(str, bad[:limit]))
    return s + (" ..." if len(bad) > limit else "")


def check_text(path, data):
    if not path.lower().endswith(TEXT_EXT):
        return []
    out = []
    if b"\r\n" in data:
        out.append((ERR, "co CRLF (dong %s). VM can LF: git add --renormalize ." % _lines_with(data, lambda l: l.endswith(b"\r"))))
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as e:
        out.append((ERR, "khong phai UTF-8 hop le (byte %d)" % e.start))
    if path.lower().endswith(ASCII_EXT) and not data.isascii():
        out.append((ERR, "co ky tu khong phai ASCII (dong %s); tool cu trong VM khong doc duoc" % _lines_with(data, lambda l: not l.isascii())))
    return out


def check_sh(path, data):
    if not path.lower().endswith(".sh"):
        return []
    first = data.split(b"\n", 1)[0].rstrip(b"\r").rstrip()
    if first in SHEBANGS:
        return []
    level = ERR if path.startswith("tools/") else WARN
    return [(level, "dong dau phai la #!/bin/bash hoac #!/bin/sh")]


def check_il(path, data):
    """Ngoac (), [], {} phai can bang, bo qua "chuoi" va chu thich ; va /* */."""
    if not path.lower().endswith(".il"):
        return []
    text = data.decode("utf-8", "replace")
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []  # (ky tu mo, dong)
    line, i, n = 1, 0, len(text)
    in_str = False
    str_line = 0
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
        if in_str:
            if c == "\\":
                if i + 1 < n and text[i + 1] == "\n":
                    line += 1
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str, str_line = True, line
        elif c == ";":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            if j < 0:
                return [(ERR, "chu thich /* mo o dong %d khong dong" % line)]
            line += text.count("\n", i, j)
            i = j + 2
            continue
        elif c in "([{":
            stack.append((c, line))
        elif c in pairs:
            if not stack:
                return [(ERR, "dong %d: '%s' thua, khong co ngoac mo" % (line, c))]
            o, ol = stack.pop()
            if o != pairs[c]:
                return [(ERR, "dong %d: '%s' khong khop voi '%s' mo o dong %d" % (line, c, o, ol))]
        i += 1
    if in_str:
        return [(ERR, "chuoi mo o dong %d khong dong" % str_line)]
    if stack:
        o, ol = stack[-1]
        return [(ERR, "'%s' mo o dong %d khong dong (con %d ngoac mo)" % (o, ol, len(stack)))]
    return []


_SCS_COMMENT = re.compile(r"(^|\s)//.*")
_SUBCKT = re.compile(r"^\s*(?:inline\s+)?subckt\s+(\S+)")
_ENDS = re.compile(r"^\s*ends(?:\s+(\S+))?\s*$")
_INCLUDE = re.compile(r'^\s*\.?(?:ahdl_)?include\s+"?([^"\s]+)')
_WIN_PATH = re.compile(r"^[A-Za-z]:|\\")


def check_scs(path, data):
    if not path.lower().endswith(".scs"):
        return []
    out = []
    stack = []
    for no, raw in enumerate(data.decode("utf-8", "replace").split("\n"), 1):
        ln = raw.rstrip("\r")
        if ln.lstrip().startswith("*"):
            continue
        ln = _SCS_COMMENT.sub("", ln)
        m = _SUBCKT.match(ln)
        if m:
            stack.append((m.group(1), no))
            continue
        m = _ENDS.match(ln)
        if m:
            name = m.group(1)
            if not stack:
                out.append((ERR, "dong %d: 'ends' khong co subckt tuong ung" % no))
            elif name and name != stack[-1][0]:
                out.append((ERR, "dong %d: 'ends %s' nhung subckt dang mo la '%s' (dong %d)" % (no, name, stack[-1][0], stack[-1][1])))
                stack.pop()
            else:
                stack.pop()
            continue
        m = _INCLUDE.match(ln)
        if m:
            p = m.group(1)
            if _WIN_PATH.search(p):
                out.append((ERR, "dong %d: include dung duong dan Windows '%s'" % (no, p)))
            elif p.startswith("/") and not p.startswith("/home/buet/"):
                out.append((ERR, "dong %d: include tuyet doi phai bat dau bang /home/buet/ (hoac dung duong dan tuong doi): '%s'" % (no, p)))
    for name, no in stack:
        out.append((ERR, "subckt %s (dong %d) thieu 'ends'" % (name, no)))
    return out


def check_py(path, data):
    if not path.lower().endswith(".py"):
        return []
    try:
        compile(data, path, "exec", dont_inherit=True)
    except (SyntaxError, ValueError) as e:
        return [(ERR, "Python khong bien dich duoc: dong %s: %s" % (getattr(e, "lineno", "?"), getattr(e, "msg", e)))]
    return []


CONTENT_RULES = (check_text, check_sh, check_il, check_scs, check_py)


def check_file(path, data):
    """Tat ca quy tac cho mot file: (path, bytes) -> [(muc, thong bao)]."""
    out = check_path(path, len(data))
    for rule in CONTENT_RULES:
        out += rule(path, data)
    return out


def run_model_tests(root, paths):
    if not any(p.startswith("model/") for p in paths):
        return []
    if not os.path.isfile(os.path.join(root, "model", "test_alu_ref.py")):
        return []
    # shortcut: chay test tren thu muc lam viec, khong phai ban da stage; doi neu hay stage mot phan file
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "model"],
                       cwd=root, capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-15:])
        return [(ERR, "unittest trong model/ that bai:\n" + tail)]
    return []


def _git(root, *args):
    return subprocess.run(["git"] + list(args), cwd=root, capture_output=True, check=True).stdout


def staged_files(root):
    raw = _git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    return [p.decode("utf-8", "surrogateescape") for p in raw.split(b"\0") if p]


def current_branch(root):
    r = subprocess.run(["git", "symbolic-ref", "--short", "-q", "HEAD"], cwd=root, capture_output=True, text=True)
    return r.stdout.strip()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except AttributeError:
        pass
    root = os.getcwd()
    report = []  # (path, [(muc, msg)])
    if argv:
        paths = [p.replace("\\", "/") for p in argv]
        for p in paths:
            with open(p, "rb") as f:
                report.append((p, check_file(p, f.read())))
    else:
        root = _git(root, "rev-parse", "--show-toplevel").decode().strip()
        report.append(("(nhanh)", check_branch(current_branch(root))))
        paths = staged_files(root)
        for p in paths:
            size = int(_git(root, "cat-file", "-s", ":" + p))
            if size > MAX_SIZE:  # khong doc file khong lo vao RAM
                report.append((p, check_path(p, size)))
                continue
            report.append((p, check_file(p, _git(root, "show", ":" + p))))
    report.append(("(model/ unittest)", run_model_tests(root, paths)))

    n_err = n_warn = 0
    print("check_compat: kiem tra %d file" % len(paths))
    for p, issues in report:
        if not issues:
            if not p.startswith("("):
                print("  OK        %s" % p)
            continue
        for level, msg in issues:
            print("  %-9s %s: %s" % (level, p, msg))
            n_err += level == ERR
            n_warn += level == WARN
    if n_err:
        print("check_compat: %d LOI, %d CANH BAO -> CHAN COMMIT. Sua roi git add lai." % (n_err, n_warn))
        return 1
    print("check_compat: dat (%d CANH BAO)." % n_warn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
