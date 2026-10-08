"""Generate the patient seed SQL from the corpus patient modules.

    python db/seed/export_patients.py              -> db/005_seed_practice_and_patients.sql
    python db/seed/export_patients.py --holdout    -> db/019_seed_holdout_patients.sql
    python db/seed/export_patients.py --benchmark  -> db/023_seed_benchmark_patients.sql

One demo practice, one seed user, and the synthetic patients the corpus was built
around - name, sex, date of birth, UHID and city, exactly as the generator invented
them. The UHIDs are what fn_match_patient_by_uhid matches documents against, so they
have to agree to the character.

The holdout patients (P21 up) get their own migration rather than being appended to
005, so a database can be loaded with the training corpus alone. Run 006 only when
you intend to score the extractor; leaving it out means those three UHIDs match no
patient and every holdout document quarantines, which is the correct behaviour for a
patient the practice has never seen.

Everything here is synthetic. No row describes a real person.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "corpus" / "generator"))

PATIENTS_DIR = ROOT / "corpus" / "generator" / "patients"
HOLDOUT_FROM = 21  # keep in step with corpus/generator/build.py
BENCHMARK_FROM = 31  # the 30-panel vocabulary fixtures
DEMO_FROM = 41  # disposable presentation material

PRACTICE_NAME = "Contexta Demo Clinic"
SEED_USER = "idp.seed@contexta.local"


def q(value) -> str:
    if value is None or value == "":
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def patient_numbers(which: str) -> list[int]:
    """Whichever patient modules exist, split at the holdout boundary."""
    found = sorted(int(f.stem[1:]) for f in PATIENTS_DIR.glob("p*.py") if f.stem[1:].isdigit())
    if which == "demo":
        return [n for n in found if n >= DEMO_FROM]
    if which == "benchmark":
        return [n for n in found if BENCHMARK_FROM <= n < DEMO_FROM]
    if which == "holdout":
        return [n for n in found if HOLDOUT_FROM <= n < BENCHMARK_FROM]
    return [n for n in found if n < HOLDOUT_FROM]


def main() -> None:
    which = (
        "demo"
        if "--demo" in sys.argv
        else "benchmark"
        if "--benchmark" in sys.argv
        else "holdout"
        if "--holdout" in sys.argv
        else "training"
    )
    holdout = which != "training"  # neither seeds the practice or user
    out = (
        ROOT
        / "db"
        / {
            "training": "005_seed_practice_and_patients.sql",
            "holdout": "019_seed_holdout_patients.sql",
            "benchmark": "023_seed_benchmark_patients.sql",
            "demo": "029_seed_demo_patient.sql",
        }[which]
    )
    numbers = patient_numbers(which)
    if not numbers:
        sys.exit("no patient modules found for that range")

    patients = []
    for n in numbers:
        mod = importlib.import_module(f"patients.p{n:02d}")
        p = mod.PATIENT
        first, _, last = p["name"].partition(" ")
        patients.append(
            {
                "uhid": p["uhid"],
                "first": first,
                "last": last or first,
                "dob": p["dob"],
                "sex": p["sex"],
                "city": p.get("city"),
                "dept": p.get("department"),
                "brief": p.get("brief"),
            }
        )

    lines: list[str] = []
    add = lines.append
    src = (
        f"p{numbers[0]:02d}.py .. p{numbers[-1]:02d}.py"
        if len(numbers) > 1
        else f"p{numbers[0]:02d}.py"
    )
    flag = f" --{which}" if which != "training" else ""
    add("-- =============================================================================")
    add("-- Contexta - Lab extraction store")
    if holdout:
        label = {
            "benchmark": "BENCHMARK vocabulary fixture",
            "demo": "DEMO presentation",
            "holdout": "HELD-OUT evaluation",
        }[which]
        number = {"benchmark": "023", "demo": "029", "holdout": "019"}[which]
        add(f"-- {number}  Seed: the {len(numbers)} {label} patient(s)")
    else:
        add(f"-- 005  Seed: demo practice, seed user, {len(numbers)} synthetic patients")
    add("-- =============================================================================")
    add("-- GENERATED FILE - do not edit by hand.")
    add(f"--   Source:     corpus/generator/patients/{src}")
    add(f"--   Regenerate: python db/seed/export_patients.py{flag}")
    add("--")
    if holdout:
        add("-- These three are the evaluation set. Their PDFs live in")
        add("-- corpus/data/holdout/ and are loaded only by")
        add("-- scripts/load_corpus.py --holdout.")
        add("--")
        add("-- Numbered last on purpose: it must run after 005 has created the")
        add("-- practice these patients hang off, and it is the one migration a")
        add("-- normal setup is expected to skip.")
        add("--")
        add("-- Apply this migration ONLY when you intend to score the extractor. Without")
        add("-- it these UHIDs match no patient, so every holdout document lands in the")
        add("-- review queue - which is the right answer for a patient the practice has")
        add("-- never registered, and is itself worth testing.")
    else:
        add("-- Every person below is invented. The UHIDs are the ones printed on the 300")
        add("-- corpus PDFs, so scripts/load_corpus.py can match documents to patients the")
        add("-- same way the real pipeline will: by reading the UHID off the page.")
    add("-- =============================================================================")
    add("")
    add("BEGIN;")
    add("")
    if not holdout:
        add("-- ------------------------------------------------------------- practice")
        add("INSERT INTO core.practices (name, city)")
        add(f"VALUES ({q(PRACTICE_NAME)}, 'Pune')")
        add("ON CONFLICT DO NOTHING;")
        add("")
        add("-- ----------------------------------------------------------- seed user")
        add("-- The actor recorded as created_by on everything the loader writes.")
        add("INSERT INTO core.users (practice_id, email, full_name, role)")
        add("SELECT p.id, " + q(SEED_USER) + ", 'Corpus Loader', 'service'")
        add(f"FROM core.practices p WHERE p.name = {q(PRACTICE_NAME)}")
        add("ON CONFLICT (email) DO NOTHING;")
        add("")
    add("-- ------------------------------------------------------------- patients")
    add("INSERT INTO core.patients (practice_id, uhid, first_name, last_name, dob,")
    add("                           gender, city, created_by)")
    add("SELECT pr.id, v.uhid, v.first_name, v.last_name, v.dob::DATE, v.gender,")
    add("       v.city, u.id")
    add("FROM (VALUES")
    # The case note goes on its own line above the row: a trailing comment would
    # swallow the comma that separates one VALUES row from the next.
    rows = [
        f"    -- {p['dept']}: {p['brief']}\n"
        f"    ({q(p['uhid'])}, {q(p['first'])}, {q(p['last'])}, "
        f"{q(p['dob'])}, {q('Male' if p['sex'] == 'M' else 'Female')}, "
        f"{q(p['city'])})"
        for p in patients
    ]
    add(",\n".join(rows))
    add(") AS v(uhid, first_name, last_name, dob, gender, city)")
    add("CROSS JOIN core.practices pr")
    add(f"LEFT JOIN core.users u ON u.email = {q(SEED_USER)}")
    add(f"WHERE pr.name = {q(PRACTICE_NAME)}")
    add("  AND NOT EXISTS (")
    add("      SELECT 1 FROM core.patients ex")
    add("      WHERE ex.practice_id = pr.id AND ex.uhid = v.uhid")
    add("  );")
    add("")
    add("COMMIT;")
    add("")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(
        f"wrote {out.relative_to(ROOT)}  ({len(patients)} patients: "
        f"{', '.join(f'P{n:02d}' for n in numbers)})"
    )


if __name__ == "__main__":
    main()
