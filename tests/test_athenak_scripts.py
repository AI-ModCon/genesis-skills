"""Unit tests for the athenak skill's helper scripts (synthetic fixtures only)."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "astro-sim-skills" / "athenak" / "scripts" / "athinput_tool.py"

SPEC = importlib.util.spec_from_file_location("athinput_tool", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


SAMPLE = """\
# leading comment
<comment>
problem = synthetic test   # not physics

<job>
basename  = demo

<mesh>
nghost = 2
nx1 = 64
x1min = -1.0
x1max = 1.0
ix1_bc = periodic
ox1_bc = periodic
nx2 = 32
x2min = 0.0
x2max = 0.5
ix2_bc = reflect
ox2_bc = outflow
nx3 = 1

<meshblock>
nx1 = 16
nx2 = 16
nx3 = 1

<time>
evolution = dynamic
integrator = rk2
cfl_number = 0.3
tlim\t= 1.0
nlim = -1

<hydro>
eos = ideal
gamma = 1.4
reconstruct = plm
rsolver = hllc

<output2>
file_type = bin
variable = hydro_w
dt = 0.1

<output1>
file_type = hst
dt = 0.01

<hydro>
gamma = 1.6666667   # repeated: later value wins
<par_end>
<ignored>
x = 1
"""


def _run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = TOOL.main(argv)
    return code, out.getvalue(), err.getvalue()


class ParseTests(unittest.TestCase):
    def test_blocks_comments_tabs_and_overwrite(self) -> None:
        blocks = TOOL.parse_text(SAMPLE)
        self.assertEqual(blocks["job"]["basename"], "demo")
        self.assertEqual(blocks["comment"]["problem"], "synthetic test")
        self.assertEqual(blocks["time"]["tlim"], "1.0")
        self.assertEqual(blocks["hydro"]["gamma"], "1.6666667")
        self.assertEqual(blocks["hydro"]["rsolver"], "hllc")
        self.assertNotIn("ignored", blocks)

    def test_parameter_before_block_is_an_error(self) -> None:
        with self.assertRaises(TOOL.AthinputError):
            TOOL.parse_text("nx1 = 4\n<mesh>\n")

    def test_indented_block_header_warns(self) -> None:
        warnings: list[str] = []
        blocks = TOOL.parse_text("<job>\nbasename = a\n  <mesh>\nnx1 = 4\n", warnings)
        self.assertEqual(blocks["mesh"]["nx1"], "4")
        self.assertEqual(len(warnings), 1)
        self.assertIn("indented <mesh>", warnings[0])

    def test_unterminated_block_is_an_error(self) -> None:
        with self.assertRaises(TOOL.AthinputError):
            TOOL.parse_text("<mesh\nnx1 = 4\n")

    def test_reads_parameter_dump_from_binary_header(self) -> None:
        dump = "\n".join(
            [
                "#------------------------- PAR_DUMP -------------------------",
                "<job>",
                "basename= demo",
                "<time>",
                "tlim= 2.0          # comment",
                "#------------------------- PAR_DUMP -------------------------",
                "<par_end>",
                "",
            ]
        )
        preheader = "\n".join(
            [
                "Athena binary output version=1.1",
                "  size of preheader=5",
                "  time=0.0000000000000000e+00",
                "  cycle=0",
                "  size of location=8",
                "  size of variable=4",
                "  number of variables=1",
                "  variables:  dens  ",
                "  header offset=5475",
                "",
            ]
        )
        payload = preheader.encode() + dump.encode() + b"\x00\x01\x02" * 50
        text = TOOL.extract_parameter_text(payload)
        blocks = TOOL.parse_text(text)
        self.assertEqual(blocks, {"job": {"basename": "demo"}, "time": {"tlim": "2.0"}})

    def test_binary_without_header_is_rejected(self) -> None:
        with self.assertRaises(TOOL.AthinputError):
            TOOL.extract_parameter_text(b"\x00\x01garbage")


class OverrideTests(unittest.TestCase):
    def test_override_replaces_existing_value(self) -> None:
        blocks = TOOL.parse_text(SAMPLE)
        TOOL.apply_overrides(blocks, ["time/tlim=5.0", "mesh/nx1=128"])
        self.assertEqual(blocks["time"]["tlim"], "5.0")
        self.assertEqual(blocks["mesh"]["nx1"], "128")

    def test_override_of_missing_block_or_key_is_an_error(self) -> None:
        blocks = TOOL.parse_text(SAMPLE)
        with self.assertRaises(TOOL.AthinputError):
            TOOL.apply_overrides(blocks, ["output9/dt=1"])
        with self.assertRaises(TOOL.AthinputError):
            TOOL.apply_overrides(blocks, ["time/ndiag=10"])


class SummaryTests(unittest.TestCase):
    def test_summary_contents(self) -> None:
        text = TOOL.summary(TOOL.parse_text(SAMPLE))
        self.assertIn("basename: demo", text)
        self.assertIn("mesh: 64 x 32 (2D), nghost=2", text)
        self.assertIn("bc: reflect / outflow", text)
        self.assertIn("-> 8 MeshBlocks on the root level", text)
        self.assertIn("refinement: none", text)
        self.assertIn("physics blocks: hydro", text)
        self.assertLess(text.index("<output1>"), text.index("<output2>"))
        self.assertIn("<output2> file_type=bin variable=hydro_w dt=0.1", text)
        self.assertNotIn("WARNING", text)

    def test_summary_flags_bad_meshblock_and_unknown_block(self) -> None:
        text = SAMPLE.replace("nx1 = 16", "nx1 = 24").replace("<par_end>", "<hydor>\ngamma = 1\n<par_end>")
        blocks = TOOL.parse_text(text)
        text = TOOL.summary(blocks)
        self.assertIn("not a multiple of meshblock nx", text)
        self.assertIn("block names AthenaK will reject: hydor", text)

    def test_output_cadence_follows_athenak_rules(self) -> None:
        extra = (
            "<output3>\nfile_type = bin\nvariable = hydro_u\ndt = 0.5\ndcycle = 10\n"
            "<output4>\nfile_type = rst\n"
            "<output5>\nfile_type = hst\ndt = 0\n"
        )
        text = TOOL.summary(TOOL.parse_text(SAMPLE.replace("<par_end>", extra + "<par_end>")))
        self.assertIn("<output3> file_type=bin variable=hydro_u dcycle=10", text)
        self.assertIn("<output4> file_type=rst no dt/dcycle (AthenaK aborts)", text)
        self.assertIn("<output5> file_type=hst dt=0 (disabled: dt <= 0)", text)

    def test_refinement_listing(self) -> None:
        extra = "<mesh_refinement>\nrefinement = static\nnum_levels = 2\n<refined_region1>\nlevel = 1\n"
        text = TOOL.summary(TOOL.parse_text(SAMPLE.replace("<par_end>", extra + "<par_end>")))
        self.assertIn("refinement: refinement=static, num_levels=2", text)
        self.assertIn("static regions: refined_region1", text)


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.a = Path(self.tmp.name) / "a.athinput"
        self.b = Path(self.tmp.name) / "b.athinput"
        self.a.write_text(SAMPLE, encoding="utf-8")
        self.b.write_text(SAMPLE.replace("cfl_number = 0.3", "cfl_number = 0.4").replace("nlim = -1\n", ""),
                          encoding="utf-8")

    def test_get_with_override(self) -> None:
        code, out, _ = _run([str(self.a), "time/tlim=3", "--get", "time/tlim", "--get", "job/basename"])
        self.assertEqual(code, 0)
        self.assertEqual(out.split(), ["3", "demo"])

    def test_get_missing_key_fails(self) -> None:
        code, _, err = _run([str(self.a), "--get", "time/ndiag"])
        self.assertEqual(code, 2)
        self.assertIn("time/ndiag not set", err)

    def test_diff(self) -> None:
        code, out, _ = _run(["--diff", str(self.a), str(self.b)])
        self.assertEqual(code, 1)
        self.assertIn("~ time/cfl_number: 0.3 -> 0.4", out)
        self.assertIn("- time/nlim = -1", out)
        code, out, _ = _run(["--diff", str(self.a), str(self.a)])
        self.assertEqual((code, out.strip()), (0, "no differences"))

    def test_json_and_dump(self) -> None:
        code, out, _ = _run([str(self.a), "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["mesh"]["nx2"], "32")
        code, out, _ = _run([str(self.a), "--dump"])
        self.assertIn("hydro/gamma = 1.6666667", out.splitlines())



HST_SCRIPT = ROOT / "skills" / "astro-sim-skills" / "athenak" / "scripts" / "hst_summary.py"
HST_SPEC = importlib.util.spec_from_file_location("hst_summary", HST_SCRIPT)
assert HST_SPEC is not None and HST_SPEC.loader is not None
HST = importlib.util.module_from_spec(HST_SPEC)
HST_SPEC.loader.exec_module(HST)

HST_HEADER = (
    "# Athena++ history data\n"
    "#  [1]=time      [2]=dt       [3]=mass    [4]=tot-E    \n"
)
# Two segments: the run wrote t=0.3 after its last restart dump at t=0.2, then was
# restarted from t=0.2, so the second segment rewrites t=0.3 and continues.
HST_RESTARTED = (
    HST_HEADER
    + "  0.00000e+00  1.0e-02  1.00000e+00  2.50000e+00\n"
    + "  1.00000e-01  1.0e-02  1.00000e+00  2.40000e+00\n"
    + "  2.00000e-01  1.0e-02  1.00000e+00  2.30000e+00\n"
    + "  3.00000e-01  1.0e-02  1.00000e+00  9.99000e+02\n"
    + HST_HEADER
    + "  3.00000e-01  1.0e-02  1.00000e+00  2.20000e+00\n"
    + "  4.00000e-01  1.0e-02  1.00000e+00          nan\n"
)


class HstSummaryTests(unittest.TestCase):
    def test_merges_restart_segments_and_drops_superseded_rows(self) -> None:
        hist = HST.parse_text(HST_RESTARTED)
        self.assertEqual(hist.columns, ["time", "dt", "mass", "tot-E"])
        self.assertEqual(hist.segments, 2)
        self.assertEqual(hist.dropped, 1)
        self.assertEqual(hist.column("time"), [0.0, 0.1, 0.2, 0.3, 0.4])
        self.assertEqual(hist.column("tot-E")[3], 2.2)

    def test_raw_keeps_every_row(self) -> None:
        hist = HST.parse_text(HST_RESTARTED, raw=True)
        self.assertEqual(len(hist.rows), 6)
        self.assertEqual(hist.dropped, 0)

    def test_summary_reports_ranges_and_non_finite_values(self) -> None:
        text = HST.summary(HST.parse_text(HST_RESTARTED))
        self.assertIn("segments (starts/restarts): 2", text)
        tot_e = next(line for line in text.splitlines() if line.startswith("tot-E"))
        self.assertIn("2.500000e+00", tot_e)
        self.assertIn("1 non-finite, first at time=4.000000e-01", tot_e)
        self.assertNotIn("9.990000e+02", text)

    def test_errors(self) -> None:
        with self.assertRaises(HST.HstError):
            HST.parse_text("  0.0 1.0\n")
        with self.assertRaises(HST.HstError):
            HST.parse_text(HST_HEADER + "  0.0 1.0\n")
        with self.assertRaises(HST.HstError):
            HST.parse_text(HST_HEADER + "# Athena++ history data\n#  [1]=time  [2]=dt\n")
        with self.assertRaises(HST.HstError):
            HST.parse_text(HST_RESTARTED).column("nope")

    def test_cli_columns_and_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "run.hydro.hst"
            path.write_text(HST_RESTARTED, encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(HST.main([str(path), "--columns"]), 0)
                self.assertEqual(HST.main([str(path), "--csv"]), 0)
                self.assertEqual(HST.main([str(path), "--plot", "missing", "-o", str(Path(tmp_dir) / "x.png")]), 2)
            lines = out.getvalue().splitlines()
            self.assertEqual(lines[:4], ["time", "dt", "mass", "tot-E"])
            self.assertEqual(lines[4], "time,dt,mass,tot-E")
            self.assertEqual(len(lines), 4 + 1 + 5)


if __name__ == "__main__":
    unittest.main()
