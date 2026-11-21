from flask import Blueprint,request,jsonify
from app.errors import DomainError
from app import store
from app.modules.m8_sections.rules import adjudicate,basis_digest
bp=Blueprint("sections",__name__)
def body():
    payload=request.get_json(silent=True)
    if not isinstance(payload,dict): raise DomainError("BAD_BODY","请求需要对象")
    return payload
@bp.post("/api/sections/adjudicate")
def preview():
    return jsonify(adjudicate(body()))
@bp.post("/api/sections/basis/switch")
def switch():
    payload=body()
    record={"basis_id":basis_digest(payload),"request":payload,"result":adjudicate(payload)}
    return jsonify(store.switch_basis(record["basis_id"],record))
@bp.get("/api/sections/basis")
def current():
    return jsonify({"active":store.active_basis(),"history":store.basis_history()})
@bp.get("/api/sections/basis/<basis_id>")
def detail(basis_id):
    return jsonify(store.get_basis(basis_id))
@bp.get("/api/sections/basis/<basis_id>/sections/<section_id>")
def section_trace(basis_id,section_id):
    basis=store.get_basis(basis_id);result=basis["result"]
    spans=[s for s in result["signed_intervals"] if s["section_id"]==section_id]
    assignments=[a for a in result["assignments"] if a["section_id"]==section_id]
    if not spans and not assignments: raise DomainError("NOT_FOUND","施工段不在该依据中",404)
    return jsonify({"basis_id":basis_id,"section_id":section_id,"signed_intervals":spans,"assignments":assignments,"metrics":result["metrics"]["per_section"].get(section_id,{})})
