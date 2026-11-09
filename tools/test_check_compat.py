"""Test cho tools/check_compat.py.  Chay: python -m unittest tools/test_check_compat.py"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_compat as cc  # noqa: E402


def errs(issues):
    return [m for lvl, m in issues if lvl == cc.ERR]


def warns(issues):
    return [m for lvl, m in issues if lvl == cc.WARN]


class Branch(unittest.TestCase):
    def test_main_master_blocked(self):
        self.assertTrue(errs(cc.check_branch("main")))
        self.assertTrue(errs(cc.check_branch("master")))

    def test_feature_ok(self):
        self.assertEqual(cc.check_branch("feat/A-cells-alu-core"), [])
        self.assertEqual(cc.check_branch(""), [])  # detached HEAD


class Path(unittest.TestCase):
    def test_good(self):
        self.assertEqual(cc.check_path("cells/A/INV_X1/tb_INV_X1.scs", 10), [])

    def test_bad_names(self):
        for p in ("docs/ke hoach.md", "docs/k\u1ebf_ho\u1ea1ch.md", "a/b(1).scs", "a\\b.scs"):
            self.assertTrue(errs(cc.check_path(p, 1)), p)

    def test_junk(self):
        for p in ("vm/CentOS.vmdk", "vm/x.VMX", "a.nvram", "b.rar", "c.iso", "vm/d.vmdk.lck/M1.lck",
                  "lib/INV/schematic/sch.oa.cdslck", "lib/INV/layout/layout.oa.cdslck.RHEL60.host.123",
                  "out/inv.raw/x.tran"):
            self.assertTrue(errs(cc.check_path(p, 1)), p)

    def test_size(self):
        self.assertEqual(cc.check_path("a.csv", cc.MAX_SIZE), [])
        self.assertTrue(errs(cc.check_path("a.csv", cc.MAX_SIZE + 1)))


class Text(unittest.TestCase):
    def test_crlf(self):
        self.assertTrue(errs(cc.check_text("a.csv", b"op,a\r\n0,1\r\n")))
        self.assertEqual(cc.check_text("a.csv", b"op,a\n0,1\n"), [])
        self.assertEqual(cc.check_text("a.bin", b"\r\n\xff"), [])  # khong phai file text cua VM

    def test_utf8(self):
        self.assertTrue(errs(cc.check_text("a.md", b"caf\xe9\n")))
        self.assertEqual(cc.check_text("a.md", "k\u1ebf ho\u1ea1ch\n".encode()), [])  # .md cho phep tieng Viet

    def test_ascii_only(self):
        viet = "// k\u1ebf ho\u1ea1ch\n".encode()
        for ext in (".sh", ".il", ".scs", ".vec", ".rsf", ".cdl"):
            self.assertTrue(errs(cc.check_text("x" + ext, viet)), ext)
        self.assertEqual(cc.check_text("x.py", b"# " + viet), [])


class Shell(unittest.TestCase):
    def test_shebang(self):
        self.assertEqual(cc.check_sh("tools/a.sh", b"#!/bin/bash\necho\n"), [])
        self.assertEqual(cc.check_sh("tools/a.sh", b"#!/bin/sh\n"), [])
        self.assertTrue(errs(cc.check_sh("tools/a.sh", b"echo hi\n")))
        self.assertTrue(errs(cc.check_sh("tools/a.sh", b"#!/usr/bin/env zsh\n")))
        self.assertEqual(errs(cc.check_sh("cells/A/run.sh", b"echo hi\n")), [])
        self.assertTrue(warns(cc.check_sh("cells/A/run.sh", b"echo hi\n")))


class Skill(unittest.TestCase):
    def test_balanced(self):
        src = b'procedure(f(x) ; comment )\n  let((a [1 2]) printf("(%d\\")" a))\n /* ) */ )\n'
        self.assertEqual(cc.check_il("a.il", src), [])

    def test_unbalanced(self):
        self.assertTrue(errs(cc.check_il("a.il", b"procedure(f(x)\n  x\n")))
        self.assertTrue(errs(cc.check_il("a.il", b"f(x))\n")))
        self.assertTrue(errs(cc.check_il("a.il", b"f([x)]\n")))
        self.assertTrue(errs(cc.check_il("a.il", b'f("abc)\n')))
        self.assertTrue(errs(cc.check_il("a.il", b"f(x) /* open\n")))

    def test_line_number(self):
        self.assertIn("dong 3", errs(cc.check_il("a.il", b"f(\n)\n)\n"))[0])


class Spectre(unittest.TestCase):
    GOOD = (b"// tb\nsimulator lang=spectre\n"
            b'include "/home/buet/cadence/gpdk090_v4.6/models/spectre/gpdk090.scs" section=NN\n'
            b'include "../cells/A/INV_X1.scs"\n'
            b"subckt INV_X1 A Y VDD VSS\n  MN0 (Y A VSS VSS) nmos1v w=0.12u l=0.1u\nends INV_X1\n"
            b"subckt BUF A Y VDD VSS\nends\n* ends nothing\n")

    def test_good(self):
        self.assertEqual(cc.check_scs("a.scs", self.GOOD), [])

    def test_missing_ends(self):
        self.assertTrue(errs(cc.check_scs("a.scs", b"subckt INV_X1 A Y VDD VSS\n")))

    def test_wrong_ends_name(self):
        self.assertTrue(errs(cc.check_scs("a.scs", b"subckt INV_X1 A Y\nends NAND2\n")))

    def test_extra_ends(self):
        self.assertTrue(errs(cc.check_scs("a.scs", b"subckt A x\nends A\nends\n")))

    def test_include_paths(self):
        for line in (b'include "D:\\Hoc\\gpdk090.scs"\n', b'include "C:/models/a.scs"\n',
                     b'include "/mnt/other/a.scs"\n', b'include "..\\a.scs"\n'):
            self.assertTrue(errs(cc.check_scs("a.scs", line)), line)


class Py(unittest.TestCase):
    def test_compile(self):
        self.assertEqual(cc.check_py("a.py", b"x = 1\n"), [])
        self.assertTrue(errs(cc.check_py("a.py", b"def f(:\n")))
        self.assertTrue(errs(cc.check_py("a.py", b"x = 1\x00\n")))


class FileAndModel(unittest.TestCase):
    def test_check_file_combines(self):
        issues = cc.check_file("tools/x y.sh", b"echo\r\n")
        self.assertGreaterEqual(len(errs(issues)), 3)  # ten file, CRLF, shebang

    def test_model_tests(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        self.assertEqual(cc.run_model_tests(d, ["model/a.py"]), [])  # khong co model/
        os.mkdir(os.path.join(d, "model"))
        t = os.path.join(d, "model", "test_alu_ref.py")
        with open(t, "w") as f:
            f.write("import unittest\nclass T(unittest.TestCase):\n    def test_x(self): self.assertEqual(1, 2)\n")
        self.assertEqual(cc.run_model_tests(d, ["docs/a.md"]), [])  # khong dung model/
        self.assertTrue(errs(cc.run_model_tests(d, ["model/a.py"])))
        with open(t, "w") as f:
            f.write("import unittest\nclass T(unittest.TestCase):\n    def test_x(self): pass\n")
        self.assertEqual(cc.run_model_tests(d, ["model/a.py"]), [])


@unittest.skipUnless(shutil.which("git"), "can git")
class StagedRepo(unittest.TestCase):
    """main() phai doc ban DA STAGE va chan nhanh main."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.git("init", "-q", "-b", "main")
        self.git("config", "core.autocrlf", "false")
        self.old = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, self.old)

    def git(self, *a):
        subprocess.run(["git"] + list(a), cwd=self.d, check=True, capture_output=True)

    def write(self, name, data):
        with open(os.path.join(self.d, name), "wb") as f:
            f.write(data)

    def run_main(self):
        with open(os.devnull, "w") as null:
            old, sys.stdout = sys.stdout, null
            try:
                return cc.main([])
            finally:
                sys.stdout = old

    def test_main_branch_blocked(self):
        self.write("a.csv", b"op\n0\n")
        self.git("add", "a.csv")
        self.assertEqual(self.run_main(), 1)
        self.git("switch", "-q", "-c", "feat/A-x")
        self.assertEqual(self.run_main(), 0)

    def test_reads_staged_not_worktree(self):
        self.git("switch", "-q", "-c", "feat/A-x")
        self.write("a.csv", b"op\r\n0\r\n")
        self.git("add", "a.csv")
        self.write("a.csv", b"op\n0\n")  # sua thu muc lam viec, ban stage van CRLF
        self.assertEqual(self.run_main(), 1)
        self.git("add", "a.csv")
        self.assertEqual(self.run_main(), 0)


if __name__ == "__main__":
    unittest.main()
