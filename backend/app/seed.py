from sqlalchemy.orm import Session
from .db import Base, engine
from .models import Employee, LeaveType
from .auth import hash_password

def init_db():
    Base.metadata.create_all(bind=engine)

def seed(db: Session):
    if db.query(LeaveType).count() == 0:
        db.add_all([
            LeaveType(code="CL", name="Casual Leave", max_per_year=12),
            LeaveType(code="SL", name="Sick Leave", max_per_year=12),
            LeaveType(code="ML", name="Medical Leave", max_per_year=15),
        ])
        db.commit()

    admin = db.query(Employee).filter(Employee.email == "admin@company.com").first()
    if not admin:
        admin = Employee(
            name="System Admin",
            email="admin@company.com",
            password_hash=hash_password("Admin@123"),
            role="ADMIN",
            manager_id=None
        )
        db.add(admin)
        db.commit()