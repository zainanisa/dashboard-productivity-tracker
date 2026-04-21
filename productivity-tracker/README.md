# Productivity Tracker

Local-first dashboard for employee activity tracking across divisions. The app is designed for analyst-led internal use: proper database schema, admin CRUD, dashboard views, and local SQLite storage without production backend complexity.

## Stack

- `Streamlit` for UI and admin forms
- `SQLAlchemy` for ORM and schema
- `SQLite` for local storage
- `Pandas` and `Plotly` for tabular analysis and charts

## Run

Prerequisites:

- Python `3.13+`
- `uv` installed

Install dependencies:

```bash
uv sync
```

Start the app:

```bash
uv run streamlit run app/main.py
```

Open in browser:

```text
http://localhost:8501
```

The app will:

- create `data/tracker.db` if it does not exist
- build the schema automatically
- seed demo data across multiple divisions on first run

Reset the local demo database:

```bash
rm -f data/tracker.db
uv run streamlit run app/main.py
```

## Included Views

- `Overview`: executive summary, activity trend, overdue and blocked work
- `Divisions`: division-level workload and recent activity
- `Employees`: assignment and activity monitoring per employee
- `Projects`: project progress and work item breakdown
- `Work Items`: detailed work list with quick status update
- `Admin`: add and edit divisions, employees, projects, work items, and activity logs
- `Bulk Import`: upload CSV files for divisions, employees, projects, work items, and activity logs

## CSV Import

CSV templates are included in the `templates/` folder:

- `templates/divisions.csv`
- `templates/employees.csv`
- `templates/projects.csv`
- `templates/work_items.csv`
- `templates/activity_logs.csv`

You can also download the template directly from the `Admin > Bulk Import` tab in the app.

Bulk import behavior:

- append-only import
- validation is done per row
- invalid rows are reported back with row numbers
- successful rows are saved even if some other rows fail

## Notes

- This is intentionally local-first and not production hardened.
- SQLite is suitable for local or small-team internal workflows.
- If usage grows, the data model can be migrated to PostgreSQL later.
