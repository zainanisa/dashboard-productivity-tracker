from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import ActivityLog, Division, Employee, Project, WorkItem, WorkItemAssignee


def divisions_dataframe(session: Session) -> pd.DataFrame:
    divisions = session.scalars(
        select(Division)
        .options(selectinload(Division.employees), selectinload(Division.projects), selectinload(Division.work_items))
        .order_by(Division.name)
    ).all()

    rows: list[dict[str, object]] = []
    for division in divisions:
        active_employees = [
            employee
            for employee in division.employees
            if employee.is_active and employee.employment_status == "Active"
        ]
        rows.append(
            {
                "id": division.id,
                "code": division.code,
                "division_name": division.name,
                "description": division.description or "",
                "is_active": division.is_active,
                "active_employees": len(active_employees),
                "project_count": len(division.projects),
                "open_work_items": sum(1 for item in division.work_items if item.status != "Done"),
                "blocked_work_items": sum(1 for item in division.work_items if item.status == "Blocked"),
                "avg_progress_pct": round(
                    sum(item.progress_pct for item in division.work_items) / len(division.work_items), 1
                )
                if division.work_items
                else 0,
            }
        )

    return pd.DataFrame(rows)


def employees_dataframe(session: Session) -> pd.DataFrame:
    employees = session.scalars(
        select(Employee)
        .options(
            selectinload(Employee.division),
            selectinload(Employee.assignments).selectinload(WorkItemAssignee.work_item),
            selectinload(Employee.activity_logs),
        )
        .order_by(Employee.full_name)
    ).all()

    cutoff = date.today() - timedelta(days=6)
    rows: list[dict[str, object]] = []
    for employee in employees:
        active_assignment_ids = {
            assignment.work_item_id
            for assignment in employee.assignments
            if assignment.work_item and assignment.work_item.status != "Done"
        }
        rows.append(
            {
                "id": employee.id,
                "employee_code": employee.employee_code,
                "full_name": employee.full_name,
                "email": employee.email or "",
                "job_title": employee.job_title,
                "division_id": employee.division_id,
                "division_name": employee.division.name if employee.division else "",
                "manager_name": employee.manager_name or "",
                "employment_status": employee.employment_status,
                "joined_date": employee.joined_date,
                "is_active": employee.is_active,
                "active_assignments": len(active_assignment_ids),
                "activities_last_7d": sum(
                    1 for activity in employee.activity_logs if activity.activity_date >= cutoff
                ),
                "total_activity_logs": len(employee.activity_logs),
            }
        )

    return pd.DataFrame(rows)


def projects_dataframe(session: Session) -> pd.DataFrame:
    projects = session.scalars(
        select(Project)
        .options(selectinload(Project.owner_division), selectinload(Project.work_items))
        .order_by(Project.name)
    ).all()

    rows: list[dict[str, object]] = []
    for project in projects:
        total_items = len(project.work_items)
        done_items = sum(1 for item in project.work_items if item.status == "Done")
        rows.append(
            {
                "id": project.id,
                "project_code": project.project_code,
                "project_name": project.name,
                "owner_division_id": project.owner_division_id,
                "owner_division": project.owner_division.name if project.owner_division else "",
                "priority": project.priority,
                "status": project.status,
                "start_date": project.start_date,
                "target_end_date": project.target_end_date,
                "work_item_count": total_items,
                "done_items": done_items,
                "avg_progress_pct": round(
                    sum(item.progress_pct for item in project.work_items) / total_items, 1
                )
                if total_items
                else 0,
            }
        )

    return pd.DataFrame(rows)


def work_items_dataframe(session: Session) -> pd.DataFrame:
    work_items = session.scalars(
        select(WorkItem)
        .options(
            selectinload(WorkItem.division),
            selectinload(WorkItem.project),
            selectinload(WorkItem.owner_employee),
            selectinload(WorkItem.assignees).selectinload(WorkItemAssignee.employee),
            selectinload(WorkItem.activity_logs),
        )
        .order_by(WorkItem.due_date, WorkItem.title)
    ).all()

    today = date.today()
    rows: list[dict[str, object]] = []
    for work_item in work_items:
        assignee_ids = [assignment.employee_id for assignment in work_item.assignees if assignment.employee]
        assignee_names = sorted(
            {assignment.employee.full_name for assignment in work_item.assignees if assignment.employee}
        )
        latest_activity = max(
            work_item.activity_logs,
            key=lambda activity: (activity.activity_date, activity.id),
            default=None,
        )
        is_overdue = bool(work_item.due_date and work_item.due_date < today and work_item.status != "Done")
        rows.append(
            {
                "id": work_item.id,
                "project_id": work_item.project_id,
                "project_name": work_item.project.name if work_item.project else "Unassigned",
                "division_id": work_item.division_id,
                "division_name": work_item.division.name if work_item.division else "",
                "title": work_item.title,
                "description": work_item.description or "",
                "category": work_item.category or "",
                "priority": work_item.priority,
                "status": work_item.status,
                "owner_employee_id": work_item.owner_employee_id,
                "owner_name": work_item.owner_employee.full_name if work_item.owner_employee else "",
                "planned_start_date": work_item.planned_start_date,
                "due_date": work_item.due_date,
                "completed_date": work_item.completed_date,
                "progress_pct": work_item.progress_pct,
                "assignee_ids": assignee_ids,
                "assignee_names": ", ".join(assignee_names),
                "activity_count": len(work_item.activity_logs),
                "latest_activity_date": latest_activity.activity_date if latest_activity else None,
                "is_overdue": is_overdue,
                "days_to_due": (work_item.due_date - today).days if work_item.due_date else None,
            }
        )

    return pd.DataFrame(rows)


def activity_logs_dataframe(session: Session) -> pd.DataFrame:
    activity_logs = session.scalars(
        select(ActivityLog)
        .options(
            selectinload(ActivityLog.employee).selectinload(Employee.division),
            selectinload(ActivityLog.work_item),
            selectinload(ActivityLog.project),
        )
        .order_by(ActivityLog.activity_date.desc(), ActivityLog.id.desc())
    ).all()

    rows: list[dict[str, object]] = []
    for activity in activity_logs:
        rows.append(
            {
                "id": activity.id,
                "activity_date": activity.activity_date,
                "employee_id": activity.employee_id,
                "employee_name": activity.employee.full_name if activity.employee else "",
                "division_name": activity.employee.division.name if activity.employee and activity.employee.division else "",
                "work_item_id": activity.work_item_id,
                "work_item_title": activity.work_item.title if activity.work_item else "",
                "project_name": activity.project.name if activity.project else "",
                "activity_type": activity.activity_type,
                "summary": activity.summary,
                "details": activity.details or "",
                "hours_spent": float(activity.hours_spent) if activity.hours_spent is not None else None,
                "status": activity.status,
                "progress_pct": activity.progress_pct,
                "blocker_note": activity.blocker_note or "",
                "next_action": activity.next_action or "",
                "created_by": activity.created_by or "",
            }
        )

    return pd.DataFrame(rows)
