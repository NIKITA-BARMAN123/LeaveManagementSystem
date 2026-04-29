from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime

from .db import get_db, SessionLocal
from .models import Employee, LeaveType, LeaveBalance, LeaveRequest, AuditLog
from .auth import verify_password, create_access_token, require_role, hash_password
from .seed import init_db, seed
from .email_service import send_email

from .agent import (
    detect_intent,
    extract_leave_type,
    extract_dates,
    extract_reason,
    extract_duration_days,
    AgentState,
    
    update_state,
    decide_next_step,
    load_state_from_db,   
    save_state_to_db,     
    reset_state 
)
from .rules import validate_dates, compute_days

app = FastAPI(title="AI Leave Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()

# ---------- MANUAL UI AUDIT ----------
@app.post("/audit/log")
def audit_log_action(
    action: str,
    target_type: str = "UI",
    target_id: int | None = None,
    details: str | None = None,
    db: Session = Depends(get_db),
    user: Employee = Depends(require_role("ADMIN", "MANAGER", "EMPLOYEE"))
):
    db.add(AuditLog(
        actor_id=user.employee_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details
    ))
    db.commit()

    return {"message": "Audit logged"}
# ---------- AUTH ----------
@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    email = form_data.username
    password = form_data.password

    user = db.query(Employee).filter(Employee.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.employee_id), "role": user.role})

    db.add(AuditLog(
        actor_id=user.employee_id,
        action="LOGIN",
        target_type="Auth",
        details=f"User {user.name} ({user.email}) logged in"
    ))
    db.commit()

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "name": user.name,
        "user_id": user.employee_id
    }


@app.post("/auth/logout")
def logout(
    db: Session = Depends(get_db),
    user: Employee = Depends(require_role("ADMIN", "MANAGER", "EMPLOYEE"))
):
    db.add(AuditLog(
        actor_id=user.employee_id,
        action="LOGOUT",
        target_type="Auth",
        details=f"User {user.name} ({user.email}) logged out"
    ))
    db.commit()

    return {"message": "Logged out"}


# ---------- ADMIN ----------
@app.get("/admin/audit")
def admin_audit(
    db: Session = Depends(get_db),
    admin: Employee = Depends(require_role("ADMIN"))
):
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(200)
        .all()
    )

    return [{
        "log_id": log.log_id,
        "actor_id": log.actor_id,
        "action": log.action,
        "target_type": log.target_type,
        "target_id": log.target_id,
        "timestamp": log.timestamp.isoformat() + "Z",
        "details": log.details
    } for log in logs]
@app.post("/admin/create-user")
def admin_create_user(
    name: str,
    email: str,
    password: str,
    role: str,
    manager_id: int | None = None,
    db: Session = Depends(get_db),
    admin: Employee = Depends(require_role("ADMIN"))
):
    if role not in ["EMPLOYEE", "MANAGER", "ADMIN"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    if db.query(Employee).filter(Employee.email == email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    user = Employee(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        manager_id=manager_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    year = datetime.utcnow().year
    leave_types = db.query(LeaveType).all()
    for lt in leave_types:
        db.add(LeaveBalance(
            employee_id=user.employee_id,
            leave_type_id=lt.leave_type_id,
            year=year,
            total_allocated=lt.max_per_year,
            used=0,
            remaining=lt.max_per_year
        ))

    db.add(AuditLog(
        actor_id=admin.employee_id,
        action="CREATE_USER",
        target_type="Employee",
        target_id=user.employee_id,
        details=(
            f"{admin.name} ({admin.email}) created user: "
            f"name={user.name}, email={user.email}, role={user.role}, manager_id={user.manager_id}"
        )
    ))
    db.commit()

    return {
        "message": "User created",
        "employee_id": user.employee_id,
        "email": user.email,
        "role": user.role
    }


@app.get("/admin/requests")
def admin_requests(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    admin: Employee = Depends(require_role("ADMIN"))
):
    q = db.query(LeaveRequest)
    if status_filter:
        q = q.filter(LeaveRequest.status == status_filter.upper())

    reqs = q.order_by(LeaveRequest.applied_at.desc()).limit(200).all()

    return [{
        "request_id": r.request_id,
        "employee_id": r.employee_id,
        "leave_type_id": r.leave_type_id,
        "start": str(r.start_date),
        "end": str(r.end_date),
        "days": r.days_count,
        "reason": r.reason,
        "status": r.status,
        "applied_at": r.applied_at.isoformat(),
        "decided_at": r.decided_at.isoformat() if r.decided_at else None,
        "decided_by": r.decided_by
    } for r in reqs]


@app.post("/admin/leave-types")
def admin_create_leave_type(
    code: str,
    name: str,
    max_per_year: int,
    db: Session = Depends(get_db),
    admin: Employee = Depends(require_role("ADMIN"))
):
    code = code.upper()
    if db.query(LeaveType).filter(LeaveType.code == code).first():
        raise HTTPException(status_code=400, detail="Leave type already exists")

    lt = LeaveType(code=code, name=name, max_per_year=max_per_year)
    db.add(lt)
    db.flush()

    db.add(AuditLog(
        actor_id=admin.employee_id,
        action="CREATE_LEAVE_TYPE",
        target_type="LeaveType",
        target_id=lt.leave_type_id,
        details=(
            f"{admin.name} ({admin.email}) created leave type: "
            f"code={lt.code}, name={lt.name}, max_per_year={lt.max_per_year}"
        )
    ))
    db.commit()

    return {"message": "Leave type created", "code": code}


# ---------- EMPLOYEE CHAT ----------

@app.post("/chat")
def chat(
    message: str,
    db: Session = Depends(get_db),
    user: Employee = Depends(require_role("EMPLOYEE", "MANAGER", "ADMIN"))
):
    state = load_state_from_db(db, user.employee_id)

    state = update_state(state, message)
    decision = decide_next_step(state, message)

    # Restricting chat to APPLY_LEAVE only :))
    if state.intent and state.intent != "APPLY_LEAVE":
        reset_state(db, user.employee_id)  

        return {
            "intent": state.intent,
            "reply": "Please use this section only to apply for leave.",
            "data": None
        }

    # 1. Ask follow-up question
    if decision["action"] == "ASK":
        save_state_to_db(db, user.employee_id, state)
        return {
            "intent": state.intent or "UNKNOWN",
            "reply": decision["message"],
            "data": None
        }

    # 2. Check balance
    if decision["action"] == "CHECK_BALANCE":
        year = datetime.utcnow().year
        rows = (
            db.query(LeaveBalance, LeaveType)
            .join(LeaveType, LeaveType.leave_type_id == LeaveBalance.leave_type_id)
            .filter(
                LeaveBalance.employee_id == user.employee_id,
                LeaveBalance.year == year
            )
            .all()
        )

        db.add(AuditLog(
            actor_id=user.employee_id,
            action="CHECK_BALANCE",
            target_type="LeaveBalance",
            details=f"{user.name} ({user.email}) checked leave balance for year={year}"
        ))
        db.commit()

        reset_state(db, user.employee_id)

        return {
            "intent": "CHECK_BALANCE",
            "reply": "Here is your leave balance.",
            "data": [
                {
                    "type": lt.code,
                    "remaining": b.remaining,
                    "used": b.used,
                    "total": b.total_allocated
                }
                for b, lt in rows
            ]
        }

    # 3. View history
    if decision["action"] == "VIEW_HISTORY":
        reqs = (
            db.query(LeaveRequest)
            .filter(LeaveRequest.employee_id == user.employee_id)
            .order_by(LeaveRequest.applied_at.desc())
            .limit(20)
            .all()
        )

        db.add(AuditLog(
            actor_id=user.employee_id,
            action="VIEW_HISTORY",
            target_type="LeaveRequest",
            details=f"{user.name} ({user.email}) viewed recent leave request history"
        ))
        db.commit()

        reset_state(db, user.employee_id)

        return {
            "intent": "VIEW_HISTORY",
            "reply": "Here is your recent leave history.",
            "data": [{
                "request_id": r.request_id,
                "start": str(r.start_date),
                "end": str(r.end_date),
                "days": r.days_count,
                "status": r.status,
                "applied_at": r.applied_at.isoformat()
            } for r in reqs]
        }

    # 4. Final apply leave
    if decision["action"] == "APPLY_LEAVE":
        lt_code = state.leave_type
        start = state.start_date
        end = state.end_date
        reason = state.reason
        duration_days = state.duration_days

        if not start or not end:
            save_state_to_db(db, user.employee_id, state)
            return {
                "intent": "APPLY_LEAVE",
                "reply": "Please provide complete leave dates.",
                "data": None
            }

        err = validate_dates(start, end)
        if err:
            reset_state(db, user.employee_id)
            raise HTTPException(status_code=400, detail=err)

        days = compute_days(start, end)

        if duration_days and duration_days != days:
            reset_state(db, user.employee_id)
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Duration mismatch: extracted duration={duration_days} day(s), "
                    f"but calculated from dates={days} day(s)."
                )
            )

        lt = db.query(LeaveType).filter(LeaveType.code == lt_code).first()
        if not lt:
            reset_state(db, user.employee_id)
            raise HTTPException(status_code=400, detail="Invalid leave type")

        year = datetime.utcnow().year
        bal = (
            db.query(LeaveBalance)
            .filter(
                LeaveBalance.employee_id == user.employee_id,
                LeaveBalance.leave_type_id == lt.leave_type_id,
                LeaveBalance.year == year
            )
            .first()
        )
        if not bal:
            reset_state(db, user.employee_id)
            raise HTTPException(status_code=400, detail="Leave balance not initialized")

        if bal.remaining < days:
            reset_state(db, user.employee_id)
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient {lt_code} balance. Remaining={bal.remaining}, Requested={days}"
            )

        overlap = (
            db.query(LeaveRequest)
            .filter(
                LeaveRequest.employee_id == user.employee_id,
                LeaveRequest.status.in_(["PENDING", "APPROVED"]),
                LeaveRequest.start_date <= end,
                LeaveRequest.end_date >= start
            )
            .first()
        )
        if overlap:
            reset_state(db, user.employee_id)
            raise HTTPException(status_code=400, detail="Overlapping leave request already exists.")

        req = LeaveRequest(
            employee_id=user.employee_id,
            leave_type_id=lt.leave_type_id,
            start_date=start,
            end_date=end,
            days_count=days,
            reason=reason,
            status="PENDING"
        )
        db.add(req)
        db.commit()
        db.refresh(req)

        db.add(AuditLog(
            actor_id=user.employee_id,
            action="APPLY_LEAVE",
            target_type="LeaveRequest",
            target_id=req.request_id,
            details=(
                f"Leave applied by {user.name} ({user.email}) "
                f"from {start} to {end}, days={days}, "
                f"extracted_duration={duration_days}, reason={reason}"
            )
        ))
        db.commit()

        reset_state(db, user.employee_id)

        return {
            "intent": "APPLY_LEAVE",
            "reply": (
                f"Your leave request has been submitted successfully. "
                f"It has been forwarded to your manager for approval. "
                f"Leave details: {lt_code}, {start} to {end}, {days} day(s). "
                f"Current status: PENDING."
            ),
            "data": {
                "request_id": req.request_id,
                "status": req.status,
                "duration_extracted": duration_days
            }
        }
        

    save_state_to_db(db, user.employee_id, state)
    return {
        "intent": state.intent or "UNKNOWN",
        "reply": "Try: apply leave / balance / history",
        "data": None
    }

# ---------- EMPLOYEE ENDPOINTS ----------
@app.get("/employee/balance")
def employee_balance(
    db: Session = Depends(get_db),
    user: Employee = Depends(require_role("EMPLOYEE", "MANAGER", "ADMIN"))
):
    year = datetime.utcnow().year
    rows = (
        db.query(LeaveBalance, LeaveType)
        .join(LeaveType, LeaveType.leave_type_id == LeaveBalance.leave_type_id)
        .filter(
            LeaveBalance.employee_id == user.employee_id,
            LeaveBalance.year == year
        )
        .all()
    )

    return [{
        "type": lt.code,
        "remaining": b.remaining,
        "used": b.used,
        "total": b.total_allocated
    } for b, lt in rows]


@app.get("/employee/history")
def employee_history(
    db: Session = Depends(get_db),
    user: Employee = Depends(require_role("EMPLOYEE", "MANAGER", "ADMIN"))
):
    reqs = (
        db.query(LeaveRequest)
        .filter(LeaveRequest.employee_id == user.employee_id)
        .order_by(LeaveRequest.applied_at.desc())
        .limit(50)
        .all()
    )
    
    return [{
        "request_id": r.request_id,
        "start": str(r.start_date),
        "end": str(r.end_date),
        "days": r.days_count,
        "status": r.status,
        "applied_at": r.applied_at.isoformat(),
        "decided_at": r.decided_at.isoformat() if r.decided_at else None,
        "decided_by": r.decided_by,
        "comment": r.manager_comment
    } for r in reqs]


# ---------- MANAGER ----------
@app.get("/manager/requests")
def manager_requests(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    manager: Employee = Depends(require_role("MANAGER", "ADMIN"))
):
    q = db.query(LeaveRequest)

    if manager.role == "MANAGER":
        team_ids = [
            e.employee_id
            for e in db.query(Employee).filter(Employee.manager_id == manager.employee_id).all()
        ]
        q = q.filter(LeaveRequest.employee_id.in_(team_ids))

    if status_filter:
        q = q.filter(LeaveRequest.status == status_filter.upper())

    reqs = q.order_by(LeaveRequest.applied_at.desc()).limit(100).all()

    result = []
    for r in reqs:
        emp = db.query(Employee).filter(Employee.employee_id == r.employee_id).first()
        result.append({
            "request_id": r.request_id,
            "employee_name": emp.name if emp else None,
            "start_date": str(r.start_date),
            "end_date": str(r.end_date),
            "days": r.days_count,
            "status": r.status,
            "reason": r.reason,
            "comment": r.manager_comment,
            "applied_at": r.applied_at.isoformat()
        })
  
    return result


@app.post("/manager/decide")
def manager_decide(
    request_id: int,
    action: str,
    comment: str | None = None,
    db: Session = Depends(get_db),
    manager: Employee = Depends(require_role("MANAGER", "ADMIN"))
):
    req = db.query(LeaveRequest).filter(LeaveRequest.request_id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if manager.role == "MANAGER":
        emp = db.query(Employee).filter(Employee.employee_id == req.employee_id).first()
        if not emp or emp.manager_id != manager.employee_id:
            raise HTTPException(status_code=403, detail="Not authorized for this request")

    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail="Only PENDING requests can be decided")

    action_u = action.upper()
    if action_u not in ["APPROVE", "REJECT"]:
        raise HTTPException(status_code=400, detail="Invalid action")

    req.status = "APPROVED" if action_u == "APPROVE" else "REJECTED"
    req.decided_by = manager.employee_id
    req.decided_at = datetime.utcnow()
    req.manager_comment = comment

    if req.status == "APPROVED":
        year = datetime.utcnow().year
        bal = (
            db.query(LeaveBalance)
            .filter(
                LeaveBalance.employee_id == req.employee_id,
                LeaveBalance.leave_type_id == req.leave_type_id,
                LeaveBalance.year == year
            )
            .first()
        )
        if not bal or bal.remaining < req.days_count:
            raise HTTPException(status_code=400, detail="Balance issue while approving")

        bal.used += req.days_count
        bal.remaining -= req.days_count

    employee = db.query(Employee).filter(Employee.employee_id == req.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    db.add(AuditLog(
        actor_id=manager.employee_id,
        action=f"{action_u}_LEAVE",
        target_type="LeaveRequest",
        target_id=req.request_id,
        details=(
            f"Request {req.request_id} for employee {req.employee_id} was "
            f"{req.status} by {manager.name} ({manager.email}). "
            f"Comment={comment if comment else 'No comment'}"
        )
    ))
    db.commit()

    try:
        if req.status == "APPROVED":
            subject = "Leave Request Approved"
            body = f"""
Hello {employee.name},

Your leave request has been approved by your manager.

Leave details:
Start Date: {req.start_date}
End Date: {req.end_date}
Number of Days: {req.days_count}
Status: {req.status}
Manager Comment: {comment if comment else "No comment"}

Regards,
AI Leave Management System
"""
        else:
            subject = "Leave Request Rejected"
            body = f"""
Hello {employee.name},

Your leave request has been rejected by your manager.

Leave details:
Start Date: {req.start_date}
End Date: {req.end_date}
Number of Days: {req.days_count}
Status: {req.status}
Manager Comment: {comment if comment else "No comment"}

Regards,
AI Leave Management System
"""

        send_email(
            to_email=employee.email,
            subject=subject,
            body=body
        )

    except Exception as e:
        print("Email sending failed:", str(e))

    return {
        "message": f"Request {req.status}",
        "request_id": req.request_id,
        "status": req.status
    }
# decide_next_step