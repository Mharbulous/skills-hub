#!/usr/bin/env python3
"""
get_legal_authorities_for_drafting.py -- Return legal criteria for a cause of action.

Queries causes_of_action joined via concept_id to law.legal_concepts and
law.legal_criteria to produce structured authority data for downstream
drafting agents. Requires law.sqlite (attached as 'law').

Usage:
    python get_legal_authorities_for_drafting.py --matter-root <path> --coa-id <id>

Returns JSON to stdout:
{
  "criteria": [
    {
      "concept_name": "Negligence",
      "concept_type": "cause_of_action",
      "criterion_id": 1,
      "requirement_type": "mandatory",
      "criterion_order": 1,
      "criterion_description": "Duty of care owed by defendant to plaintiff",
      "burden_of_proof": "balance_of_probabilities",
      "determined_by_concept_id": null,
      "determined_by_name": null,
      "authority_id": 3,
      "authority_title": "Donoghue v Stevenson",
      "authority_citation": "[1932] AC 562",
      "authority_proposition": "..."
    }
  ]
}

Exits non-zero on failure.
"""

import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile

from resolve_paths import load_pointer, resolve_case_data_dir

QUERY = """
SELECT
    lc.name AS concept_name,
    lc.concept_type,
    le.criterion_id,
    le.requirement_type,
    le.criterion_order,
    le.criterion_description,
    le.burden_of_proof,
    le.determined_by_concept_id,
    det.name AS determined_by_name,
    le.authority_id,
    a.title AS authority_title,
    a.citation AS authority_citation,
    le.authority_proposition
FROM causes_of_action coa
JOIN law.legal_concepts lc ON lc.concept_id = coa.concept_id
JOIN law.legal_criteria le ON le.concept_id = lc.concept_id
LEFT JOIN law.legal_concepts det ON det.concept_id = le.determined_by_concept_id
LEFT JOIN law.authorities a ON a.authority_id = le.authority_id
WHERE coa.coa_id = ?
ORDER BY le.criterion_order
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matter-root", required=True)
    parser.add_argument("--coa-id", required=True, type=int)
    args = parser.parse_args()

    matter_root = args.matter_root
    try:
        pointer = load_pointer(matter_root)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    case_data_dir = resolve_case_data_dir(matter_root, pointer["case_data_dir"])
    main_src = os.path.join(case_data_dir, "main.sqlite")
    if not os.path.exists(main_src):
        print("error: main.sqlite not found", file=sys.stderr)
        sys.exit(1)

    law_src = os.path.join(case_data_dir, "law.sqlite")
    if not os.path.exists(law_src):
        print("error: law.sqlite not found", file=sys.stderr)
        sys.exit(1)

    # FUSE safety: copy to temp dir before reading
    tmpdir = tempfile.mkdtemp(prefix="coclerk_law_")
    try:
        main_tmp = os.path.join(tmpdir, "main.sqlite")
        law_tmp = os.path.join(tmpdir, "law.sqlite")
        shutil.copy2(main_src, main_tmp)
        shutil.copy2(law_src, law_tmp)

        conn = sqlite3.connect(main_tmp)
        conn.row_factory = sqlite3.Row
        conn.execute(f"ATTACH DATABASE '{law_tmp}' AS law")

        # Check if causes_of_action table exists
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "causes_of_action" not in tables:
            conn.close()
            print(json.dumps({"criteria": []}, indent=2))
            return

        rows = conn.execute(QUERY, (args.coa_id,)).fetchall()

        criteria = []
        for row in rows:
            criteria.append({
                "concept_name": row["concept_name"],
                "concept_type": row["concept_type"],
                "criterion_id": row["criterion_id"],
                "requirement_type": row["requirement_type"],
                "criterion_order": row["criterion_order"],
                "criterion_description": row["criterion_description"],
                "burden_of_proof": row["burden_of_proof"],
                "determined_by_concept_id": row["determined_by_concept_id"],
                "determined_by_name": row["determined_by_name"],
                "authority_id": row["authority_id"],
                "authority_title": row["authority_title"],
                "authority_citation": row["authority_citation"],
                "authority_proposition": row["authority_proposition"],
            })

        conn.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print(json.dumps({"criteria": criteria}, indent=2))


if __name__ == "__main__":
    main()
