from app.modules.m3_changes.rules import evaluate
def row(change="C1",period="2026-11"):return {"change_id":change,"period":period}
def test_real_unapproved_rejected(result): assert any(r["reason"]=="UNAPPROVED_CHANGE" for r in result["stages"][2]["quarantine"])
def test_effective_boundary():
    "TRAP-23"
    assert evaluate([row()],{})["rows"][0]["unit_price"]=="120.00"
def test_before_effective(): assert evaluate([row(period="2026-10")],{})["quarantine"][0]["reason"]=="CHANGE_NOT_EFFECTIVE"
def test_draft_price_not_used(): assert evaluate([row("DRAFT")],{})["rows"]==[]
def test_unknown_change(): assert evaluate([row("X")],{})["quarantine"][0]["reason"]=="UNAPPROVED_CHANGE"
def test_real_original_and_change_versions(result): assert result["stages"][2]["metrics"]["versions"]==["C0","C1"]
def test_negative_price_rejected(): assert evaluate([row()],{"parameters":{"changes":{"C1":{"approved":True,"effective":"2026-01","price":"-1"}}}})["quarantine"][0]["reason"]=="BAD_PRICE"
