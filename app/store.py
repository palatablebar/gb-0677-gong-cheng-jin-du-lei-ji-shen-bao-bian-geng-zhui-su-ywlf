import sqlite3,json
from pathlib import Path
from datetime import datetime,timezone
from app.config import DATA_DIR
from app.errors import DomainError
def connect():
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(DATA_DIR/"records.db",timeout=20)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY,payload TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,decision TEXT NOT NULL DEFAULT '待复核')")
    db.execute("CREATE TABLE IF NOT EXISTS section_bases (basis_id TEXT PRIMARY KEY,payload TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL)")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_active_basis ON section_bases(status) WHERE status='active'")
    return db
def save(run_id,payload):
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO runs(id,payload) VALUES (?,?)",(run_id,json.dumps(payload,ensure_ascii=False)))
    return get(run_id)
def get(run_id):
    with connect() as db: row=db.execute("SELECT payload,version,decision FROM runs WHERE id=?",(run_id,)).fetchone()
    if not row: raise DomainError("NOT_FOUND","批次不存在",404)
    return {**json.loads(row[0]),"version":row[1],"decision":row[2]}
def latest():
    with connect() as db: row=db.execute("SELECT id FROM runs ORDER BY rowid DESC LIMIT 1").fetchone()
    return get(row[0]) if row else None
def history():
    with connect() as db: return [{"run_id":i,"version":v,"decision":d} for i,v,d in db.execute("SELECT id,version,decision FROM runs ORDER BY rowid DESC")]
def review(run_id,version,decision):
    if decision not in {"已复核","退回复核"}: raise DomainError("BAD_DECISION","复核状态无效")
    with connect() as db:
        cursor=db.execute("UPDATE runs SET version=version+1,decision=? WHERE id=? AND version=?",(decision,run_id,version))
        if cursor.rowcount!=1:
            if not db.execute("SELECT 1 FROM runs WHERE id=?",(run_id,)).fetchone(): raise DomainError("NOT_FOUND","批次不存在",404)
            raise DomainError("STALE_VERSION","版本已更新，请刷新",409)
    return get(run_id)
def switch_basis(basis_id,record):
    "计量依据整体切换：同一事务内完成覆盖校验、旧签证留存与新依据激活；任何失败回滚，旧签证不动"
    from app.modules.m8_sections.rules import covers
    db=connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        existing=db.execute("SELECT payload,status FROM section_bases WHERE basis_id=?",(basis_id,)).fetchone()
        if existing:
            db.rollback()
            stored=json.loads(existing[0])
            if stored["request"]==record["request"]: return {**stored,"status":existing[1],"idempotent":True}
            raise DomainError("BASIS_CONFLICT","同一依据标识对应不同内容",409)
        active=db.execute("SELECT payload FROM section_bases WHERE status='active'").fetchone()
        if active:
            old=json.loads(active[0])
            if not covers(record["result"]["union"],old["result"]["union"]): raise DomainError("SWITCH_GAP","新依据未覆盖已签认区间，已保留旧签证",409)
        created=datetime.now(timezone.utc).isoformat()
        db.execute("UPDATE section_bases SET status='superseded' WHERE status='active'")
        db.execute("INSERT INTO section_bases(basis_id,payload,status,created_at) VALUES (?,?,?,?)",(basis_id,json.dumps(record,ensure_ascii=False),"active",created))
        db.commit()
        return {**record,"status":"active","idempotent":False,"created_at":created}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
def active_basis():
    with connect() as db: row=db.execute("SELECT payload,status,created_at FROM section_bases WHERE status='active'").fetchone()
    return {**json.loads(row[0]),"status":row[1],"created_at":row[2]} if row else None
def get_basis(basis_id):
    with connect() as db: row=db.execute("SELECT payload,status,created_at FROM section_bases WHERE basis_id=?",(basis_id,)).fetchone()
    if not row: raise DomainError("NOT_FOUND","计量依据不存在",404)
    return {**json.loads(row[0]),"status":row[1],"created_at":row[2]}
def basis_history():
    with connect() as db: return [{"basis_id":i,"status":s,"created_at":c} for i,s,c in db.execute("SELECT basis_id,status,created_at FROM section_bases ORDER BY rowid DESC")]
