from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base

class Employee(Base):
    __tablename__ = "employees"
    employee_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # EMPLOYEE / MANAGER / ADMIN
    manager_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=True)

    manager = relationship("Employee", remote_side=[employee_id], backref="subordinates")

class LeaveType(Base):
    __tablename__ = "leave_types"
    leave_type_id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False)  # CL/SL/PL
    name = Column(String(60), nullable=False)
    max_per_year = Column(Integer, nullable=False)

class LeaveBalance(Base):
    __tablename__ = "leave_balances"
    balance_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.leave_type_id"), nullable=False)
    year = Column(Integer, nullable=False)
    total_allocated = Column(Integer, nullable=False)
    used = Column(Integer, nullable=False, default=0)
    remaining = Column(Integer, nullable=False)

class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    request_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.leave_type_id"), nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_count = Column(Integer, nullable=False)

    reason = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="PENDING")

    applied_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)
    decided_by = Column(Integer, ForeignKey("employees.employee_id"), nullable=True)
    manager_comment = Column(Text, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    log_id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)
    action = Column(String(50), nullable=False)
    target_type = Column(String(50), nullable=True)
    target_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    details = Column(Text, nullable=True)

class AgentMemory(Base):
    __tablename__ = "agent_memory"

    user_id = Column(Integer, primary_key=True)
    intent = Column(String)
    stage = Column(String)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    duration_days = Column(Integer, nullable=True)
    reason = Column(String, nullable=True)
    leave_type = Column(String, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow)