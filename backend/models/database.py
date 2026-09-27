import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    Date, DateTime, Text, Boolean, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from backend.config import SQLITE_DB_PATH

DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False)
    department = Column(String(80), nullable=False, index=True)
    role = Column(String(100), nullable=False)
    hire_date = Column(Date, nullable=False)
    manager_id = Column(Integer, nullable=True)
    manager_name = Column(String(100), nullable=True)
    total_annual_leave = Column(Integer, default=24)
    used_annual_leave = Column(Integer, default=0)
    sick_leave_balance = Column(Integer, default=12)
    casual_leave_balance = Column(Integer, default=8)
    status = Column(String(30), default="ACTIVE")  # ACTIVE, ON_LEAVE, RESIGNED
    location = Column(String(50), default="Bengaluru")

    leave_requests = relationship("LeaveRequest", back_populates="employee")

    @property
    def remaining_annual_leave(self) -> int:
        return max(0, (self.total_annual_leave or 24) - (self.used_annual_leave or 0))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "department": self.department,
            "role": self.role,
            "hire_date": str(self.hire_date),
            "manager_id": self.manager_id,
            "manager_name": self.manager_name,
            "total_annual_leave": self.total_annual_leave,
            "used_annual_leave": self.used_annual_leave,
            "remaining_annual_leave": self.remaining_annual_leave,
            "sick_leave_balance": self.sick_leave_balance,
            "casual_leave_balance": self.casual_leave_balance,
            "status": self.status,
            "location": self.location
        }


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    employee_name = Column(String(100), nullable=False)
    leave_type = Column(String(50), nullable=False)  # Annual, Sick, Casual, Sabbatical
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_requested = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(30), default="PENDING")  # PENDING, APPROVED, REJECTED
    approver_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    employee = relationship("Employee", back_populates="leave_requests")

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee_name,
            "leave_type": self.leave_type,
            "start_date": str(self.start_date),
            "end_date": str(self.end_date),
            "days_requested": self.days_requested,
            "reason": self.reason,
            "status": self.status,
            "approver_notes": self.approver_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    session_id = Column(String(64), nullable=True, index=True)
    user_request = Column(Text, nullable=True)
    tool_name = Column(String(100), nullable=False)
    tool_input = Column(Text, nullable=True)
    tool_output = Column(Text, nullable=True)
    status = Column(String(30), default="SUCCESS")  # SUCCESS, FAILED, PENDING_APPROVAL, REJECTED
    reasoning = Column(Text, nullable=True)
    requires_approval = Column(Boolean, default=False)
    approval_status = Column(String(30), default="NOT_REQUIRED")  # NOT_REQUIRED, PENDING, APPROVED, REJECTED

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "session_id": self.session_id,
            "user_request": self.user_request,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_output": self.tool_output,
            "status": self.status,
            "reasoning": self.reasoning,
            "requires_approval": self.requires_approval,
            "approval_status": self.approval_status
        }


class AgentMemory(Base):
    __tablename__ = "agent_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), default="global", index=True)
    memory_key = Column(String(100), nullable=False, index=True)
    memory_value = Column(Text, nullable=False)
    category = Column(String(50), default="general")  # preference, fact, context
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "memory_key": self.memory_key,
            "memory_value": self.memory_value,
            "category": self.category,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
