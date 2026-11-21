from app.values import number
from app.reasons import reject
from app.errors import DomainError
ITEMS={"钢筋":"001","001":"001","混凝土":"002","002":"002"}
def evaluate(rows,context):
    good=[];bad=[]
    for row in rows:
        try:
            item=ITEMS.get(row.get("item"))
            if item is None:raise DomainError("UNKNOWN_ITEM","清单项未登记")
            current=number(row["cumulative_qty"]);previous=number(row["previous_qty"]);reported=number(row["reported"])
            if current<0 or previous<0:raise DomainError("NEGATIVE_CUMULATIVE","累计量不能为负")
            good.append({**row,"item":item,"cumulative_qty":str(current),"previous_qty":str(previous),"reported":str(reported),"unit":"t" if item=="001" else "m³"})
        except (DomainError,KeyError) as e:bad.append(reject(row,getattr(e,"code","MISSING_FIELD"),str(e)))
    return {"rows":good,"quarantine":bad,"metrics":{"accepted":len(good),"items":len(set(r["item"] for r in good))}}
