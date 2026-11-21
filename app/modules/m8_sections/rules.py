import hashlib,json
from datetime import date
from decimal import Decimal
from app.errors import DomainError
from app.values import number
from app.reasons import reject
ADJUDICATION_VERSION="sections-2026.11.21-r1"
POLICIES={"earliest_start":"先开工段优先","latest_start":"后开工段优先"}
def parse_day(value):
    try:
        text=str(value).strip();result=date.fromisoformat(text)
        if text!=result.isoformat(): raise ValueError()
        return result
    except (TypeError,ValueError): raise DomainError("INVALID_DATE","日期需要YYYY-MM-DD")
def normalize_sections(sections):
    if not isinstance(sections,list) or not sections: raise DomainError("BAD_SECTIONS","施工段需要非空列表")
    seen={}
    for raw in sections:
        if not isinstance(raw,dict): raise DomainError("BAD_SECTIONS","施工段需要对象")
        section_id=str(raw.get("section_id","")).strip()
        if not section_id: raise DomainError("EMPTY_VALUE","施工段编号为空")
        if section_id in seen: raise DomainError("DUPLICATE_SECTION","施工段编号重复")
        start=parse_day(raw.get("start"));end=parse_day(raw.get("end"))
        if not start<end: raise DomainError("BAD_INTERVAL","施工段起止无效，需满足start<end")
        seen[section_id]={"section_id":section_id,"start":start,"end":end}
    return list(seen.values())
def pick(covering,policy):
    edge=(min if policy=="earliest_start" else max)(s["start"] for s in covering)
    return min((s for s in covering if s["start"]==edge),key=lambda s:s["section_id"])
def partition(sections,policy):
    points=sorted({s["start"] for s in sections}|{s["end"] for s in sections})
    signed=[]
    for start,end in zip(points,points[1:]):
        covering=[s for s in sections if s["start"]<=start and s["end"]>=end]
        if not covering: continue
        owner=pick(covering,policy);kind="adjudicated" if len(covering)>1 else "undisputed"
        if signed and signed[-1]["section_id"]==owner["section_id"] and signed[-1]["kind"]==kind and signed[-1]["end"]==start:
            signed[-1]["end"]=end
        else: signed.append({"section_id":owner["section_id"],"start":start,"end":end,"kind":kind,"contenders":sorted(s["section_id"] for s in covering)})
    return signed
def union(intervals):
    merged=[]
    for start,end in sorted(intervals):
        if merged and start<=merged[-1][1]: merged[-1]=(merged[-1][0],max(merged[-1][1],end))
        else: merged.append((start,end))
    return merged
def covers(outer,inner):
    "outer与inner均为[start,end]文本区间列表；outer的并集须完整覆盖inner的每一段"
    available=union((parse_day(a),parse_day(b)) for a,b in outer)
    for a,b in inner:
        start,end=parse_day(a),parse_day(b)
        if not any(x<=start and end<=y for x,y in available): return False
    return True
def adjudicate(payload):
    if not isinstance(payload,dict): raise DomainError("BAD_BODY","请求需要对象")
    policy=payload.get("overlap_policy","earliest_start")
    if policy not in POLICIES: raise DomainError("BAD_POLICY","交叠裁决策略无效")
    sections=normalize_sections(payload.get("sections"))
    shifts=payload.get("shifts",[])
    if not isinstance(shifts,list) or any(not isinstance(s,dict) for s in shifts): raise DomainError("BAD_SHIFTS","班次需要对象列表")
    signed=partition(sections,policy)
    for left,right in zip(signed,signed[1:]):
        if left["end"]>right["start"]: raise DomainError("INTERVAL_OVERLAP","签认区间存在交叠")
    good=[];bad=[];seen={};duplicate=0
    for index,raw in enumerate(shifts,1):
        row={**raw,"_line":index,"_sources":[index]}
        shift_id=str(row.get("shift_id","")).strip()
        if not shift_id: bad.append(reject(row,"EMPTY_VALUE","班次编号为空"));continue
        if shift_id in seen:
            if row.get("date")==seen[shift_id].get("date") and str(row.get("qty",""))==str(seen[shift_id].get("qty","")): duplicate+=1
            else: bad.append(reject(row,"DUPLICATE_CONFLICT","同班次不同值"))
            continue
        try:
            day=parse_day(row.get("date"));qty=number(row.get("qty",""))
        except DomainError as e: bad.append(reject(row,e.code,e.message));continue
        contenders=[s for s in sections if s["start"]<=day<s["end"]]
        if not contenders: bad.append(reject(row,"NO_SECTION_COVER","班次日期不在任何施工段区间内"));continue
        owner=pick(contenders,policy)
        hits=[s for s in signed if s["section_id"]==owner["section_id"] and s["start"]<=day<s["end"]]
        if len(hits)!=1: raise DomainError("INTERVAL_OVERLAP","班次未唯一落入签认区间")
        seen[shift_id]=row
        good.append({**row,"shift_id":shift_id,"date":day.isoformat(),"qty":str(qty),"section_id":owner["section_id"],"contenders":sorted(s["section_id"] for s in contenders),"disputed":len(contenders)>1,"ruling":POLICIES[policy] if len(contenders)>1 else "唯一覆盖"})
    intervals=[]
    for span in signed:
        measured=[g for g in good if g["section_id"]==span["section_id"] and span["start"].isoformat()<=g["date"]<span["end"].isoformat()]
        intervals.append({**span,"start":span["start"].isoformat(),"end":span["end"].isoformat(),"shifts":[g["shift_id"] for g in measured],"qty_total":str(sum((number(g["qty"]) for g in measured),Decimal(0)))})
    per={}
    for g in good:
        slot=per.setdefault(g["section_id"],{"shifts":0,"disputed":0,"qty_total":"0"})
        slot["shifts"]+=1;slot["disputed"]+=g["disputed"];slot["qty_total"]=str(number(slot["qty_total"])+number(g["qty"]))
    metrics={"sections":len(sections),"shifts":len(shifts),"measured":len(good),"disputed":sum(g["disputed"] for g in good),"quarantined":len(bad),"duplicate":duplicate,"signed_intervals":len(intervals),"adjudicated_spans":sum(s["kind"]=="adjudicated" for s in intervals),"non_overlapping":True,"per_section":per}
    return {"policy":policy,"ruling":POLICIES[policy],"signed_intervals":intervals,"assignments":good,"quarantine":bad,"union":[[a.isoformat(),b.isoformat()] for a,b in union((s["start"],s["end"]) for s in signed)],"metrics":metrics}
def basis_digest(payload):
    canonical=json.dumps(payload,sort_keys=True,ensure_ascii=False)
    return hashlib.sha256((canonical+ADJUDICATION_VERSION).encode()).hexdigest()[:20]
