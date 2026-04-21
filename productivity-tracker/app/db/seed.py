from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    ActivityLog,
    Division,
    Employee,
    Project,
    StatusHistory,
    WorkItem,
    WorkItemAssignee,
)
from app.db.session import SessionLocal, create_database


def seed_sample_data(session: Session) -> bool:
    division_count = session.scalar(select(func.count(Division.id)))
    if division_count and division_count > 0:
        return False

    today = date.today()

    divisions = [
        Division(code="OPS", name="Operations", description="Regional operations execution"),
        Division(code="SAL", name="Sales", description="Commercial team and pipeline management"),
        Division(code="FIN", name="Finance", description="Budgeting and reporting"),
        Division(code="HR", name="Human Resources", description="People operations"),
        Division(code="DAT", name="Data Analytics", description="Reporting and insights"),
        Division(code="TEC", name="Technology", description="Application delivery and automation"),
    ]
    session.add_all(divisions)
    session.flush()
    division_map = {division.code: division for division in divisions}

    employees = [
        Employee(
            employee_code="EMP001",
            full_name="Alya Rahma",
            email="alya.rahma@example.com",
            job_title="Operations Lead",
            division_id=division_map["OPS"].id,
            manager_name="Nadia Putri",
            employment_status="Active",
            joined_date=today - timedelta(days=720),
        ),
        Employee(
            employee_code="EMP002",
            full_name="Bima Saputra",
            email="bima.saputra@example.com",
            job_title="Sales Supervisor",
            division_id=division_map["SAL"].id,
            manager_name="Ricky Ananta",
            employment_status="Active",
            joined_date=today - timedelta(days=620),
        ),
        Employee(
            employee_code="EMP003",
            full_name="Citra Wulandari",
            email="citra.wulandari@example.com",
            job_title="Finance Analyst",
            division_id=division_map["FIN"].id,
            manager_name="Mira Astuti",
            employment_status="Active",
            joined_date=today - timedelta(days=410),
        ),
        Employee(
            employee_code="EMP004",
            full_name="Deni Kurniawan",
            email="deni.kurniawan@example.com",
            job_title="HR Business Partner",
            division_id=division_map["HR"].id,
            manager_name="Sinta Lestari",
            employment_status="Active",
            joined_date=today - timedelta(days=530),
        ),
        Employee(
            employee_code="EMP005",
            full_name="Eka Prasetyo",
            email="eka.prasetyo@example.com",
            job_title="Senior Data Analyst",
            division_id=division_map["DAT"].id,
            manager_name="Arif Nugroho",
            employment_status="Active",
            joined_date=today - timedelta(days=305),
        ),
        Employee(
            employee_code="EMP006",
            full_name="Farah Annisa",
            email="farah.annisa@example.com",
            job_title="BI Analyst",
            division_id=division_map["DAT"].id,
            manager_name="Arif Nugroho",
            employment_status="Active",
            joined_date=today - timedelta(days=190),
        ),
        Employee(
            employee_code="EMP007",
            full_name="Gilang Mahendra",
            email="gilang.mahendra@example.com",
            job_title="Backend Engineer",
            division_id=division_map["TEC"].id,
            manager_name="Tara Wisesa",
            employment_status="Active",
            joined_date=today - timedelta(days=455),
        ),
        Employee(
            employee_code="EMP008",
            full_name="Hana Maharani",
            email="hana.maharani@example.com",
            job_title="Product Operations Specialist",
            division_id=division_map["OPS"].id,
            manager_name="Nadia Putri",
            employment_status="Active",
            joined_date=today - timedelta(days=165),
        ),
        Employee(
            employee_code="EMP009",
            full_name="Indra Setiawan",
            email="indra.setiawan@example.com",
            job_title="Finance Controller",
            division_id=division_map["FIN"].id,
            manager_name="Mira Astuti",
            employment_status="Active",
            joined_date=today - timedelta(days=900),
        ),
        Employee(
            employee_code="EMP010",
            full_name="Jihan Lazuardi",
            email="jihan.lazuardi@example.com",
            job_title="Talent Acquisition",
            division_id=division_map["HR"].id,
            manager_name="Sinta Lestari",
            employment_status="On Leave",
            joined_date=today - timedelta(days=270),
            is_active=True,
        ),
    ]
    session.add_all(employees)
    session.flush()
    employee_map = {employee.employee_code: employee for employee in employees}

    projects = [
        Project(
            project_code="PRJ-001",
            name="Cross Division KPI Review",
            description="Standardize KPI tracking and weekly reporting across divisions.",
            owner_division_id=division_map["DAT"].id,
            priority="High",
            status="Active",
            start_date=today - timedelta(days=45),
            target_end_date=today + timedelta(days=30),
        ),
        Project(
            project_code="PRJ-002",
            name="Local Attendance Reconciliation",
            description="Reconcile attendance and activity reporting with team-level trackers.",
            owner_division_id=division_map["HR"].id,
            priority="Medium",
            status="Active",
            start_date=today - timedelta(days=20),
            target_end_date=today + timedelta(days=25),
        ),
        Project(
            project_code="PRJ-003",
            name="Operations Efficiency Dashboard",
            description="Improve operational visibility for ongoing service delivery metrics.",
            owner_division_id=division_map["OPS"].id,
            priority="Critical",
            status="Blocked",
            start_date=today - timedelta(days=60),
            target_end_date=today + timedelta(days=10),
        ),
    ]
    session.add_all(projects)
    session.flush()
    project_map = {project.project_code: project for project in projects}

    work_items = [
        WorkItem(
            project_id=project_map["PRJ-001"].id,
            division_id=division_map["DAT"].id,
            title="Build KPI baseline dataset",
            description="Consolidate source files and clean division-level KPI definitions.",
            category="Data Prep",
            priority="High",
            status="In Progress",
            owner_employee_id=employee_map["EMP005"].id,
            planned_start_date=today - timedelta(days=21),
            due_date=today + timedelta(days=5),
            progress_pct=72,
        ),
        WorkItem(
            project_id=project_map["PRJ-001"].id,
            division_id=division_map["TEC"].id,
            title="Create local dashboard shell",
            description="Prepare local app skeleton and data access layer.",
            category="Development",
            priority="High",
            status="In Progress",
            owner_employee_id=employee_map["EMP007"].id,
            planned_start_date=today - timedelta(days=15),
            due_date=today + timedelta(days=4),
            progress_pct=60,
        ),
        WorkItem(
            project_id=project_map["PRJ-001"].id,
            division_id=division_map["SAL"].id,
            title="Validate sales KPI ownership",
            description="Confirm accountabilities and final review cadence with sales supervisors.",
            category="Validation",
            priority="Medium",
            status="Not Started",
            owner_employee_id=employee_map["EMP002"].id,
            planned_start_date=today - timedelta(days=5),
            due_date=today + timedelta(days=8),
            progress_pct=0,
        ),
        WorkItem(
            project_id=project_map["PRJ-002"].id,
            division_id=division_map["HR"].id,
            title="Map attendance exception cases",
            description="Document edge cases for leave, overtime, and field assignments.",
            category="Process Mapping",
            priority="Medium",
            status="Done",
            owner_employee_id=employee_map["EMP004"].id,
            planned_start_date=today - timedelta(days=18),
            due_date=today - timedelta(days=4),
            completed_date=today - timedelta(days=3),
            progress_pct=100,
        ),
        WorkItem(
            project_id=project_map["PRJ-002"].id,
            division_id=division_map["FIN"].id,
            title="Align payroll reference calendar",
            description="Prepare shared date mapping used for payroll and attendance reconciliation.",
            category="Finance Alignment",
            priority="High",
            status="On Hold",
            owner_employee_id=employee_map["EMP009"].id,
            planned_start_date=today - timedelta(days=12),
            due_date=today + timedelta(days=10),
            progress_pct=35,
        ),
        WorkItem(
            project_id=project_map["PRJ-003"].id,
            division_id=division_map["OPS"].id,
            title="Review branch productivity inputs",
            description="Collect and verify branch-level daily productivity submissions.",
            category="Operations Review",
            priority="Critical",
            status="Blocked",
            owner_employee_id=employee_map["EMP001"].id,
            planned_start_date=today - timedelta(days=30),
            due_date=today - timedelta(days=2),
            progress_pct=48,
        ),
        WorkItem(
            project_id=project_map["PRJ-003"].id,
            division_id=division_map["DAT"].id,
            title="Design backlog aging metric",
            description="Create aging logic for task backlog and SLA exception counts.",
            category="Analytics",
            priority="High",
            status="In Progress",
            owner_employee_id=employee_map["EMP006"].id,
            planned_start_date=today - timedelta(days=14),
            due_date=today + timedelta(days=6),
            progress_pct=55,
        ),
        WorkItem(
            project_id=project_map["PRJ-003"].id,
            division_id=division_map["TEC"].id,
            title="Prepare CSV import utility",
            description="Support batch loading of employee activities and task updates.",
            category="Automation",
            priority="Medium",
            status="Not Started",
            owner_employee_id=employee_map["EMP007"].id,
            planned_start_date=today + timedelta(days=1),
            due_date=today + timedelta(days=14),
            progress_pct=0,
        ),
    ]
    session.add_all(work_items)
    session.flush()

    assignments = [
        WorkItemAssignee(work_item_id=work_items[0].id, employee_id=employee_map["EMP005"].id, assignment_role="Lead", allocation_pct=60),
        WorkItemAssignee(work_item_id=work_items[0].id, employee_id=employee_map["EMP006"].id, assignment_role="Support", allocation_pct=40),
        WorkItemAssignee(work_item_id=work_items[1].id, employee_id=employee_map["EMP007"].id, assignment_role="Lead", allocation_pct=70),
        WorkItemAssignee(work_item_id=work_items[1].id, employee_id=employee_map["EMP005"].id, assignment_role="Product", allocation_pct=30),
        WorkItemAssignee(work_item_id=work_items[2].id, employee_id=employee_map["EMP002"].id, assignment_role="Lead", allocation_pct=100),
        WorkItemAssignee(work_item_id=work_items[3].id, employee_id=employee_map["EMP004"].id, assignment_role="Lead", allocation_pct=100),
        WorkItemAssignee(work_item_id=work_items[4].id, employee_id=employee_map["EMP009"].id, assignment_role="Lead", allocation_pct=70),
        WorkItemAssignee(work_item_id=work_items[4].id, employee_id=employee_map["EMP003"].id, assignment_role="Analyst", allocation_pct=30),
        WorkItemAssignee(work_item_id=work_items[5].id, employee_id=employee_map["EMP001"].id, assignment_role="Lead", allocation_pct=60),
        WorkItemAssignee(work_item_id=work_items[5].id, employee_id=employee_map["EMP008"].id, assignment_role="Coordinator", allocation_pct=40),
        WorkItemAssignee(work_item_id=work_items[6].id, employee_id=employee_map["EMP006"].id, assignment_role="Lead", allocation_pct=100),
        WorkItemAssignee(work_item_id=work_items[7].id, employee_id=employee_map["EMP007"].id, assignment_role="Lead", allocation_pct=100),
    ]
    session.add_all(assignments)

    activity_logs = [
        ActivityLog(
            activity_date=today - timedelta(days=3),
            employee_id=employee_map["EMP005"].id,
            work_item_id=work_items[0].id,
            project_id=project_map["PRJ-001"].id,
            activity_type="Analysis",
            summary="Updated KPI field mapping with finance and sales metric owners.",
            details="Merged duplicate definitions and standardized denominator notes.",
            hours_spent=Decimal("5.50"),
            status="In Progress",
            progress_pct=65,
            next_action="Finalize unresolved ownership for conversion rate metric.",
            created_by="System Seed",
        ),
        ActivityLog(
            activity_date=today - timedelta(days=2),
            employee_id=employee_map["EMP007"].id,
            work_item_id=work_items[1].id,
            project_id=project_map["PRJ-001"].id,
            activity_type="Execution",
            summary="Created local app scaffold and tested database connectivity.",
            details="Completed initial SQLite wiring and module structure.",
            hours_spent=Decimal("6.00"),
            status="In Progress",
            progress_pct=60,
            next_action="Implement summary charts and admin form flow.",
            created_by="System Seed",
        ),
        ActivityLog(
            activity_date=today - timedelta(days=2),
            employee_id=employee_map["EMP004"].id,
            work_item_id=work_items[3].id,
            project_id=project_map["PRJ-002"].id,
            activity_type="Review",
            summary="Closed attendance exception inventory with HR operations.",
            details="All known exceptions documented and approved.",
            hours_spent=Decimal("4.00"),
            status="Done",
            progress_pct=100,
            next_action="Hand over to finance for reconciliation review.",
            created_by="System Seed",
        ),
        ActivityLog(
            activity_date=today - timedelta(days=1),
            employee_id=employee_map["EMP001"].id,
            work_item_id=work_items[5].id,
            project_id=project_map["PRJ-003"].id,
            activity_type="Support",
            summary="Followed up missing branch submissions for productivity tracker.",
            details="Three branches still inconsistent against weekly recap.",
            hours_spent=Decimal("3.50"),
            status="Blocked",
            progress_pct=48,
            blocker_note="Regional branch data submission is incomplete.",
            next_action="Escalate missing files to branch coordinators.",
            created_by="System Seed",
        ),
        ActivityLog(
            activity_date=today,
            employee_id=employee_map["EMP006"].id,
            work_item_id=work_items[6].id,
            project_id=project_map["PRJ-003"].id,
            activity_type="Analysis",
            summary="Refined backlog aging buckets and drafted SLA breach logic.",
            details="Prepared threshold proposal for 3, 7, and 14 day aging bands.",
            hours_spent=Decimal("4.75"),
            status="In Progress",
            progress_pct=55,
            next_action="Review metric logic with operations lead.",
            created_by="System Seed",
        ),
        ActivityLog(
            activity_date=today,
            employee_id=employee_map["EMP003"].id,
            work_item_id=work_items[4].id,
            project_id=project_map["PRJ-002"].id,
            activity_type="Meeting",
            summary="Discussed payroll cut-off dependency for reconciliation timeline.",
            details="Need finalized attendance calendar before next payroll cycle.",
            hours_spent=Decimal("2.00"),
            status="On Hold",
            progress_pct=35,
            blocker_note="Pending payroll calendar approval.",
            next_action="Revisit after controller sign-off.",
            created_by="System Seed",
        ),
    ]
    session.add_all(activity_logs)

    history_rows = [
        StatusHistory(entity_type="project", entity_id=project_map["PRJ-001"].id, old_status=None, new_status="Active", changed_by="System Seed", changed_at=today - timedelta(days=45), note="Project initialized"),
        StatusHistory(entity_type="project", entity_id=project_map["PRJ-003"].id, old_status="Active", new_status="Blocked", changed_by="System Seed", changed_at=today - timedelta(days=6), note="Waiting for branch data inputs"),
        StatusHistory(entity_type="work_item", entity_id=work_items[3].id, old_status="In Progress", new_status="Done", changed_by="System Seed", changed_at=today - timedelta(days=3), note="Exception case mapping approved"),
        StatusHistory(entity_type="work_item", entity_id=work_items[5].id, old_status="In Progress", new_status="Blocked", changed_by="System Seed", changed_at=today - timedelta(days=1), note="Regional files incomplete"),
    ]
    session.add_all(history_rows)
    session.commit()
    return True


def initialize_database() -> None:
    create_database()
    with SessionLocal() as session:
        seed_sample_data(session)
