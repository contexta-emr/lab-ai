"""Build one patient's synthetic lab-report corpus: HTML -> PDF -> sealed answer key.

    python corpus/generator/build.py --patient 1 --fresh
    python corpus/generator/build.py --patient holdout --fresh

Writes, from the repository root::

    corpus/data/pdfs/P01/P01-R01.pdf     the only thing the parser is allowed to see
    corpus/data/html/P01/P01-R01.html    source page, kept so a layout tweak re-renders
    corpus/data/answers/reports.csv      sealed key: one line per report
    corpus/data/answers/rows.csv         sealed key: one line per printed test
    corpus/data/vitals/P01-vitals.json   vitals at each visit, companion EMR data

HOLDOUT PATIENTS
    P21 and up are the held-out evaluation set and write to corpus/data/holdout/ -
    its own pdfs/, html/, answers/ and vitals/. A separate tree, because a holdout
    that can be mixed into the training corpus by a forgotten flag is not a holdout.
    They carry HOLDOUT = True in their module and are checked more loosely: they are
    five-report arcs, not fifteen, so the corpus-shape rules do not apply to them.

No data JSON is written next to the PDFs. The checks at the end are the corpus spec's own
coverage rules, so a run that quietly drops a panel or a trap fails instead of passing.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import catalog as C  # noqa: E402
import render as R  # noqa: E402
import vocabulary as V  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "corpus" / "data"
HOLDOUT_FROM = 21          # P21-P30 are the held-out evaluation set
BENCHMARK_FROM = 31        # P31-P40 are the 30-panel vocabulary fixtures
DEMO_FROM = 41             # P41 and up are disposable presentation material
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
EDGE_ALT = Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")

CORE_PANELS = ["CBC", "LIPID", "DIABETES", "LFT", "KFT", "THYROID",
               "URINE_ROUTINE", "ELECTROLYTES", "IRON", "VITAMIN"]

TECHNICIANS = ["Y. Gaikwad (DMLT)", "S. Pawar (B.Sc. MLT)", "A. Jadhav (DMLT)",
               "M. Shaikh (B.Sc. MLT)"]

REPORT_FIELDS = ["report_id", "pdf_path", "patient_number", "uhid", "patient_name", "sex",
                 "age_printed", "collected_at", "reported_at", "lab_name", "uhid_label",
                 "referring_doctor", "department", "expected_panels", "layout_style",
                 "header_style", "traps"]
ROW_FIELDS = ["report_id", "section_heading", "printed_label", "code", "value", "unit",
              "reference", "method", "flag", "trap"]


def age_on(dob: str, when: str) -> int:
    d = date.fromisoformat(dob)
    t = date.fromisoformat(when[:10])
    return t.year - d.year - ((t.month, t.day) < (d.month, d.day))


def dmy(stamp: str) -> str:
    dt = datetime.fromisoformat(stamp)
    return dt.strftime("%d/%m/%Y %I:%M %p").replace(" 0", " ")


def accession(lab: dict, seq: int, collected: str) -> str:
    """Each lab numbers its samples its own way - part of what the parser has to survive."""
    yy = collected[2:4]
    abbr = lab.get("abbr") or "".join(w[0] for w in lab["name"].split()[:3]).upper()
    style = lab.get("acc_style", 0) % 4
    if style == 1:
        return f"{abbr}/20{yy}/{3000 + seq * 137:05d}"
    if style == 2:
        return f"{abbr}{yy}-{40000 + seq * 913:06d}"
    if style == 3:
        return f"{abbr}-{yy}-{seq * 211 + 640:05d}"
    return f"{abbr}/{yy}/{seq * 431 + 1170:06d}"


# ----------------------------------------------------------------------- compose


def _row(code: str | None, spec: dict, values: dict, alias: int,
         labels: dict, methods: bool, row_traps: dict,
         sex: str = "M", age: int = 40) -> dict:
    """One printed test line, as it appears on the page and in the key.

    The printed reference range and the H/L flag both come from ``catalog.ref`` for this
    patient's sex and age, so a woman's haemoglobin and a child's creatinine are judged
    against their own ranges rather than an adult male's.
    """
    if code:
        # V answers from catalog first and the 30-panel benchmark second, so a
        # report can declare a culture or a serology analyte that the corpus
        # vocabulary has never contained. For every code catalog DOES have, V
        # returns catalog's own answer - verified in vocabulary.demo() - so the
        # 300 existing reports render byte for byte as before.
        spellings = V.labels(code)
        raw = spec["value"] if "value" in spec else values.get(code)
        label = (spec.get("label") or labels.get(code)
                 or spellings[alias % len(spellings)])
        unit = spec.get("unit", V.unit(code))
        ref = spec.get("reference", V.reference(code, sex, age))
        value = spec["value"] if isinstance(spec.get("value"), str) else V.fmt(code, raw)
        flag = spec.get("flag", V.flag(code, raw, sex, age))
        method = C.METHODS.get(code, "") if methods else ""
    else:
        raw = spec.get("value")
        label = spec["label"]
        unit = spec.get("unit", "")
        ref = spec.get("reference", "")
        value = str(raw)
        flag = spec.get("flag", "")
        method = spec.get("method", "")
    trap = spec.get("trap") or row_traps.get(code or "", "")
    return {"printed_label": label, "code": code or "", "value": value, "unit": unit,
            "reference": ref, "method": method, "flag": flag, "trap": trap,
            "marker": spec.get("marker", ""), "hand": spec.get("hand", False),
            "prev": spec.get("prev", ""), "lab_code": spec.get("lab_code", "")}


def compose(patient: dict, labs: dict, spec: dict, seq: int) -> dict:
    """Expand an authored report spec into the exact rows the page will print."""
    lab_key = spec["lab"]
    lab = labs[lab_key]
    pid = f"P{patient['number']:02d}"
    rid = f"{pid}-R{seq:02d}"
    age = age_on(patient["dob"], spec["collected"])
    alias_default = spec.get("alias", 0)

    sections, panels, traps = [], [], set(spec.get("traps", []))
    for sec in spec["sections"]:
        codes: list[str] = []
        sec_panels = sec.get("panels") or ([sec["panel"]] if "panel" in sec else [])
        drop = set(sec.get("drop", []))
        methods = bool(sec.get("methods"))
        if methods:
            traps.add("method_sub_line")
        if sec.get("legend"):
            traps.add("legend_lines")
        if sec.get("sample_row"):
            traps.add("sample_type_row")
        if sec.get("trap"):
            traps.add(sec["trap"])

        heading = sec.get("heading")
        if sec_panels and not heading:
            p = sec_panels[0]
            titles = V.panel_titles(p)
            heading = titles[sec.get("title", 0) % len(titles)]
        for p in sec_panels:
            codes += [c for c in V.panel_analytes(p) if c not in drop]
        panels += sec_panels

        raw_vals = {k: v for k, v in sec.get("values", {}).items() if not isinstance(v, str)}
        text_vals = {k: v for k, v in sec.get("values", {}).items() if isinstance(v, str)}
        row_specs = sec.get("rows", [])
        for rs in row_specs:
            if rs.get("code") and "value" in rs and not isinstance(rs["value"], str):
                raw_vals[rs["code"]] = rs["value"]
        values = C.derive(raw_vals, age, patient["sex"])
        values.update(text_vals)

        alias = sec.get("alias", alias_default)
        labels = sec.get("labels", {})
        row_traps = sec.get("row_traps", {})
        rows = []
        if codes:
            rows += [_row(c, {}, values, alias, labels, methods, row_traps,
                          patient["sex"], age)
                     for c in codes if c in values]
        for rs in row_specs:
            merged = dict(rs)
            if rs.get("code") and "value" not in rs:
                merged["value"] = values.get(rs["code"])
                if merged["value"] is None:
                    continue
                if not isinstance(merged["value"], str):
                    del merged["value"]  # let _row format it from values
            rows.append(_row(rs.get("code"), merged, values, alias, labels, methods,
                             row_traps, patient["sex"], age))
        for rs in sec.get("extra_rows", []):
            rows.append(_row(rs.get("code"), rs, values, alias, labels, methods,
                             row_traps, patient["sex"], age))

        prev_map = sec.get("prev", {})
        code_map = sec.get("lab_codes", {})
        for r in rows:
            if r["trap"]:
                traps.add(r["trap"])
            if not r["prev"] and r["code"] in prev_map:
                r["prev"] = prev_map[r["code"]]
            if not r["lab_code"] and r["code"] in code_map:
                r["lab_code"] = code_map[r["code"]]
        sections.append({"heading": heading, "rows": rows, "legend": sec.get("legend"),
                         "sample_row": sec.get("sample_row"), "sub": sec.get("sub"),
                         "hand_addendum": sec.get("hand_addendum", False),
                         "panels": sec_panels, "values": values})

    if spec.get("footnotes"):
        traps.add("footnote_marker")
    if spec.get("interpretation"):
        traps.add("interpretation_block")
    KIND_TRAPS = {"chat_screenshot": "chat_screenshot", "register_page": "register_page",
                  "discharge_summary": "labs_inside_discharge_summary",
                  "range_bar": "range_bar_graphic"}
    if spec["layout_style"] in KIND_TRAPS:
        traps.add(KIND_TRAPS[spec["layout_style"]])
    if spec["layout_style"] == "register_page":
        traps.add("other_patients_on_page")
    DAMAGE_TRAPS = {"aged": "aged_paper", "fold": "fold_creases", "stain": "stain_damage",
                    "torn": "torn_corner", "crop-right": "cropped_edge",
                    "crop-left": "cropped_edge", "crop-bottom": "cropped_edge",
                    "blur": "blurred_photo", "dark": "poor_lighting",
                    "thumb": "finger_over_page", "scanborder": "scanner_border"}
    for d in spec.get("damage", []):
        traps.add(DAMAGE_TRAPS.get(d, d))
    if spec.get("illegible"):
        traps.add("illegible_scan")

    rep = {
        "report_id": rid, "patient_number": patient["number"],
        "patient_name": patient["name"], "sex": patient["sex"], "uhid": patient["uhid"],
        "uhid_label": spec["uhid_label"], "age_printed": age,
        "collected_at": spec["collected"], "reported_at": spec["reported"],
        "collected_printed": dmy(spec["collected"]), "reported_printed": dmy(spec["reported"]),
        "lab": lab, "lab_key": lab_key, "accession": accession(lab, seq, spec["collected"]),
        "referring_doctor": spec["doctor"], "department": patient["department"],
        "specimen": spec["specimen"], "layout_style": spec["layout_style"],
        "header_style": spec["header_style"], "traps": sorted(traps),
        "expected_panels": panels, "sections": sections,
        "pathologist": lab["path"], "technician": TECHNICIANS[seq % len(TECHNICIANS)],
        "footnotes": spec.get("footnotes", []), "note": spec.get("note", ""),
        "age": age,
    }
    for key in ("stamp", "page_break_after", "interpretation", "damage", "illegible",
                "discharge"):
        if key in spec:
            rep[key] = spec[key]
    return rep


# ------------------------------------------------------------------------- print


def edge_print(html: Path, pdf: Path) -> None:
    exe = EDGE if EDGE.exists() else EDGE_ALT
    if not exe.exists():
        raise SystemExit(f"Microsoft Edge not found at {EDGE} or {EDGE_ALT}")
    pdf.parent.mkdir(parents=True, exist_ok=True)
    profile = Path(tempfile.mkdtemp(prefix="corpus-edge-"))
    try:
        subprocess.run(
            [str(exe), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             f"--user-data-dir={profile}", "--no-first-run", "--disable-extensions",
             f"--print-to-pdf={pdf}", html.resolve().as_uri()],
            check=True, capture_output=True, timeout=120,
        )
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    if not pdf.exists() or pdf.stat().st_size < 4000:
        raise SystemExit(f"{pdf} did not render (size {pdf.stat().st_size if pdf.exists() else 0})")


def page_count(pdf: Path) -> int:
    blob = pdf.read_bytes()
    return len(re.findall(rb"/Type\s*/Page[^s]", blob)) or 1


# -------------------------------------------------------------------------- key


def write_vitals(patient: dict, reps: list[dict], height_cm: float, vitals: dict,
                 dirs: dict[str, Path]) -> Path:
    """Vitals recorded at each lab-report visit, as vitals/P<nn>-vitals.json.

    Companion EMR data, deliberately kept out of generated/corpus/ - the parser is given
    the PDFs and nothing else. BMI is computed here from the authored height and weight,
    so it cannot disagree with them; blood pressure stays TEXT "148/94" to match the
    production column, which is split at query time.
    """
    out = dirs["vitals"]
    out.mkdir(parents=True, exist_ok=True)
    missing = [i for i in range(1, len(reps) + 1) if i not in vitals]
    if missing:
        raise SystemExit(f"no vitals authored for report(s) {missing}")
    rows = []
    for seq, rep in enumerate(reps, start=1):
        v = vitals[seq]
        row_height = v.get("height_cm", height_cm)
        sys_, dia = (int(x) for x in v["bp"].split("/"))
        assert 70 <= sys_ <= 220 and 35 <= dia <= 130 and sys_ > dia, f"BP {v['bp']} seq {seq}"
        assert 85 <= v["spo2"] <= 100, f"SpO2 {v['spo2']} seq {seq}"
        assert 95.0 <= v["temp_f"] <= 106.0, f"temperature {v['temp_f']} seq {seq}"
        assert 8.0 <= v["weight_kg"] <= 200.0, f"weight {v['weight_kg']} seq {seq}"
        assert 60.0 <= row_height <= 210.0, f"height {row_height} seq {seq}"
        rows.append({
            "report_id": rep["report_id"],
            "date": rep["collected_at"][:10],
            "age_years": rep["age_printed"],
            "height_cm": v.get("height_cm", height_cm),
            "weight_kg": v["weight_kg"],
            "bmi": round(v["weight_kg"] / (v.get("height_cm", height_cm) / 100) ** 2, 1),
            "blood_pressure": v["bp"],
            "spo2_pct": v["spo2"],
            "temperature_f": v["temp_f"],
            "context": v.get("context", ""),
        })
    path = out / f'P{patient["number"]:02d}-vitals.json'
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return path


def _drop_patient(path: Path, fields: list[str], pid: str) -> list[dict]:
    """Existing rows minus this patient's, so a rebuild replaces rather than duplicates."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if not r["report_id"].startswith(pid + "-")]


def write_key(reps: list[dict], fresh: bool, dirs: dict[str, Path]) -> None:
    ans = dirs["answers"]
    ans.mkdir(parents=True, exist_ok=True)
    rpath, xpath = ans / "reports.csv", ans / "rows.csv"
    pid = f'P{reps[0]["patient_number"]:02d}'
    keep = [] if fresh else _drop_patient(rpath, REPORT_FIELDS, pid)
    with rpath.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, REPORT_FIELDS)
        w.writeheader()
        w.writerows(keep)
        for rep in reps:
            w.writerow({
                "report_id": rep["report_id"],
                "pdf_path": f'pdfs/P{rep["patient_number"]:02d}/{rep["report_id"]}.pdf',
                "patient_number": rep["patient_number"], "uhid": rep["uhid"],
                "patient_name": rep["patient_name"], "sex": rep["sex"],
                "age_printed": rep["age_printed"], "collected_at": rep["collected_at"],
                "reported_at": rep["reported_at"], "lab_name": rep["lab"]["name"],
                "uhid_label": rep["uhid_label"], "referring_doctor": rep["referring_doctor"],
                "department": rep["department"],
                "expected_panels": "|".join(rep["expected_panels"]),
                "layout_style": rep["layout_style"], "header_style": rep["header_style"],
                "traps": "|".join(rep["traps"]),
            })
    keep_rows = [] if fresh else _drop_patient(xpath, ROW_FIELDS, pid)
    with xpath.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ROW_FIELDS)
        w.writeheader()
        w.writerows(keep_rows)
        for rep in reps:
            for sec in rep["sections"]:
                for row in sec["rows"]:
                    w.writerow({"report_id": rep["report_id"],
                                "section_heading": sec["heading"] or "",
                                "printed_label": row["printed_label"], "code": row["code"],
                                "value": row["value"], "unit": row["unit"],
                                "reference": row["reference"], "method": row["method"],
                                "flag": row["flag"], "trap": row["trap"]})


# ------------------------------------------------------------------------ checks


def _numeric(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return True


def _tree(mod) -> str:
    """Which tree this patient writes to, and "" for the training corpus.

    demo is deliberately a tree of its own: it is built to look good, which is
    precisely the bias a measurement must not contain. Nothing scores against it.
    """
    if getattr(mod, "DEMO", False):
        return "demo"
    if getattr(mod, "BENCHMARK", False):
        return "benchmark"
    if getattr(mod, "HOLDOUT", False):
        return "holdout"
    return ""


def checks(patient: dict, reps: list[dict], pdfs: list[Path], mod=None) -> list[str]:
    """Coverage rules. A holdout patient is a short arc, so the rules that describe
    the *shape of the training corpus* - fifteen reports, each core panel on two or
    three of them, a tracked analyte on eight - are skipped for it. The rules that
    describe a report being *correct* still apply to everything."""
    fails = []
    # Both the holdout and the benchmark fixtures are short arcs, so the rules
    # that describe the SHAPE of the training corpus do not apply to either. The
    # rules about a report being CORRECT apply to everything.
    holdout = bool(mod is not None and _tree(mod))
    benchmark = bool(mod is not None and getattr(mod, "BENCHMARK", False))
    demo = bool(mod is not None and getattr(mod, "DEMO", False))
    n_expected = len(mod.REPORTS) if holdout and mod is not None else 15

    def want(cond, msg):
        if not cond:
            fails.append(msg)

    want(len(reps) == n_expected, f"expected {n_expected} reports, got {len(reps)}")
    dates = [r["collected_at"] for r in reps]
    want(dates == sorted(dates), "collection dates are not in chronological order")
    want(all("2021-09-18" <= d[:10] <= "2026-09-18" for d in dates),
         "a collection date falls outside the five-year window")
    want(len({r["uhid"] for r in reps}) == 1, "the UHID is not identical on all reports")
    ages = [r["age_printed"] for r in reps]
    first = patient["age_at_first"]
    want(ages == sorted(ages) and ages[0] == first,
         f'ages do not advance from {first}: {ages}')

    panel_reports: dict[str, set[str]] = {p: set() for p in CORE_PANELS}
    for rep in reps:
        for p in rep["expected_panels"]:
            if p in panel_reports:
                panel_reports[p].add(rep["report_id"])
    if not holdout:
        for p, ids in panel_reports.items():
            want(2 <= len(ids) <= 3, f"{p} appears on {len(ids)} reports, need 2 or 3")

    titles: dict[str, set[str]] = {}
    for rep in reps:
        for sec in rep["sections"]:
            for p in sec["panels"]:
                titles.setdefault(p, set()).add(sec["heading"])
    for p, t in titles.items():
        if p in CORE_PANELS and not holdout:
            want(len(t) == len(panel_reports[p]) or len(t) > 1,
                 f"{p} printed the same title every time: {t}")

    layouts = {r["layout_style"] for r in reps}
    # A holdout report is one layout the extractor has never met, so no repeats.
    # A benchmark fixture is about the VOCABULARY, not the layout, so it reuses
    # ordinary ones on purpose - a new analyte failing on a familiar layout is
    # unambiguous about which of the two went wrong.
    want(len(layouts) >= (len(reps) if demo else 3 if benchmark
                          else len(reps) if holdout else 6),
         f"only {len(layouts)} layouts used")
    labs = {r["lab"]["name"] for r in reps}
    want(len(labs) >= (2 if (benchmark or demo) else 3), f"only {len(labs)} labs used")
    traps = {t for r in reps for t in r["traps"]}
    want(len(traps) >= (2 if demo else 4 if holdout else 8),
         f"only {len(traps)} traps used: {sorted(traps)}")

    all_rows = [(r, s, row) for r in reps for s in r["sections"] for row in s["rows"]]
    coded = {row["code"] for _, _, row in all_rows if row["code"]}
    uncoded = {row["printed_label"] for _, _, row in all_rows if not row["code"]}
    want(len(coded) + len(uncoded) >= (10 if demo else 20 if benchmark
                                       else 25 if holdout else 45),
         f"only {len(coded) + len(uncoded)} distinct tests")
    # A benchmark fixture prints the NEW vocabulary, all of which has a code by
    # construction. Demanding uncoded rows of it would be demanding noise.
    want(len(uncoded) >= (0 if (benchmark or demo) else 3 if holdout else 4),
         f"only {len(uncoded)} tests without a code")
    texts = [row for _, _, row in all_rows
             if row["trap"] == "text_result" or row["code"] in
             ("BLOOD_GROUP", "PERIPH_SMEAR", "URINE_CULTURE")]
    # The fixtures exist largely FOR the non-numeric types, so they are held to
    # a higher bar than the corpus rather than a lower one.
    want(len(texts) >= (0 if demo else 12 if benchmark else 3),
         f"only {len(texts)} text results")

    if not holdout:
        checks_5 = [r for r in reps
                    if len([p for p in r["expected_panels"] if p in CORE_PANELS]) >= 5]
        want(len(checks_5) >= 2, f"only {len(checks_5)} health-check reports with 5+ panels")
        singles = [r for r in reps if sum(len(s["rows"]) for s in r["sections"]) == 1]
        want(len(singles) >= 2, f"only {len(singles)} single-test reports")

    # the disease-tracking test must appear often enough to draw a line
    series: dict[str, list[tuple[str, float]]] = {}
    # A benchmark fixture exists to prove a vocabulary can be read, not to draw
    # a line. Two points is enough to check the arc still makes clinical sense -
    # check_arc still runs - without forcing the same analyte onto a culture
    # report and a blood group report where no lab would print it.
    need_hits = 2 if (benchmark or demo) else 4 if holdout else 8
    for code in patient["tracked"]:
        hits = [r for r in reps
                if any(row["code"] == code for s in r["sections"] for row in s["rows"])]
        want(len(hits) >= need_hits,
             f"{code} on only {len(hits)} of {len(reps)} reports")
        series[code] = [
            (r["collected_at"][:10], float(row["value"]))
            for r in reps for s in r["sections"] for row in s["rows"]
            if row["code"] == code and _numeric(row["value"])
        ]
    if mod is not None and hasattr(mod, "check_arc"):
        fails.extend(mod.check_arc(series))

    for rep in reps:
        for sec in rep["sections"]:
            bad = C.check_derived(sec["values"], rep["age"], rep["sex"])
            for b in bad:
                fails.append(f'{rep["report_id"]} {sec["heading"]}: {b}')

    for rep, pdf in zip(reps, pdfs or []):
        want(pdf.exists() and pdf.stat().st_size > 4000, f"{pdf.name} missing or too small")
        pages = page_count(pdf)
        if rep["layout_style"] in ("thermal_slip", "chat_screenshot",
                                   "discharge_summary"):
            continue  # a roll, a screenshot and a discharge summary run to any length
        expect = 2 if rep["layout_style"] == "continuation" else 1
        want(pages == expect,
             f'{rep["report_id"]} ({rep["layout_style"]}) rendered {pages} pages, expected {expect}')
    return fails


# --------------------------------------------------------------------------- main


def parse_patients(spec: str) -> list[int]:
    """`3`, `2-20`, `1,4,9`, `all` (the training corpus) or `holdout` (P21 up)."""
    word = spec.strip().lower()
    if word == "all":
        return [n for n in sorted(int(f.stem[1:])
                                  for f in (Path(__file__).parent / "patients").glob("p*.py")
                                  if f.stem[1:].isdigit())
                if n < HOLDOUT_FROM]
    pdir = Path(__file__).parent / "patients"
    found = sorted(int(f.stem[1:]) for f in pdir.glob("p*.py") if f.stem[1:].isdigit())
    if word == "holdout":
        return [n for n in found if HOLDOUT_FROM <= n < BENCHMARK_FROM]
    if word == "benchmark":
        return [n for n in found if BENCHMARK_FROM <= n < DEMO_FROM]
    if word == "demo":
        return [n for n in found if n >= DEMO_FROM]
    out: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            lo, hi = (int(x) for x in part.split("-"))
            out += list(range(lo, hi + 1))
        else:
            out.append(int(part))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--patient", required=True,
                    help="patient number, a range (2-20), a list (1,4,9), "
                         "'all' (the training corpus), 'holdout' (the evaluation "
                         "set), 'benchmark' (the vocabulary fixtures) or 'demo' "
                         "(disposable presentation material)")
    ap.add_argument("--fresh", action="store_true", help="truncate the answer key first")
    ap.add_argument("--html-only", action="store_true", help="skip the PDF print step")
    ap.add_argument("--key-only", action="store_true",
                    help="rewrite the answer key and vitals without rendering anything")
    ap.add_argument("--only", type=int, nargs="*", metavar="N",
                    help="rebuild only these report numbers (skips the key and checks)")
    args = ap.parse_args()

    wanted = parse_patients(args.patient)
    if len(wanted) > 1:
        failed, fresh = [], args.fresh
        for n in wanted:
            rc = build_patient(n, fresh, args.html_only, None, args.key_only)
            fresh = False  # only the first patient may truncate the key
            if rc:
                failed.append(n)
            print()
        print("=" * 78)
        print(f'{len(wanted) - len(failed)}/{len(wanted)} patients built and checked'
              + (f"; FAILED: {failed}" if failed else ""))
        return 1 if failed else 0
    return build_patient(wanted[0], args.fresh, args.html_only, args.only, args.key_only)


def build_patient(number: int, fresh: bool, html_only: bool, only: list[int] | None,
                  key_only: bool = False) -> int:
    """Build one patient end to end. Returns 0 when every coverage check passes."""
    mod = importlib.import_module(f"patients.p{number:02d}")
    pid = f"P{number:02d}"
    # Three trees, and nothing merges them.
    #   DATA              the 300-report training corpus
    #   DATA/holdout      the evaluation set - see docs/holdout-testset.md
    #   DATA/benchmark    fixtures for the 30-panel vocabulary, which exist to
    #                     prove a culture or a serology report can be read at
    #                     all, not to measure anything
    # Separate because a number is only meaningful if you know which population
    # it came from, and a flag someone forgets is how populations get mixed.
    base = DATA / _tree(mod) if _tree(mod) else DATA
    dirs = {"html": base / "html" / pid, "pdfs": base / "pdfs" / pid,
            "answers": base / "answers", "vitals": base / "vitals"}
    html_dir, pdf_dir = dirs["html"], dirs["pdfs"]
    dirs["vitals"].mkdir(parents=True, exist_ok=True)
    html_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    reps, pdfs = [], []
    for i, spec in enumerate(mod.REPORTS, start=1):
        if only and i not in only:
            continue
        rep = compose(mod.PATIENT, mod.LABS, spec, i)
        html = html_dir / f'{rep["report_id"]}.html'
        if not key_only:
            html.write_text(R.render(rep), encoding="utf-8")
        pdf = pdf_dir / f'{rep["report_id"]}.pdf'
        if not html_only and not key_only:
            edge_print(html, pdf)
        reps.append(rep)
        pdfs.append(pdf)
        rows = sum(len(s["rows"]) for s in rep["sections"])
        print(f'{rep["report_id"]}  {rep["collected_at"][:10]}  {rep["layout_style"]:<19}'
              f'{rep["lab"]["name"]:<30}{rows:>3} tests  '
              f'{"|".join(rep["expected_panels"]) or "-"}')

    if only:
        print(f'\nrebuilt {len(reps)} report(s); answer key and checks left untouched')
        return 0
    if html_only:
        fails = checks(mod.PATIENT, reps, None, mod)
        print("\nHTML only - coverage checked, answer key left untouched.")
        for f in fails:
            print(f"  - {f}")
        return 1 if fails else 0

    write_key(reps, fresh, dirs)
    vitals_path = write_vitals(mod.PATIENT, reps, mod.HEIGHT_CM, mod.VITALS, dirs)
    if key_only:
        print(f"\n{pid}: answer key and vitals rewritten, nothing rendered")
        return 0

    fails = checks(mod.PATIENT, reps, pdfs, mod)
    print(f'\n{pid}: {len(reps)} PDFs in {pdf_dir.relative_to(ROOT)}, '
          f'key in {dirs["answers"].relative_to(ROOT)}, vitals in '
          f'{vitals_path.relative_to(ROOT)}')
    if fails:
        print("\nFAILED CHECKS:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("all coverage checks pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
