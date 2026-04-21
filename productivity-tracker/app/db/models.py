from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

WORK_ITEM_STATUSES = ("Not Started", "In Progress", "Blocked", "On Hold", "Done")
PROJECT_STATUSES = ("Planned", "Active", "Blocked", "On Hold", "Completed")
PRIORITY_LEVELS = ("Low", "Medium", "High", "Critical")
EMPLOYMENT_STATUSES = ("Active", "On Leave", "Inactive")
ACTIVITY_TYPES = ("Planning", "Execution", "Analysis", "Meeting", "Support", "Review")


class Division(TimestampMixin, Base):
    __tablename__ = "divisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    employees: Mapped[list["Employee"]] = relationship(back_populates="division")
    projects: Mapped[list["Project"]] = relationship(back_populates="owner_division")
    work_items: Mapped[list["WorkItem"]] = relationship(back_populates="division")


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    job_title: Mapped[str] = mapped_column(String(120), nullable=False)
    division_id: Mapped[int] = mapped_column(ForeignKey("divisions.id"), nullable=False)
    manager_name: Mapped[str | None] = mapped_column(String(120))
    employment_status: Mapped[str] = mapped_column(String(32), default="Active", nullable=False)
    joined_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    division: Mapped["Division"] = relationship(back_populates="employees")
    owned_work_items: Mapped[list["WorkItem"]] = relationship(back_populates="owner_employee")
    assignments: Mapped[list["WorkItemAssignee"]] = relationship(back_populates="employee")
    activity_logs: Mapped[list["ActivityLog"]] = relationship(back_populates="employee")


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner_division_id: Mapped[int] = mapped_column(ForeignKey("divisions.id"), nullable=False)
    priority: Mapped[str] = mapped_column(String(32), default="Medium", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="Planned", nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    target_end_date: Mapped[date | None] = mapped_column(Date)

    owner_division: Mapped["Division"] = relationship(back_populates="projects")
    work_items: Mapped[list["WorkItem"]] = relationship(back_populates="project")
    activity_logs: Mapped[list["ActivityLog"]] = relationship(back_populates="project")


class WorkItem(TimestampMixin, Base):
    __tablename__ = "work_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    division_id: Mapped[int] = mapped_column(ForeignKey("divisions.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(80))
    priority: Mapped[str] = mapped_column(String(32), default="Medium", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="Not Started", nullable=False)
    owner_employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    planned_start_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    completed_date: Mapped[date | None] = mapped_column(Date)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    division: Mapped["Division"] = relationship(back_populates="work_items")
    project: Mapped["Project | None"] = relationship(back_populates="work_items")
    owner_employee: Mapped["Employee | None"] = relationship(back_populates="owned_work_items")
    assignees: Mapped[list["WorkItemAssignee"]] = relationship(
        back_populates="work_item",
        cascade="all, delete-orphan",
    )
    activity_logs: Mapped[list["ActivityLog"]] = relationship(back_populates="work_item")


class WorkItemAssignee(Base):
    __tablename__ = "work_item_assignees"
    __table_args__ = (UniqueConstraint("work_item_id", "employee_id", name="uq_work_item_employee"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_item_id: Mapped[int] = mapped_column(ForeignKey("work_items.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    assignment_role: Mapped[str | None] = mapped_column(String(80))
    allocation_pct: Mapped[int | None] = mapped_column(Integer)

    work_item: Mapped["WorkItem"] = relationship(back_populates="assignees")
    employee: Mapped["Employee"] = relationship(back_populates="assignments")


class ActivityLog(TimestampMixin, Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    work_item_id: Mapped[int | None] = mapped_column(ForeignKey("work_items.id"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    activity_type: Mapped[str] = mapped_column(String(32), default="Execution", nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    hours_spent: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    status: Mapped[str] = mapped_column(String(32), default="In Progress", nullable=False)
    progress_pct: Mapped[int | None] = mapped_column(Integer)
    blocker_note: Mapped[str | None] = mapped_column(Text)
    next_action: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(120))

    employee: Mapped["Employee"] = relationship(back_populates="activity_logs")
    work_item: Mapped["WorkItem | None"] = relationship(back_populates="activity_logs")
    project: Mapped["Project | None"] = relationship(back_populates="activity_logs")


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(32))
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_by: Mapped[str | None] = mapped_column(String(120))
    changed_at: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
