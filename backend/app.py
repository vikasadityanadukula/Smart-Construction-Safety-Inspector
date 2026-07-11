from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from database import engine, SessionLocal
from models import Base, Violation
from schemas import ViolationCreate
from report import generate_report


app = FastAPI()

# ---------------- DATABASE ----------------

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- HOME ----------------

@app.get("/")
def home():
    return {
        "project": "SafeSite AI",
        "status": "Backend Running Successfully"
    }


# ---------------- ADD VIOLATION ----------------

@app.post("/violations")
def create_violation(data: ViolationCreate, db: Session = Depends(get_db)):

    violation = Violation(
        worker_id=data.worker_id,
        helmet=data.helmet,
        vest=data.vest,
        zone=data.zone,
        time=data.time
    )

    db.add(violation)
    db.commit()
    db.refresh(violation)

    return {
        "message": "Violation Saved Successfully"
    }


# ---------------- DASHBOARD ----------------

@app.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):

    total_records = db.query(Violation).count()

    helmet_violations = db.query(Violation).filter(
        Violation.helmet == False
    ).count()

    vest_violations = db.query(Violation).filter(
        Violation.vest == False
    ).count()

    danger_zone_entries = db.query(Violation).filter(
        Violation.zone == "Danger"
    ).count()

    violations = []

    all_records = db.query(Violation).all()

    for record in all_records:

        if not record.helmet:
            violation_type = "Helmet Missing"

        elif not record.vest:
            violation_type = "Vest Missing"

        elif record.zone == "Danger":
            violation_type = "Danger Zone"

        else:
            violation_type = "Safe"

        violations.append({
            "worker_id": record.worker_id,
            "type": violation_type,
            "time": record.time
        })

    return {
        "total_records": total_records,
        "helmet_violations": helmet_violations,
        "vest_violations": vest_violations,
        "danger_zone_entries": danger_zone_entries,
        "violations": violations
    }


# ---------------- GET ALL VIOLATIONS ----------------

@app.get("/violations")
def get_violations(db: Session = Depends(get_db)):

    violations = db.query(Violation).all()

    data = []

    for v in violations:

        data.append({
            "worker_id": v.worker_id,
            "helmet": v.helmet,
            "vest": v.vest,
            "zone": v.zone,
            "time": v.time
        })

    return data


# ---------------- REPORT ----------------

@app.get("/report")
def report(db: Session = Depends(get_db)):

    return {
        "report": generate_report(db)
    }


# ---------------- CLEAR DATABASE ----------------

@app.delete("/clear")
def clear_database(db: Session = Depends(get_db)):

    db.query(Violation).delete()

    db.commit()

    return {
        "message": "Database Cleared Successfully"
    }