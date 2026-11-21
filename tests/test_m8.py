import pytest
from datetime import date,timedelta
from app.errors import DomainError
from app.modules.m8_sections.rules import adjudicate,basis_digest
from app import store
def payload(**over):
    base={"sections":[{"section_id":"S1","start":"2026-03-01","end":"2026-06-30"},{"section_id":"S2","start":"2026-05-01","end":"2026-08-31"}],
          "shifts":[{"shift_id":"B01","date":"2026-04-10","qty":"10"},{"shift_id":"B02","date":"2026-05-12","qty":"20"},{"shift_id":"B03","date":"2026-07-01","qty":"30"}]}
    base.update(over);return base
def days(union):
    out=set()
    for start,end in union:
        day=date.fromisoformat(start)
        while day<date.fromisoformat(end): out.add(day);day+=timedelta(days=1)
    return out
def test_overlap_adjudicated_to_earliest_section():
    result=adjudicate(payload())
    shift=next(a for a in result["assignments"] if a["shift_id"]=="B02")
    assert shift["section_id"]=="S1" and shift["disputed"] is True
    assert shift["contenders"]==["S1","S2"] and shift["ruling"]=="先开工段优先"
def test_undisputed_shifts_settle_directly():
    result=adjudicate(payload())
    direct={a["shift_id"]:a for a in result["assignments"] if not a["disputed"]}
    assert direct["B01"]["section_id"]=="S1" and direct["B03"]["section_id"]=="S2"
    assert result["metrics"]["disputed"]==1 and result["metrics"]["measured"]==3
def test_signed_intervals_non_overlapping_and_cover_union():
    result=adjudicate(payload())
    owner={}
    for span in result["signed_intervals"]:
        for day in days([[span["start"],span["end"]]]):
            assert day not in owner,"每个日期只能对应一份正式计量依据"
            owner[day]=span["section_id"]
    assert set(owner)==days(result["union"])
    assert result["metrics"]["non_overlapping"] is True
def test_adjudicated_span_records_contenders():
    spans=adjudicate(payload())["signed_intervals"]
    span=next(s for s in spans if s["kind"]=="adjudicated")
    assert (span["section_id"],span["start"],span["end"])==("S1","2026-05-01","2026-06-30")
    assert span["contenders"]==["S1","S2"] and span["shifts"]==["B02"] and span["qty_total"]=="20"
def test_latest_start_policy_flips_winner():
    result=adjudicate(payload(overlap_policy="latest_start"))
    shift=next(a for a in result["assignments"] if a["shift_id"]=="B02")
    assert shift["section_id"]=="S2" and shift["ruling"]=="后开工段优先"
def test_uncovered_shift_quarantined_not_measured():
    result=adjudicate(payload(shifts=[{"shift_id":"B09","date":"2026-09-01","qty":"5"}]))
    assert result["assignments"]==[] and result["quarantine"][0]["reason"]=="NO_SECTION_COVER"
def test_identical_shift_retry_not_double_measured():
    shifts=[{"shift_id":"B01","date":"2026-04-10","qty":"10"},{"shift_id":"B01","date":"2026-04-10","qty":"10"}]
    result=adjudicate(payload(shifts=shifts))
    assert len(result["assignments"])==1 and result["metrics"]["duplicate"]==1
def test_conflicting_shift_quarantined_first_kept():
    shifts=[{"shift_id":"B01","date":"2026-04-10","qty":"10"},{"shift_id":"B01","date":"2026-04-10","qty":"99"}]
    result=adjudicate(payload(shifts=shifts))
    assert [a["qty"] for a in result["assignments"]]==["10"]
    assert result["quarantine"][0]["reason"]=="DUPLICATE_CONFLICT"
def test_per_section_trace_and_totals():
    result=adjudicate(payload())
    assert result["metrics"]["per_section"]=={"S1":{"shifts":2,"disputed":1,"qty_total":"30"},"S2":{"shifts":1,"disputed":0,"qty_total":"30"}}
    assert all(a["_sources"] for a in result["assignments"])
def test_bad_section_definitions_rejected():
    with pytest.raises(DomainError) as e: adjudicate(payload(sections=[{"section_id":"S1","start":"2026-06-30","end":"2026-03-01"}]))
    assert e.value.code=="BAD_INTERVAL"
    with pytest.raises(DomainError) as e: adjudicate(payload(sections=[{"section_id":"S1","start":"2026-03-01","end":"2026-05-01"},{"section_id":"S1","start":"2026-04-01","end":"2026-06-01"}]))
    assert e.value.code=="DUPLICATE_SECTION"
    with pytest.raises(DomainError) as e: adjudicate(payload(overlap_policy="first_come"))
    assert e.value.code=="BAD_POLICY"
def test_shift_requires_real_quantity():
    result=adjudicate(payload(shifts=[{"shift_id":"B01","date":"2026-04-10","qty":""}]))
    assert result["quarantine"][0]["reason"]=="EMPTY_VALUE"
def switch(client,body): return client.post("/api/sections/basis/switch",json=body)
def test_switch_activates_and_retry_idempotent(client):
    first=switch(client,payload());assert first.status_code==200
    basis_id=first.get_json()["basis_id"];assert basis_id==basis_digest(payload())
    again=switch(client,payload());assert again.get_json()["idempotent"] is True
    current=client.get("/api/sections/basis").get_json()
    assert current["active"]["basis_id"]==basis_id and len(current["history"])==1
    assert client.get("/api/sections/basis/"+basis_id).get_json()["result"]["metrics"]["measured"]==3
def test_switch_gap_keeps_old_basis(client):
    switch(client,payload())
    gappy={"sections":[{"section_id":"S2","start":"2026-07-01","end":"2026-08-31"}],"shifts":[]}
    r=switch(client,gappy);assert r.status_code==409 and r.get_json()["code"]=="SWITCH_GAP"
    current=client.get("/api/sections/basis").get_json()
    assert current["active"]["basis_id"]==basis_digest(payload()) and len(current["history"])==1
def test_superseded_basis_recoverable_per_section(client):
    old_id=switch(client,payload()).get_json()["basis_id"]
    newer=payload(sections=[{"section_id":"S1","start":"2026-03-01","end":"2026-06-30"},{"section_id":"S2","start":"2026-05-01","end":"2026-09-30"}])
    assert switch(client,newer).status_code==200
    history=client.get("/api/sections/basis").get_json()["history"]
    assert {h["basis_id"]:h["status"] for h in history}[old_id]=="superseded"
    trace=client.get(f"/api/sections/basis/{old_id}/sections/S1").get_json()
    assert trace["signed_intervals"] and trace["metrics"]["qty_total"]=="30"
    assert client.get(f"/api/sections/basis/{old_id}/sections/S9").status_code==404
def test_switch_conflict_same_id_different_content(client):
    from app.modules.m8_sections.rules import adjudicate
    one={"basis_id":"fixed","request":{"sections":[{"section_id":"S1","start":"2026-03-01","end":"2026-06-30"}]},"result":adjudicate({"sections":[{"section_id":"S1","start":"2026-03-01","end":"2026-06-30"}]})}
    two={"basis_id":"fixed","request":{"sections":[{"section_id":"S9","start":"2026-03-01","end":"2026-06-30"}]},"result":one["result"]}
    store.switch_basis("fixed",one)
    with pytest.raises(DomainError) as e: store.switch_basis("fixed",two)
    assert e.value.code=="BASIS_CONFLICT" and e.value.status==409
def test_adjudicate_endpoint_and_bad_body(client):
    r=client.post("/api/sections/adjudicate",json=payload())
    assert r.status_code==200 and r.get_json()["metrics"]["non_overlapping"] is True
    assert client.post("/api/sections/adjudicate",data="x").status_code==422
    assert client.get("/api/sections/basis").get_json()=={"active":None,"history":[]}
    assert client.get("/api/sections/basis/missing").status_code==404
