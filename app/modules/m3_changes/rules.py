from datetime import datetime
from app.values import number
from app.reasons import reject
from app.errors import DomainError
CHANGES={"C0":{"approved":True,"effective":"2026-01","price":"100.00"},"C1":{"approved":True,"effective":"2026-11","price":"120.00"},"DRAFT":{"approved":False,"effective":"2026-10","price":"140.00"}}
def evaluate(rows,context):
    good=[];bad=[];versions=context.get("parameters",{}).get("changes",CHANGES)
    for row in rows:
        rule=versions.get(row.get("change_id"))
        if not rule or not rule.get("approved"):bad.append(reject(row,"UNAPPROVED_CHANGE","变更尚未批准"));continue
        try: valid_period=len(row.get("period",""))==7 and datetime.strptime(row["period"],"%Y-%m") is not None
        except ValueError: valid_period=False
        if not valid_period or row["period"]<rule["effective"]:bad.append(reject(row,"CHANGE_NOT_EFFECTIVE","变更未生效"));continue
        try:
            price=number(rule["price"])
            if price<0:raise DomainError("BAD_PRICE","单价不能为负")
            good.append({**row,"unit_price":str(price),"approved_change":row["change_id"]})
        except DomainError as e:bad.append(reject(row,e.code,e.message))
    return {"rows":good,"quarantine":bad,"metrics":{"accepted":len(good),"versions":sorted(set(r["approved_change"] for r in good))}}
