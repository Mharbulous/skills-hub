# BC Litigation Deadline Rules

**Jurisdiction:** British Columbia only  
**Last verified:** 2026-04-14  
**Sources:** BC Limitation Act (SBC 2012, c 13); BC Supreme Court Civil Rules (BC Reg 168/2009); BC Court of Appeal Rules (BC Reg 297/2001)

> **Maintenance note:** BC court rules change. When a rule change is confirmed, update this file and set any affected `deadlines` rows to `status='stale'` so the practitioner can review them.

---

## Anchor Type: `trial_date`

Deadlines calculated backward from the trial date. All offsets are calendar days unless noted.

| Deadline Type | Offset | Rule | Description |
|---|---|---|---|
| `expert_report_plaintiff` | −84 days | Rule 11-6(3) | Plaintiff must serve expert report(s) at least 84 days before trial |
| `expert_report_defendant` | −42 days | Rule 11-6(4) | Defendant must serve expert report(s) at least 42 days before trial |
| `expert_report_responding` | −21 days | Rule 11-6(5) | Responding expert report served at least 21 days before trial |
| `witness_list` | −7 days | Rule 40-1(2)(d) | Serve witness list on all parties of record |
| `trial_record` | −14 days | Rule 40-1(2)(b) | File trial record in registry |

> **Verify:** Rule numbers above reflect the BC Supreme Court Civil Rules as known at the last verified date. Confirm against the current consolidation before relying on them. Practitioner should also check whether a Trial Management Conference Order has modified any of these deadlines — order terms override rule defaults.

---

## Anchor Type: `limitation_expiry`

The limitation expiry date is itself an anchor, not a derived deadline. It is calculated when the practitioner provides the **discovery date** (when the plaintiff knew or ought reasonably to have known of the claim and the identity of the defendant).

| Deadline Type | Offset | Rule | Description |
|---|---|---|---|
| `basic_limitation` | +2 years from discovery | Limitation Act s. 6 | Basic limitation period — commencing an action |
| `ultimate_limitation` | +15 years from act/omission | Limitation Act s. 21 | Ultimate limitation period regardless of discovery |

Store two anchor rows per matter when tracking limitation periods:
- `anchor_type='discovery_date'` — date of discovery (from instructions or documents)
- `anchor_type='act_date'` — date of act or omission (for ultimate period)

Then derive `limitation_expiry` (basic) and `ultimate_limitation_expiry` from those anchors.

> **Note:** Limitation Act exceptions exist (minors, persons under disability, fraud, concealment — ss. 7–18). When any exception may apply, flag it to the practitioner rather than calculating silently.

---

## Anchor Type: `appeal_date`

Deadlines for BC Court of Appeal matters, calculated from the date of the order or judgment being appealed.

| Deadline Type | Offset | Rule | Description |
|---|---|---|---|
| `notice_of_appeal` | +30 days from order | Court of Appeal Rules r. 14(1) | File and serve Notice of Appeal |
| `appeal_book` | Per scheduling order | Court of Appeal Rules r. 22 | File appeal book — date set by court |

> **Verify:** Appeal timelines are frequently modified by scheduling orders. Always check the specific order.

---

## Order Terms

When a court order contains deadline terms (e.g., a Trial Management Conference Order specifying "witness lists due 14 days before trial"), those terms override the rule defaults above.

Store each order term as a separate `deadlines` row:
- `source_type = 'order_term'`
- `rule_ref` = paragraph or term number in the order
- `rule_description` = the term as written
- `source_document` = order name and date (e.g., "TMC Order 2025-11-14")

If an order term conflicts with a rule default for the same deadline type, the order term governs. Mark the rule-default row `status='superseded'`.

---

## Working Day vs Calendar Day

The BC Supreme Court Civil Rules generally use **calendar days** for pre-trial deadlines. Where a deadline falls on a Saturday, Sunday, or BC statutory holiday, it shifts to the **next business day** (Rule 22-3). Apply this shift when calculating all dates above.

BC statutory holidays: New Year's Day, Family Day (3rd Monday of February), Good Friday, Victoria Day, Canada Day, BC Day (1st Monday of August), Labour Day, National Day for Truth and Reconciliation (Sept 30), Thanksgiving, Remembrance Day, Christmas Day.

When in doubt about whether a specific day qualifies, surface it to the practitioner.
