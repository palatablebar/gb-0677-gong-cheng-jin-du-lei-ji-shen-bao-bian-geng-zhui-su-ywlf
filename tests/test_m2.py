from app.modules.m2_billitems.rules import evaluate
from app.values import number
from decimal import Decimal
def test_real_alias_mapped(result): assert result["stages"][1]["rows"][0]["item"]=="001"
def test_real_units(result): assert {r["unit"] for r in result["stages"][1]["rows"]}=={"t","m³"}
def test_real_unknown_item(result): assert any(r["reason"]=="UNKNOWN_ITEM" for r in result["stages"][1]["quarantine"])
def test_real_null_not_zero(result):
    "TRAP-07"
    assert any(r["reason"]=="EMPTY_VALUE" for r in result["stages"][1]["quarantine"])
def test_fullwidth_quantity():
    "TRAP-06"
    assert number("１,２５０.００")==Decimal("1250.00")
def test_negative_cumulative():
    r=evaluate([{"item":"001","cumulative_qty":"-1","previous_qty":"0","reported":"0"}],{});assert r["quarantine"][0]["reason"]=="NEGATIVE_CUMULATIVE"
def test_real_id_zero_preserved(result): assert result["stages"][1]["rows"][0]["claim_id"]=="00001"
