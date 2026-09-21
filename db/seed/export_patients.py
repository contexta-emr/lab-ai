"""Generate db/005_seed_practice_and_patients.sql from the corpus patient modules.

One demo practice, one seed user, and the twenty synthetic patients the corpus
was built around - name, sex, date of birth, UHID and city, exactly as the
generator invented them. The UHIDs are what fn_match_patient_by_uhid will match
the 300 documents against, so they have to agree to the character.

    python db/seed/export_patients.py

Everything here is synthetic. No row describes a real person.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "corpus" / "generator"))

OUT = ROOT / "db" / "005_seed_practice_and_patients.sql"

PRACTICE_NAME = "Contexta Demo Clinic"
SEED_USER = "idp.seed@contexta.local"


def q(value) -> str:
    if value is None or value == "":
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def main() -> None:
    patients = []
    for n in range(1, 21):
        mod = importlib.import_module(f"patients.p{n:02d}")
        p = mod.PATIENT
        first, _, last = p["name"].partition(" ")
        patients.append({
            "uhid": p["uhid"],
            "first": first,
            "last": last or first,
            "dob": p["dob"],
            "sex": p["sex"],
            "city": p.get("city"),
            "dept": p.get("department"),
            "brief": p.get("brief"),
        })

    L: list[str] = []
    add = L.append
    add("-- =============================================================================")
    add("-- Contexta - Lab extraction store")
    add("-- 005  Seed: demo practice, seed user, twenty synthetic patients")
    add("-- =============================================================================")
    add("-- GENERATED FILE - do not edit by hand.")
    add("--   Source:     corpus/generator/patients/p01.py .. p20.py")
    add("--   Regenerate: python db/seed/export_patients.py")
    add("--")
    add("-- Every person below is invented. The UHIDs are the ones printed on the 300")
    add("-- corpus PDFs, so scripts/load_corpus.py can match documents to patients the")
    add("-- same way the real pipeline will: by reading the UHID off the page.")
    add("-- =============================================================================")
    add("")
    add("BEGIN;")
    add("")
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
    rows = []
    for p in patients:
        rows.append(f"    -- {p['dept']}: {p['brief']}\n"
                    f"    ({q(p['uhid'])}, {q(p['first'])}, {q(p['last'])}, "
                    f"{q(p['dob'])}, {q('Male' if p['sex'] == 'M' else 'Female')}, "
                    f"{q(p['city'])})")
    add(",\n".join(rows))
    add(") AS v(uhid, first_name, last_name, dob, gender, city)")
    add(f"CROSS JOIN core.practices pr")
    add(f"LEFT JOIN core.users u ON u.email = {q(SEED_USER)}")
    add(f"WHERE pr.name = {q(PRACTICE_NAME)}")
    add("  AND NOT EXISTS (")
    add("      SELECT 1 FROM core.patients ex")
    add("      WHERE ex.practice_id = pr.id AND ex.uhid = v.uhid")
    add("  );")
    add("")
    add("COMMIT;")
    add("")

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(patients)} patients)")


if __name__ == "__main__":
    main()
