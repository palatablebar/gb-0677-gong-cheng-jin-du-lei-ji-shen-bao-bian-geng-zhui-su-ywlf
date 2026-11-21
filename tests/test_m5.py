from app.modules.m5_deductions.rules import evaluate
from decimal import Decimal
import pytest
from app.errors import DomainError
def test_real_net_total(result): assert result["stages"][4]["metrics"]["net_total"]=="68425.00"
def test_retention_advance_separate():
    row=evaluate([{"gross_amount":"3000"}],{})["rows"][0];assert (row["retention"],row["advance_recovery"],row["expected"])==("150.00","300.00","2550.00")
def test_negative_deduction_reverses(): assert evaluate([{"gross_amount":"-100"}],{})["rows"][0]["expected"]=="-85.00"
def test_fraction_rounds_to_cent():
    "TRAP-10"
    row=evaluate([{"gross_amount":"0.13"}],{})["rows"][0];assert row["retention"]=="0.01" and row["advance_recovery"]=="0.01" and row["expected"]=="0.11"
def test_money_conservation_real_sample(result):
    assert all(Decimal(r["gross_amount"])==Decimal(r["retention"])+Decimal(r["advance_recovery"])+Decimal(r["expected"]) for r in result["stages"][4]["rows"])
def test_invalid_ratio_rejected():
    with pytest.raises(DomainError):evaluate([],{"parameters":{"retention_rate":"0.9","advance_rate":"0.2"}})
def test_empty_deductions_zero(): assert evaluate([],{})["metrics"]["net_total"]=="0.00"
