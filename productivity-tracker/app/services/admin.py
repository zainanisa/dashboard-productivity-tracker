from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ActivityLog, Division, Employee, Project, StatusHistory, WorkItem, WorkItemAssignee


def _ensure_unique(session: Session, model: type, field_name: str, value: str, current_id: int | None = None) -> None:
    field = getattr(model, field_name)
    existing = session.scalar(select(model).where(field == value))
    if existing and getattr(existing, "id", None) != current_id:
        raise ValueError(f"{field_name.replace('_', ' ').title()} '{value}' already exists.")


def _record_status_change(
    session: Session,
    *,
    entity_type: str,
    entity_id: int,
    old_status: str | None,
    new_status: str,
    changed_by: str | None,
    note: str | None,
    changed_at: date | None = None,
) -> None:
    if old_status == new_status:
        return

    session.add(
        StatusHistory(
            entity_type=entity_type,
            entity_id=entity_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            changed_at=changed_at or date.today(),
            note=note,
        )
    )


def _sync_assignees(session: Session, work_item: WorkItem, assignee_ids: list[int]) -> None:
    existing_assignments = session.scalars(
        select(WorkItemAssignee).where(WorkItemAssignee.work_item_id == work_item.id)
    ).all()
    current_ids = {assignment.employee_id for assignment in existing_assignments}
    target_ids = set(assignee_ids)

    for assignment in existing_assignments:
        if assignment.employee_id not in target_ids:
            session.delete(assignment)

    for employee_id in target_ids - current_ids:
        session.add(
            WorkItemAssignee(
                work_item_id=work_item.id,
                employee_id=employee_id,
                assignment_role="Contributor",
                allocation_pct=None,
            )
        )


def create_division(
    session: Session,
    *,
    code: str,
    name: str,
    description: str | None,
    is_active: bool,
) -> Division:
    normalized_code = code.strip().upper()
    _ensure_unique(session, Division, "code", normalized_code)
    division = Division(
        code=normalized_code,
        name=name.strip(),
        description=description.strip() or None if description else None,
        is_active=is_active,
    )
    session.add(division)
    session.commit()
    return division


def create_employee(
    session: Session,
    *,
    employee_code: str,
    full_name: str,
    email: str | None,
    job_title: str,
    division_id: int,
    manager_name: str | None,
    employment_status: str,
    joined_date: date | None,
    is_active: bool,
) -> Employee:
    normalized_code = employee_code.strip().upper()
    _ensure_unique(session, Employee, "employee_code", normalized_code)
    employee = Employee(
        employee_code=normalized_code,
        full_name=full_name.strip(),
        email=email.strip() or None if email else None,
        job_title=job_title.strip(),
        division_id=division_id,
        manager_name=manager_name.strip() or None if manager_name else None,
        employment_status=employment_status,
        joined_date=joined_date,
        is_active=is_active,
    )
    session.add(employee)
    session.commit()
    return employee


def update_employee(
    session: Session,
    *,
    employee_id: int,
    employee_code: str,
    full_name: str,
    email: str | None,
    job_title: str,
    division_id: int,
    manager_name: str | None,
    employment_status: str,
    joined_date: date | None,
    is_active: bool,
) -> Employee:
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise ValueError("Employee not found.")

    normalized_code = employee_code.strip().upper()
    _ensure_unique(session, Employee, "employee_code", normalized_code, employee_id)
    employee.employee_code = normalized_code
    employee.full_name = full_name.strip()
    employee.email = email.strip() or None if email else None
    employee.job_title = job_title.strip()
    employee.division_id = division_id
    employee.manager_name = manager_name.strip() or None if manager_name else None
    employee.employment_status = employment_status
    employee.joined_date = joined_date
    employee.is_active = is_active
    session.commit()
    return employee


def create_project(
    session: Session,
    *,
    project_code: str,
    name: str,
    description: str | None,
    owner_division_id: int,
    priority: str,
    status: str,
    start_date: date | None,
    target_end_date: date | None,
    changed_by: str | None = "Admin",
) -> Project:
    normalized_code = project_code.strip().upper()
    _ensure_unique(session, Project, "project_code", normalized_code)
    project = Project(
        project_code=normalized_code,
        name=name.strip(),
        description=description.strip() or None if description else None,
        owner_division_id=owner_division_id,
        priority=priority,
        status=status,
        start_date=start_date,
        target_end_date=target_end_date,
    )
    session.add(project)
    session.flush()
    _record_status_change(
        session,
        entity_type="project",
        entity_id=project.id,
        old_status=None,
        new_status=status,
        changed_by=changed_by,
        note="Project created",
        changed_at=start_date,
    )
    session.commit()
    return project


def update_project(
    session: Session,
    *,
    project_id: int,
    project_code: str,
    name: str,
    description: str | None,
    owner_division_id: int,
    priority: str,
    status: str,
    start_date: date | None,
    target_end_date: date | None,
    changed_by: str | None = "Admin",
) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise ValueError("Project not found.")

    normalized_code = project_code.strip().upper()
    _ensure_unique(session, Project, "project_code", normalized_code, project_id)
    old_status = project.status
    project.project_code = normalized_code
    project.name = name.strip()
    project.description = description.strip() or None if description else None
    project.owner_division_id = owner_division_id
    project.priority = priority
    project.status = status
    project.start_date = start_date
    project.target_end_date = target_end_date
    _record_status_change(
        session,
        entity_type="project",
        entity_id=project.id,
        old_status=old_status,
        new_status=status,
        changed_by=changed_by,
        note="Project updated",
    )
    session.commit()
    return project


def create_work_item(
    session: Session,
    *,
    project_id: int | None,
    division_id: int,
    title: str,
    description: str | None,
    category: str | None,
    priority: str,
    status: str,
    owner_employee_id: int | None,
    planned_start_date: date | None,
    due_date: date | None,
    progress_pct: int,
    assignee_ids: list[int] | None,
    changed_by: str | None = "Admin",
) -> WorkItem:
    if not 0 <= progress_pct <= 100:
        raise ValueError("Progress must be between 0 and 100.")

    completed_date = due_date if status == "Done" else None
    work_item = WorkItem(
        project_id=project_id,
        division_id=division_id,
        title=title.strip(),
        description=description.strip() or None if description else None,
        category=category.strip() or None if category else None,
        priority=priority,
        status=status,
        owner_employee_id=owner_employee_id,
        planned_start_date=planned_start_date,
        due_date=due_date,
        completed_date=completed_date,
        progress_pct=100 if status == "Done" else progress_pct,
    )
    session.add(work_item)
    session.flush()

    final_assignee_ids = list(assignee_ids or [])
    if owner_employee_id and owner_employee_id not in final_assignee_ids:
        final_assignee_ids.append(owner_employee_id)
    _sync_assignees(session, work_item, final_assignee_ids)
    _record_status_change(
        session,
        entity_type="work_item",
        entity_id=work_item.id,
        old_status=None,
        new_status=status,
        changed_by=changed_by,
        note="Work item created",
        changed_at=planned_start_date,
    )
    session.commit()
    return work_item


def update_work_item(
    session: Session,
    *,
    work_item_id: int,
    project_id: int | None,
    division_id: int,
    title: str,
    description: str | None,
    category: str | None,
    priority: str,
    status: str,
    owner_employee_id: int | None,
    planned_start_date: date | None,
    due_date: date | None,
    progress_pct: int,
    assignee_ids: list[int] | None,
    changed_by: str | None = "Admin",
    note: str | None = "Work item updated",
) -> WorkItem:
    if not 0 <= progress_pct <= 100:
        raise ValueError("Progress must be between 0 and 100.")

    work_item = session.get(WorkItem, work_item_id)
    if work_item is None:
        raise ValueError("Work item not found.")

    old_status = work_item.status
    work_item.project_id = project_id
    work_item.division_id = division_id
    work_item.title = title.strip()
    work_item.description = description.strip() or None if description else None
    work_item.category = category.strip() or None if category else None
    work_item.priority = priority
    work_item.status = status
    work_item.owner_employee_id = owner_employee_id
    work_item.planned_start_date = planned_start_date
    work_item.due_date = due_date
    work_item.progress_pct = 100 if status == "Done" else progress_pct
    if status == "Done":
        work_item.completed_date = date.today()
    elif old_status == "Done":
        work_item.completed_date = None

    final_assignee_ids = list(assignee_ids or [])
    if owner_employee_id and owner_employee_id not in final_assignee_ids:
        final_assignee_ids.append(owner_employee_id)
    _sync_assignees(session, work_item, final_assignee_ids)
    _record_status_change(
        session,
        entity_type="work_item",
        entity_id=work_item.id,
        old_status=old_status,
        new_status=status,
        changed_by=changed_by,
        note=note,
    )
    session.commit()
    return work_item


def update_work_item_status(
    session: Session,
    *,
    work_item_id: int,
    new_status: str,
    progress_pct: int,
    changed_by: str | None,
    note: str | None,
) -> WorkItem:
    work_item = session.get(WorkItem, work_item_id)
    if work_item is None:
        raise ValueError("Work item not found.")
    return update_work_item(
        session,
        work_item_id=work_item_id,
        project_id=work_item.project_id,
        division_id=work_item.division_id,
        title=work_item.title,
        description=work_item.description,
        category=work_item.category,
        priority=work_item.priority,
        status=new_status,
        owner_employee_id=work_item.owner_employee_id,
        planned_start_date=work_item.planned_start_date,
        due_date=work_item.due_date,
        progress_pct=progress_pct,
        assignee_ids=[assignment.employee_id for assignment in work_item.assignees],
        changed_by=changed_by,
        note=note,
    )


def create_activity_log(
    session: Session,
    *,
    activity_date: date,
    employee_id: int,
    work_item_id: int | None,
    project_id: int | None,
    activity_type: str,
    summary: str,
    details: str | None,
    hours_spent: float | None,
    status: str,
    progress_pct: int | None,
    blocker_note: str | None,
    next_action: str | None,
    created_by: str | None,
) -> ActivityLog:
    if progress_pct is not None and not 0 <= progress_pct <= 100:
        raise ValueError("Progress must be between 0 and 100.")
    if status == "Blocked" and not blocker_note:
        raise ValueError("Blocked activities require a blocker note.")

    activity = ActivityLog(
        activity_date=activity_date,
        employee_id=employee_id,
        work_item_id=work_item_id,
        project_id=project_id,
        activity_type=activity_type,
        summary=summary.strip(),
        details=details.strip() or None if details else None,
        hours_spent=Decimal(str(hours_spent)) if hours_spent is not None else None,
        status=status,
        progress_pct=progress_pct,
        blocker_note=blocker_note.strip() or None if blocker_note else None,
        next_action=next_action.strip() or None if next_action else None,
        created_by=created_by.strip() or None if created_by else None,
    )
    session.add(activity)

    if work_item_id:
        work_item = session.get(WorkItem, work_item_id)
        if work_item is not None:
            old_status = work_item.status
            work_item.status = status
            if progress_pct is not None:
                work_item.progress_pct = progress_pct
            if status == "Done":
                work_item.completed_date = activity_date
                work_item.progress_pct = 100
            elif old_status == "Done":
                work_item.completed_date = None
            _record_status_change(
                session,
                entity_type="work_item",
                entity_id=work_item.id,
                old_status=old_status,
                new_status=work_item.status,
                changed_by=created_by,
                note=f"Updated from activity log: {summary.strip()}",
                changed_at=activity_date,
            )

    session.commit()
    return activity
