from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.models import (
    ACTIVITY_TYPES,
    EMPLOYMENT_STATUSES,
    PRIORITY_LEVELS,
    PROJECT_STATUSES,
    WORK_ITEM_STATUSES,
    Division,
    Employee,
    Project,
    WorkItem,
)
from app.db.seed import initialize_database
from app.db.session import DATABASE_PATH, SessionLocal
from app.services.admin import (
    create_activity_log,
    create_division,
    create_employee,
    create_project,
    create_work_item,
    update_employee,
    update_project,
    update_work_item,
    update_work_item_status,
)
from app.services.dashboard import (
    activity_logs_dataframe,
    divisions_dataframe,
    employees_dataframe,
    projects_dataframe,
    work_items_dataframe,
)
from app.services.importers import (
    get_import_spec,
    get_template_bytes,
    import_csv_data,
    list_import_entities,
    preview_csv,
)

STATUS_COLORS = {
    "Not Started": "#6C757D",
    "In Progress": "#2F7EEA",
    "Blocked": "#C83E4D",
    "On Hold": "#D68C1F",
    "Done": "#218856",
    "Planned": "#6C757D",
    "Active": "#0F8B8D",
    "Completed": "#218856",
}


def _safe_dataframe(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=columns)
    return frame


def _id_label_map(records: list[object], label_builder) -> dict[int, str]:
    return {record.id: label_builder(record) for record in records}


def _select_index(options: list[object], current_value: object) -> int:
    try:
        return options.index(current_value)
    except ValueError:
        return 0


def _optional_id_options(record_ids: list[int]) -> list[int | None]:
    return [None, *record_ids]


def _format_optional(label_map: dict[int, str], empty_label: str):
    def formatter(value: int | None) -> str:
        if value is None:
            return empty_label
        return label_map.get(value, empty_label)

    return formatter


def _load_reference_data(session):
    divisions = session.scalars(select(Division).order_by(Division.name)).all()
    employees = session.scalars(select(Employee).order_by(Employee.full_name)).all()
    projects = session.scalars(select(Project).order_by(Project.name)).all()
    work_items = session.scalars(select(WorkItem).order_by(WorkItem.title)).all()
    return divisions, employees, projects, work_items


def render_overview(
    divisions_df: pd.DataFrame,
    employees_df: pd.DataFrame,
    projects_df: pd.DataFrame,
    work_items_df_: pd.DataFrame,
    activity_df: pd.DataFrame,
) -> None:
    st.title("Employee Activity Tracker")
    st.caption("Local-first dashboard for cross-division employee activity, workload, and delivery status.")

    active_employees = int(
        len(employees_df[(employees_df["employment_status"] == "Active") & (employees_df["is_active"])])
    ) if not employees_df.empty else 0
    active_projects = int(len(projects_df[projects_df["status"].isin(["Planned", "Active", "Blocked", "On Hold"])])) if not projects_df.empty else 0
    open_work_items = int(len(work_items_df_[work_items_df_["status"] != "Done"])) if not work_items_df_.empty else 0
    blocked_items = int(len(work_items_df_[work_items_df_["status"] == "Blocked"])) if not work_items_df_.empty else 0

    metrics = st.columns(4)
    metrics[0].metric("Active Employees", active_employees)
    metrics[1].metric("Active Projects", active_projects)
    metrics[2].metric("Open Work Items", open_work_items)
    metrics[3].metric("Blocked Items", blocked_items)

    chart_left, chart_right = st.columns((1.2, 1))
    with chart_left:
        st.subheader("Work Item Status Mix")
        status_df = (
            work_items_df_.groupby("status", as_index=False)["id"].count().rename(columns={"id": "count"})
            if not work_items_df_.empty
            else pd.DataFrame(columns=["status", "count"])
        )
        if status_df.empty:
            st.info("No work items available yet.")
        else:
            fig = px.pie(
                status_df,
                names="status",
                values="count",
                hole=0.45,
                color="status",
                color_discrete_map=STATUS_COLORS,
            )
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, width="stretch")

    with chart_right:
        st.subheader("Blocked Items by Division")
        blocked_df = (
            work_items_df_[work_items_df_["status"] == "Blocked"]
            .groupby("division_name", as_index=False)["id"]
            .count()
            .rename(columns={"id": "blocked_count"})
            if not work_items_df_.empty
            else pd.DataFrame(columns=["division_name", "blocked_count"])
        )
        if blocked_df.empty:
            st.info("No blocked items recorded.")
        else:
            fig = px.bar(
                blocked_df,
                x="division_name",
                y="blocked_count",
                color="division_name",
                text="blocked_count",
            )
            fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, width="stretch")

    trend_col, overdue_col = st.columns((1.3, 1))
    with trend_col:
        st.subheader("Activity Trend")
        if activity_df.empty:
            st.info("No activity logs available yet.")
        else:
            trend_df = (
                activity_df.groupby("activity_date", as_index=False)["id"].count().rename(columns={"id": "entries"})
            )
            fig = px.line(trend_df, x="activity_date", y="entries", markers=True)
            fig.update_traces(line_color="#0F8B8D")
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, width="stretch")

    with overdue_col:
        st.subheader("Overdue Items")
        overdue_df = (
            work_items_df_[work_items_df_["is_overdue"]][
                ["title", "division_name", "owner_name", "due_date", "status", "progress_pct"]
            ]
            if not work_items_df_.empty
            else pd.DataFrame(columns=["title", "division_name", "owner_name", "due_date", "status", "progress_pct"])
        )
        st.dataframe(_safe_dataframe(overdue_df, list(overdue_df.columns)), width="stretch", hide_index=True)

    lower_left, lower_right = st.columns((1, 1.1))
    with lower_left:
        st.subheader("Division Snapshot")
        division_snapshot = divisions_df[
            ["division_name", "active_employees", "open_work_items", "blocked_work_items", "avg_progress_pct"]
        ] if not divisions_df.empty else pd.DataFrame(
            columns=["division_name", "active_employees", "open_work_items", "blocked_work_items", "avg_progress_pct"]
        )
        st.dataframe(division_snapshot, width="stretch", hide_index=True)

    with lower_right:
        st.subheader("Recent Activities")
        recent_df = activity_df.head(10)[
            ["activity_date", "employee_name", "division_name", "work_item_title", "status", "summary"]
        ] if not activity_df.empty else pd.DataFrame(
            columns=["activity_date", "employee_name", "division_name", "work_item_title", "status", "summary"]
        )
        st.dataframe(recent_df, width="stretch", hide_index=True)


def render_divisions(divisions_df: pd.DataFrame, employees_df: pd.DataFrame, work_items_df_: pd.DataFrame, activity_df: pd.DataFrame) -> None:
    st.header("Division Performance")
    if divisions_df.empty:
        st.info("No divisions available yet.")
        return

    division_names = divisions_df["division_name"].tolist()
    selected_division = st.selectbox("Division", options=division_names)

    summary = divisions_df[divisions_df["division_name"] == selected_division].iloc[0]
    division_employees = employees_df[employees_df["division_name"] == selected_division] if not employees_df.empty else pd.DataFrame()
    division_work_items = work_items_df_[work_items_df_["division_name"] == selected_division] if not work_items_df_.empty else pd.DataFrame()
    division_activity = activity_df[activity_df["division_name"] == selected_division] if not activity_df.empty else pd.DataFrame()

    metrics = st.columns(4)
    metrics[0].metric("Active Employees", int(summary["active_employees"]))
    metrics[1].metric("Projects", int(summary["project_count"]))
    metrics[2].metric("Open Items", int(summary["open_work_items"]))
    metrics[3].metric("Average Progress", f'{summary["avg_progress_pct"]}%')

    chart_col, table_col = st.columns((1, 1.2))
    with chart_col:
        st.subheader("Status Distribution")
        status_df = (
            division_work_items.groupby("status", as_index=False)["id"].count().rename(columns={"id": "count"})
            if not division_work_items.empty
            else pd.DataFrame(columns=["status", "count"])
        )
        if status_df.empty:
            st.info("No work items in this division.")
        else:
            fig = px.bar(
                status_df,
                x="status",
                y="count",
                color="status",
                color_discrete_map=STATUS_COLORS,
                text="count",
            )
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, width="stretch")

    with table_col:
        st.subheader("Division Members")
        cols = ["employee_code", "full_name", "job_title", "employment_status", "active_assignments", "activities_last_7d"]
        st.dataframe(_safe_dataframe(division_employees[cols], cols), width="stretch", hide_index=True)

    st.subheader("Latest Activities")
    activity_cols = ["activity_date", "employee_name", "work_item_title", "status", "summary", "next_action"]
    st.dataframe(_safe_dataframe(division_activity.head(12)[activity_cols], activity_cols), width="stretch", hide_index=True)


def render_employees(employees_df: pd.DataFrame, work_items_df_: pd.DataFrame, activity_df: pd.DataFrame) -> None:
    st.header("Employee Activity")
    if employees_df.empty:
        st.info("No employees available yet.")
        return

    filters = st.columns(2)
    division_options = ["All", *employees_df["division_name"].sort_values().unique().tolist()]
    status_options = ["All", *employees_df["employment_status"].sort_values().unique().tolist()]
    selected_division = filters[0].selectbox("Filter by Division", division_options)
    selected_status = filters[1].selectbox("Filter by Employment Status", status_options)

    filtered = employees_df.copy()
    if selected_division != "All":
        filtered = filtered[filtered["division_name"] == selected_division]
    if selected_status != "All":
        filtered = filtered[filtered["employment_status"] == selected_status]

    table_cols = [
        "employee_code",
        "full_name",
        "division_name",
        "job_title",
        "employment_status",
        "active_assignments",
        "activities_last_7d",
    ]
    st.dataframe(_safe_dataframe(filtered[table_cols], table_cols), width="stretch", hide_index=True)

    employee_labels = {
        row["id"]: f'{row["employee_code"]} - {row["full_name"]}'
        for _, row in filtered.iterrows()
    }
    employee_ids = list(employee_labels.keys())
    if not employee_ids:
        st.info("No employees match the selected filters.")
        return

    selected_employee_id = st.selectbox(
        "Inspect Employee",
        options=employee_ids,
        format_func=lambda value: employee_labels[value],
    )
    employee_row = employees_df[employees_df["id"] == selected_employee_id].iloc[0]
    employee_work = (
        work_items_df_[work_items_df_["assignee_ids"].apply(lambda values: selected_employee_id in values)]
        if not work_items_df_.empty
        else pd.DataFrame()
    )
    employee_activity = activity_df[activity_df["employee_id"] == selected_employee_id] if not activity_df.empty else pd.DataFrame()

    metrics = st.columns(4)
    metrics[0].metric("Division", employee_row["division_name"])
    metrics[1].metric("Role", employee_row["job_title"])
    metrics[2].metric("Active Assignments", int(employee_row["active_assignments"]))
    metrics[3].metric("Activities (7d)", int(employee_row["activities_last_7d"]))

    left, right = st.columns((1.1, 1))
    with left:
        st.subheader("Assigned Work Items")
        cols = ["title", "project_name", "status", "priority", "due_date", "progress_pct"]
        st.dataframe(_safe_dataframe(employee_work[cols], cols), width="stretch", hide_index=True)

    with right:
        st.subheader("Recent Activity Log")
        cols = ["activity_date", "work_item_title", "status", "summary", "next_action"]
        st.dataframe(_safe_dataframe(employee_activity.head(10)[cols], cols), width="stretch", hide_index=True)


def render_projects(projects_df: pd.DataFrame, work_items_df_: pd.DataFrame) -> None:
    st.header("Project Monitor")
    if projects_df.empty:
        st.info("No projects available yet.")
        return

    summary_cols = [
        "project_code",
        "project_name",
        "owner_division",
        "priority",
        "status",
        "work_item_count",
        "done_items",
        "avg_progress_pct",
        "target_end_date",
    ]
    st.dataframe(projects_df[summary_cols], width="stretch", hide_index=True)

    project_map = {row["id"]: f'{row["project_code"]} - {row["project_name"]}' for _, row in projects_df.iterrows()}
    selected_project_id = st.selectbox(
        "Inspect Project",
        options=list(project_map.keys()),
        format_func=lambda value: project_map[value],
    )
    project_row = projects_df[projects_df["id"] == selected_project_id].iloc[0]
    project_items = work_items_df_[work_items_df_["project_id"] == selected_project_id] if not work_items_df_.empty else pd.DataFrame()

    metrics = st.columns(4)
    metrics[0].metric("Owner Division", project_row["owner_division"])
    metrics[1].metric("Priority", project_row["priority"])
    metrics[2].metric("Status", project_row["status"])
    metrics[3].metric("Average Progress", f'{project_row["avg_progress_pct"]}%')

    chart_col, table_col = st.columns((1, 1.2))
    with chart_col:
        st.subheader("Project Status Mix")
        status_df = (
            project_items.groupby("status", as_index=False)["id"].count().rename(columns={"id": "count"})
            if not project_items.empty
            else pd.DataFrame(columns=["status", "count"])
        )
        if status_df.empty:
            st.info("This project has no work items.")
        else:
            fig = px.funnel_area(status_df, names="status", values="count", color="status", color_discrete_map=STATUS_COLORS)
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, width="stretch")

    with table_col:
        st.subheader("Work Items")
        cols = ["title", "division_name", "owner_name", "status", "priority", "due_date", "progress_pct"]
        st.dataframe(_safe_dataframe(project_items[cols], cols), width="stretch", hide_index=True)


def render_work_items(session, work_items_df_: pd.DataFrame, activity_df: pd.DataFrame) -> None:
    st.header("Work Items")
    if work_items_df_.empty:
        st.info("No work items available yet.")
        return

    filters = st.columns(3)
    division_options = ["All", *work_items_df_["division_name"].sort_values().unique().tolist()]
    project_options = ["All", *work_items_df_["project_name"].sort_values().unique().tolist()]
    status_options = ["All", *work_items_df_["status"].sort_values().unique().tolist()]
    selected_division = filters[0].selectbox("Division", division_options)
    selected_project = filters[1].selectbox("Project", project_options)
    selected_status = filters[2].selectbox("Status", status_options)

    filtered = work_items_df_.copy()
    if selected_division != "All":
        filtered = filtered[filtered["division_name"] == selected_division]
    if selected_project != "All":
        filtered = filtered[filtered["project_name"] == selected_project]
    if selected_status != "All":
        filtered = filtered[filtered["status"] == selected_status]

    cols = [
        "title",
        "division_name",
        "project_name",
        "owner_name",
        "assignee_names",
        "priority",
        "status",
        "due_date",
        "progress_pct",
    ]
    st.dataframe(_safe_dataframe(filtered[cols], cols), width="stretch", hide_index=True)

    item_map = {row["id"]: f'{row["title"]} [{row["status"]}]' for _, row in filtered.iterrows()}
    if not item_map:
        st.info("No work items match the selected filters.")
        return

    selected_item_id = st.selectbox(
        "Inspect Work Item",
        options=list(item_map.keys()),
        format_func=lambda value: item_map[value],
    )
    item_row = work_items_df_[work_items_df_["id"] == selected_item_id].iloc[0]
    item_activity = activity_df[activity_df["work_item_id"] == selected_item_id] if not activity_df.empty else pd.DataFrame()

    metrics = st.columns(4)
    metrics[0].metric("Owner", item_row["owner_name"] or "Unassigned")
    metrics[1].metric("Priority", item_row["priority"])
    metrics[2].metric("Due Date", str(item_row["due_date"]) if pd.notna(item_row["due_date"]) else "None")
    metrics[3].metric("Progress", f'{item_row["progress_pct"]}%')

    left, right = st.columns((1.2, 1))
    with left:
        st.subheader("Detail")
        st.write(item_row["description"] or "No description provided.")
        meta_df = pd.DataFrame(
            [
                {"Field": "Division", "Value": item_row["division_name"]},
                {"Field": "Project", "Value": item_row["project_name"]},
                {"Field": "Assignees", "Value": item_row["assignee_names"] or "None"},
                {"Field": "Category", "Value": item_row["category"] or "-"},
                {"Field": "Latest Activity", "Value": item_row["latest_activity_date"] or "-"},
            ]
        )
        st.dataframe(meta_df, width="stretch", hide_index=True)

    with right:
        st.subheader("Quick Status Update")
        with st.form("quick_work_item_status_form", clear_on_submit=False):
            new_status = st.selectbox(
                "New Status",
                options=list(WORK_ITEM_STATUSES),
                index=_select_index(list(WORK_ITEM_STATUSES), item_row["status"]),
            )
            progress_pct = st.slider("Progress", min_value=0, max_value=100, value=int(item_row["progress_pct"]))
            changed_by = st.text_input("Changed By", value="Admin")
            note = st.text_area("Note", value="")
            submit = st.form_submit_button("Update Status")

        if submit:
            try:
                update_work_item_status(
                    session,
                    work_item_id=int(selected_item_id),
                    new_status=new_status,
                    progress_pct=int(progress_pct),
                    changed_by=changed_by,
                    note=note,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("Work item status updated.")
                st.rerun()

    st.subheader("Activity Timeline")
    activity_cols = ["activity_date", "employee_name", "status", "progress_pct", "summary", "blocker_note", "next_action"]
    st.dataframe(_safe_dataframe(item_activity[activity_cols], activity_cols), width="stretch", hide_index=True)


def render_admin(session) -> None:
    st.header("Admin")
    divisions, employees, projects, work_items = _load_reference_data(session)

    division_map = _id_label_map(divisions, lambda item: f"{item.code} - {item.name}")
    employee_map = _id_label_map(employees, lambda item: f"{item.employee_code} - {item.full_name}")
    project_map = _id_label_map(projects, lambda item: f"{item.project_code} - {item.name}")
    work_item_map = _id_label_map(work_items, lambda item: f"#{item.id} - {item.title}")

    tabs = st.tabs(["Division", "Employee", "Project", "Work Item", "Activity Log", "Bulk Import"])

    with tabs[0]:
        st.subheader("Create Division")
        with st.form("create_division_form", clear_on_submit=True):
            code = st.text_input("Code", placeholder="OPS")
            name = st.text_input("Name", placeholder="Operations")
            description = st.text_area("Description")
            is_active = st.checkbox("Active", value=True)
            submit = st.form_submit_button("Save Division")
        if submit:
            try:
                create_division(session, code=code, name=name, description=description, is_active=is_active)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("Division created.")
                st.rerun()

    with tabs[1]:
        st.subheader("Create Employee")
        with st.form("create_employee_form", clear_on_submit=True):
            employee_code = st.text_input("Employee Code", placeholder="EMP011")
            full_name = st.text_input("Full Name")
            email = st.text_input("Email")
            job_title = st.text_input("Job Title")
            division_id = st.selectbox(
                "Division",
                options=list(division_map.keys()),
                format_func=lambda value: division_map[value],
            )
            manager_name = st.text_input("Manager Name")
            employment_status = st.selectbox("Employment Status", options=list(EMPLOYMENT_STATUSES))
            joined_date = st.date_input("Joined Date", value=date.today())
            is_active = st.checkbox("Active", value=True)
            submit = st.form_submit_button("Save Employee")
        if submit:
            try:
                create_employee(
                    session,
                    employee_code=employee_code,
                    full_name=full_name,
                    email=email,
                    job_title=job_title,
                    division_id=int(division_id),
                    manager_name=manager_name,
                    employment_status=employment_status,
                    joined_date=joined_date,
                    is_active=is_active,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("Employee created.")
                st.rerun()

        st.divider()
        st.subheader("Edit Employee")
        if not employees:
            st.info("Add employees first.")
        else:
            employee_ids = list(employee_map.keys())
            selected_employee_id = st.selectbox(
                "Employee to Edit",
                options=employee_ids,
                format_func=lambda value: employee_map[value],
                key="edit_employee_select",
            )
            employee = next(item for item in employees if item.id == selected_employee_id)
            with st.form("edit_employee_form", clear_on_submit=False):
                employee_code = st.text_input("Employee Code", value=employee.employee_code)
                full_name = st.text_input("Full Name", value=employee.full_name)
                email = st.text_input("Email", value=employee.email or "")
                job_title = st.text_input("Job Title", value=employee.job_title)
                division_options = list(division_map.keys())
                division_id = st.selectbox(
                    "Division",
                    options=division_options,
                    index=_select_index(division_options, employee.division_id),
                    format_func=lambda value: division_map[value],
                    key="edit_employee_division",
                )
                manager_name = st.text_input("Manager Name", value=employee.manager_name or "")
                employment_status = st.selectbox(
                    "Employment Status",
                    options=list(EMPLOYMENT_STATUSES),
                    index=_select_index(list(EMPLOYMENT_STATUSES), employee.employment_status),
                    key="edit_employee_status",
                )
                joined_date = st.date_input("Joined Date", value=employee.joined_date or date.today(), key="edit_employee_joined")
                is_active = st.checkbox("Active", value=employee.is_active, key="edit_employee_active")
                update_submit = st.form_submit_button("Update Employee")
            if update_submit:
                try:
                    update_employee(
                        session,
                        employee_id=employee.id,
                        employee_code=employee_code,
                        full_name=full_name,
                        email=email,
                        job_title=job_title,
                        division_id=int(division_id),
                        manager_name=manager_name,
                        employment_status=employment_status,
                        joined_date=joined_date,
                        is_active=is_active,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success("Employee updated.")
                    st.rerun()

    with tabs[2]:
        st.subheader("Create Project")
        with st.form("create_project_form", clear_on_submit=True):
            project_code = st.text_input("Project Code", placeholder="PRJ-004")
            name = st.text_input("Project Name")
            description = st.text_area("Description", key="create_project_desc")
            owner_division_id = st.selectbox(
                "Owner Division",
                options=list(division_map.keys()),
                format_func=lambda value: division_map[value],
            )
            priority = st.selectbox("Priority", options=list(PRIORITY_LEVELS))
            status = st.selectbox("Status", options=list(PROJECT_STATUSES))
            start_date = st.date_input("Start Date", value=date.today())
            target_end_date = st.date_input("Target End Date", value=date.today() + timedelta(days=30))
            submit = st.form_submit_button("Save Project")
        if submit:
            try:
                create_project(
                    session,
                    project_code=project_code,
                    name=name,
                    description=description,
                    owner_division_id=int(owner_division_id),
                    priority=priority,
                    status=status,
                    start_date=start_date,
                    target_end_date=target_end_date,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("Project created.")
                st.rerun()

        st.divider()
        st.subheader("Edit Project")
        if not projects:
            st.info("Add projects first.")
        else:
            project_ids = list(project_map.keys())
            selected_project_id = st.selectbox(
                "Project to Edit",
                options=project_ids,
                format_func=lambda value: project_map[value],
                key="edit_project_select",
            )
            project = next(item for item in projects if item.id == selected_project_id)
            with st.form("edit_project_form", clear_on_submit=False):
                project_code = st.text_input("Project Code", value=project.project_code)
                name = st.text_input("Project Name", value=project.name)
                description = st.text_area("Description", value=project.description or "", key="edit_project_desc")
                division_options = list(division_map.keys())
                owner_division_id = st.selectbox(
                    "Owner Division",
                    options=division_options,
                    index=_select_index(division_options, project.owner_division_id),
                    format_func=lambda value: division_map[value],
                    key="edit_project_division",
                )
                priority = st.selectbox(
                    "Priority",
                    options=list(PRIORITY_LEVELS),
                    index=_select_index(list(PRIORITY_LEVELS), project.priority),
                    key="edit_project_priority",
                )
                status = st.selectbox(
                    "Status",
                    options=list(PROJECT_STATUSES),
                    index=_select_index(list(PROJECT_STATUSES), project.status),
                    key="edit_project_status",
                )
                start_date = st.date_input("Start Date", value=project.start_date or date.today(), key="edit_project_start")
                target_end_date = st.date_input(
                    "Target End Date",
                    value=project.target_end_date or (date.today() + timedelta(days=30)),
                    key="edit_project_target",
                )
                update_submit = st.form_submit_button("Update Project")
            if update_submit:
                try:
                    update_project(
                        session,
                        project_id=project.id,
                        project_code=project_code,
                        name=name,
                        description=description,
                        owner_division_id=int(owner_division_id),
                        priority=priority,
                        status=status,
                        start_date=start_date,
                        target_end_date=target_end_date,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success("Project updated.")
                    st.rerun()

    with tabs[3]:
        st.subheader("Create Work Item")
        with st.form("create_work_item_form", clear_on_submit=True):
            title = st.text_input("Title")
            description = st.text_area("Description", key="create_work_item_desc")
            category = st.text_input("Category")
            project_id = st.selectbox(
                "Project",
                options=_optional_id_options(list(project_map.keys())),
                format_func=_format_optional(project_map, "No project"),
            )
            division_id = st.selectbox(
                "Division",
                options=list(division_map.keys()),
                format_func=lambda value: division_map[value],
            )
            owner_employee_id = st.selectbox(
                "Owner",
                options=_optional_id_options(list(employee_map.keys())),
                format_func=_format_optional(employee_map, "No owner"),
            )
            assignee_ids = st.multiselect(
                "Assignees",
                options=list(employee_map.keys()),
                format_func=lambda value: employee_map[value],
            )
            priority = st.selectbox("Priority", options=list(PRIORITY_LEVELS))
            status = st.selectbox("Status", options=list(WORK_ITEM_STATUSES))
            planned_start_date = st.date_input("Planned Start Date", value=date.today())
            due_date = st.date_input("Due Date", value=date.today() + timedelta(days=7))
            progress_pct = st.slider("Progress", min_value=0, max_value=100, value=0)
            submit = st.form_submit_button("Save Work Item")
        if submit:
            try:
                create_work_item(
                    session,
                    project_id=project_id,
                    division_id=int(division_id),
                    title=title,
                    description=description,
                    category=category,
                    priority=priority,
                    status=status,
                    owner_employee_id=owner_employee_id,
                    planned_start_date=planned_start_date,
                    due_date=due_date,
                    progress_pct=int(progress_pct),
                    assignee_ids=[int(item) for item in assignee_ids],
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("Work item created.")
                st.rerun()

        st.divider()
        st.subheader("Edit Work Item")
        if not work_items:
            st.info("Add work items first.")
        else:
            work_item_ids = list(work_item_map.keys())
            selected_work_item_id = st.selectbox(
                "Work Item to Edit",
                options=work_item_ids,
                format_func=lambda value: work_item_map[value],
                key="edit_work_item_select",
            )
            work_item = next(item for item in work_items if item.id == selected_work_item_id)
            current_assignees = [assignment.employee_id for assignment in work_item.assignees]
            with st.form("edit_work_item_form", clear_on_submit=False):
                title = st.text_input("Title", value=work_item.title)
                description = st.text_area("Description", value=work_item.description or "", key="edit_work_item_desc")
                category = st.text_input("Category", value=work_item.category or "")
                project_options = _optional_id_options(list(project_map.keys()))
                project_id = st.selectbox(
                    "Project",
                    options=project_options,
                    index=_select_index(project_options, work_item.project_id),
                    format_func=_format_optional(project_map, "No project"),
                    key="edit_work_item_project",
                )
                division_options = list(division_map.keys())
                division_id = st.selectbox(
                    "Division",
                    options=division_options,
                    index=_select_index(division_options, work_item.division_id),
                    format_func=lambda value: division_map[value],
                    key="edit_work_item_division",
                )
                owner_options = _optional_id_options(list(employee_map.keys()))
                owner_employee_id = st.selectbox(
                    "Owner",
                    options=owner_options,
                    index=_select_index(owner_options, work_item.owner_employee_id),
                    format_func=_format_optional(employee_map, "No owner"),
                    key="edit_work_item_owner",
                )
                assignee_ids = st.multiselect(
                    "Assignees",
                    options=list(employee_map.keys()),
                    default=current_assignees,
                    format_func=lambda value: employee_map[value],
                    key="edit_work_item_assignees",
                )
                priority = st.selectbox(
                    "Priority",
                    options=list(PRIORITY_LEVELS),
                    index=_select_index(list(PRIORITY_LEVELS), work_item.priority),
                    key="edit_work_item_priority",
                )
                status = st.selectbox(
                    "Status",
                    options=list(WORK_ITEM_STATUSES),
                    index=_select_index(list(WORK_ITEM_STATUSES), work_item.status),
                    key="edit_work_item_status",
                )
                planned_start_date = st.date_input(
                    "Planned Start Date",
                    value=work_item.planned_start_date or date.today(),
                    key="edit_work_item_start",
                )
                due_date = st.date_input(
                    "Due Date",
                    value=work_item.due_date or (date.today() + timedelta(days=7)),
                    key="edit_work_item_due",
                )
                progress_pct = st.slider(
                    "Progress",
                    min_value=0,
                    max_value=100,
                    value=int(work_item.progress_pct),
                    key="edit_work_item_progress",
                )
                update_submit = st.form_submit_button("Update Work Item")
            if update_submit:
                try:
                    update_work_item(
                        session,
                        work_item_id=work_item.id,
                        project_id=project_id,
                        division_id=int(division_id),
                        title=title,
                        description=description,
                        category=category,
                        priority=priority,
                        status=status,
                        owner_employee_id=owner_employee_id,
                        planned_start_date=planned_start_date,
                        due_date=due_date,
                        progress_pct=int(progress_pct),
                        assignee_ids=[int(item) for item in assignee_ids],
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success("Work item updated.")
                    st.rerun()

    with tabs[4]:
        st.subheader("Create Activity Log")
        with st.form("create_activity_log_form", clear_on_submit=True):
            activity_date = st.date_input("Activity Date", value=date.today())
            employee_id = st.selectbox(
                "Employee",
                options=list(employee_map.keys()),
                format_func=lambda value: employee_map[value],
            )
            work_item_id = st.selectbox(
                "Work Item",
                options=_optional_id_options(list(work_item_map.keys())),
                format_func=_format_optional(work_item_map, "No work item"),
            )
            project_id = st.selectbox(
                "Project",
                options=_optional_id_options(list(project_map.keys())),
                format_func=_format_optional(project_map, "No project"),
            )
            activity_type = st.selectbox("Activity Type", options=list(ACTIVITY_TYPES))
            summary = st.text_area("Summary")
            details = st.text_area("Details")
            hours_spent = st.number_input("Hours Spent", min_value=0.0, max_value=24.0, step=0.5, value=1.0)
            status = st.selectbox("Status", options=list(WORK_ITEM_STATUSES))
            progress_pct = st.slider("Progress", min_value=0, max_value=100, value=0, key="activity_progress")
            blocker_note = st.text_area("Blocker Note")
            next_action = st.text_area("Next Action")
            created_by = st.text_input("Created By", value="Admin")
            submit = st.form_submit_button("Save Activity Log")
        if submit:
            try:
                create_activity_log(
                    session,
                    activity_date=activity_date,
                    employee_id=int(employee_id),
                    work_item_id=work_item_id,
                    project_id=project_id,
                    activity_type=activity_type,
                    summary=summary,
                    details=details,
                    hours_spent=float(hours_spent),
                    status=status,
                    progress_pct=int(progress_pct),
                    blocker_note=blocker_note,
                    next_action=next_action,
                    created_by=created_by,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("Activity log created.")
                st.rerun()

    with tabs[5]:
        st.subheader("Bulk Import CSV")
        st.caption("Append-only import for master data and activity logs. Existing duplicates will be reported as row errors.")

        import_entities = list_import_entities()
        selected_entity = st.selectbox(
            "Dataset",
            options=import_entities,
            format_func=lambda value: str(get_import_spec(value)["label"]),
        )
        spec = get_import_spec(selected_entity)

        info_left, info_right = st.columns((1.2, 1))
        with info_left:
            st.markdown("**Required columns**")
            st.code(", ".join(spec["required_columns"]))
            st.markdown("**Optional columns**")
            st.code(", ".join(spec["optional_columns"]))
        with info_right:
            st.markdown("**Notes**")
            st.write(spec["notes"])
            st.download_button(
                "Download CSV Template",
                data=get_template_bytes(selected_entity),
                file_name=f"{selected_entity}.csv",
                mime="text/csv",
            )

        uploaded_file = st.file_uploader(
            "Upload CSV",
            type=["csv"],
            key=f"csv_import_{selected_entity}",
        )
        imported_by = st.text_input("Imported By", value="Admin", key=f"imported_by_{selected_entity}")

        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            try:
                preview_frame = preview_csv(file_bytes)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.markdown("**Preview**")
                st.dataframe(preview_frame, width="stretch", hide_index=True)

            if st.button("Import CSV", type="primary", key=f"import_button_{selected_entity}"):
                try:
                    result = import_csv_data(
                        session,
                        entity_type=selected_entity,
                        file_bytes=file_bytes,
                        imported_by=imported_by,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    summary = st.columns(4)
                    summary[0].metric("Processed", result.processed_count)
                    summary[1].metric("Created", result.created_count)
                    summary[2].metric("Skipped Blank Rows", result.skipped_count)
                    summary[3].metric("Errors", result.error_count)

                    if result.error_count:
                        st.warning("Some rows failed validation. Review the error report below.")
                        st.dataframe(result.errors_dataframe(), width="stretch", hide_index=True)
                    else:
                        st.success("CSV import completed without errors.")

                    st.info("Imported rows are already saved. Refresh or switch pages to reload the latest dashboard data.")


def main() -> None:
    st.set_page_config(
        page_title="Employee Activity Tracker",
        page_icon=":bar_chart:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    initialize_database()

    with SessionLocal() as session:
        divisions_df = divisions_dataframe(session)
        employees_df = employees_dataframe(session)
        projects_df = projects_dataframe(session)
        work_items_df_ = work_items_dataframe(session)
        activity_df = activity_logs_dataframe(session)

        st.sidebar.title("Navigation")
        page = st.sidebar.radio(
            "Go to",
            ["Overview", "Divisions", "Employees", "Projects", "Work Items", "Admin"],
        )
        st.sidebar.caption(f"Database: `{DATABASE_PATH.name}`")
        st.sidebar.caption("Local SQLite + SQLAlchemy + Streamlit")

        if page == "Overview":
            render_overview(divisions_df, employees_df, projects_df, work_items_df_, activity_df)
        elif page == "Divisions":
            render_divisions(divisions_df, employees_df, work_items_df_, activity_df)
        elif page == "Employees":
            render_employees(employees_df, work_items_df_, activity_df)
        elif page == "Projects":
            render_projects(projects_df, work_items_df_)
        elif page == "Work Items":
            render_work_items(session, work_items_df_, activity_df)
        else:
            render_admin(session)


if __name__ == "__main__":
    main()
