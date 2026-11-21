from decimal import Decimal
from app.values import number,money
from app.errors import DomainError
def evaluate(rows,context):
    p=context.get("parameters",{});retention=number(p.get("retention_rate","0.05"));advance=number(p.get("advance_rate","0.10"))
    if not Decimal(0)<=retention<=1 or not Decimal(0)<=advance<=1 or retention+advance>1:raise DomainError("BAD_DEDUCTION","扣回比例无效")
    good=[]
    for row in rows:
        gross=number(row["gross_amount"]);ret=number(money(gross*retention));adv=number(money(gross*advance));net=gross-ret-adv
        good.append({**row,"retention":money(ret),"advance_recovery":money(adv),"expected":money(net)})
    return {"rows":good,"quarantine":[],"metrics":{"gross_total":money(sum((number(r["gross_amount"]) for r in rows),Decimal(0))),"net_total":money(sum((number(r["expected"]) for r in good),Decimal(0)))}}
