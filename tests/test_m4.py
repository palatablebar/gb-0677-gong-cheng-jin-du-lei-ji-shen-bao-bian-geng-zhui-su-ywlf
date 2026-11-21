from app.modules.m4_increment.rules import evaluate
def claim(id="A",current="125",previous="100",reversal="none"):return {"claim_id":id,"item":"001","period":"2026-11","cumulative_qty":current,"previous_qty":previous,"unit_price":"120","reversal":reversal}
def test_naive_cumulative_would_double_pay():
    r=evaluate([claim()],{})["rows"][0];assert r["increment_qty"]=="25" and r["gross_amount"]=="3000"
def test_previous_approval_revision():
    r=evaluate([claim()],{"parameters":{"previous_revisions":{"A":"110"}}})["rows"][0];assert r["increment_qty"]=="15" and r["gross_amount"]=="1800"
def test_negative_without_evidence(): assert evaluate([claim(current="90")],{})["quarantine"][0]["reason"]=="REVERSAL_REQUIRED"
def test_approved_reversal(): assert evaluate([claim(current="90",reversal="approved")],{})["rows"][0]["increment_qty"]=="-10"
def test_same_period_not_double_counted(): assert len(evaluate([claim("A"),claim("B")],{})["quarantine"])==1
def test_real_negative_isolated(result): assert any(r["reason"]=="REVERSAL_REQUIRED" for r in result["stages"][3]["quarantine"])
def test_zero_current_period_allowed(): assert evaluate([claim(current="100")],{})["rows"][0]["gross_amount"]=="0"
def test_real_sample_32_progress_rows(result): assert len(result["stages"][3]["rows"])==32
