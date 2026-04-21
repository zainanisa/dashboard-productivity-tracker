from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

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
from app.services.admin import (
    create_activity_log,
    create_division,
    create_employee,
    create_project,
    create_work_item,
)

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"

IMPORT_SPECS = {
    "divisions": {
        "label": "Divisions",
        "required_columns": ["code", "name"],
        "optional_columns": ["description", "is_active"],
        "notes": "Use unique division codes such as OPS, HR, DAT.",
    },
    "employees": {
        "label": "Employees",
        "required_columns": ["employee_code", "full_name", "job_title", "division_code"],
        "optional_columns": [
            "email",
            "manager_name",
            "employment_status",
            "joined_date",
            "is_active",
        ],
        "notes": "Reference divisions by division_code. Dates use YYYY-MM-DD.",
    },
    "projects": {
        "label": "Projects",
        "required_columns": ["project_code", "name", "owner_division_code"],
        "optional_columns": [
            "description",
            "priority",
            "status",
            "start_date",
            "target_end_date",
        ],
        "notes": "Reference owner division by owner_division_code.",
    },
    "work_items": {
        "label": "Work Items",
        "required_columns": ["title", "division_code"],
        "optional_columns": [
            "project_code",
            "description",
            "category",
            "priority",
            "status",
            "owner_employee_code",
            "planned_start_date",
            "due_date",
            "progress_pct",
            "assignee_codes",
        ],
        "notes": "Assignee codes can be separated with ';' or ','. Project code is optional.",
    },
    "activity_logs": {
        "label": "Activity Logs",
        "required_columns": ["activity_date", "employee_code", "summary"],
        "optional_columns": [
            "work_item_title",
            "project_code",
            "activity_type",
            "details",
            "hours_spent",
            "status",
            "progress_pct",
            "blocker_note",
            "next_action",
            "created_by",
        ],
        "notes": "Use work_item_title for direct linking. Add project_code too if titles may repeat.",
    },
}


@dataclass
class ImportErrorDetail:
    row_number: int
    error: str


@dataclass
class ImportResult:
    entity_type: str
    processed_count: int
    created_count: int
    skipped_count: int
    errors: list[ImportErrorDetail]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def errors_dataframe(self) -> pd.DataFrame:
        if not self.errors:
            return pd.DataFrame(columns=["row_number", "error"])
        return pd.DataFrame(
            [{"row_number": item.row_number, "error": item.error} for item in self.errors]
        )


def list_import_entities() -> list[str]:
    return list(IMPORT_SPECS.keys())


def get_import_spec(entity_type: str) -> dict[str, object]:
    if entity_type not in IMPORT_SPECS:
        raise ValueError(f"Unsupported import type: {entity_type}")
    return IMPORT_SPECS[entity_type]


def get_template_bytes(entity_type: str) -> bytes:
    template_path = TEMPLATES_DIR / f"{entity_type}.csv"
    if not template_path.exists():
        raise ValueError(f"Template not found for {entity_type}.")
    return template_path.read_bytes()


def preview_csv(file_bytes: bytes) -> pd.DataFrame:
    frame = _read_csv(file_bytes)
    return frame.head(10)


def import_csv_data(
    session: Session,
    *,
    entity_type: str,
    file_bytes: bytes,
    imported_by: str | None = "CSV Import",
) -> ImportResult:
    spec = get_import_spec(entity_type)
    frame = _read_csv(file_bytes)
    normalized_columns = [column.strip() for column in frame.columns]
    frame.columns = normalized_columns

    required_columns = set(spec["required_columns"])
    missing_columns = sorted(required_columns - set(frame.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    importer = _CSVImporter(session=session, imported_by=imported_by)
    handlers = {
        "divisions": importer.import_division,
        "employees": importer.import_employee,
        "projects": importer.import_project,
        "work_items": importer.import_work_item,
        "activity_logs": importer.import_activity_log,
    }
    handler = handlers[entity_type]

    errors: list[ImportErrorDetail] = []
    created_count = 0
    processed_count = 0
    skipped_count = 0

    for row_index, row in enumerate(frame.to_dict(orient="records"), start=2):
        normalized_row = {key.strip(): _normalize_cell(value) for key, value in row.items()}
        if not any(value not in (None, "") for value in normalized_row.values()):
            skipped_count += 1
            continue

        processed_count += 1
        try:
            handler(normalized_row)
        except ValueError as exc:
            session.rollback()
            errors.append(ImportErrorDetail(row_number=row_index, error=str(exc)))
        else:
            created_count += 1

    return ImportResult(
        entity_type=entity_type,
        processed_count=processed_count,
        created_count=created_count,
        skipped_count=skipped_count,
        errors=errors,
    )


class _CSVImporter:
    def __init__(self, *, session: Session, imported_by: str | None) -> None:
        self.session = session
        self.imported_by = imported_by
        self._division_ids: dict[str, int] = {}
        self._employee_ids: dict[str, int] = {}
        self._project_ids: dict[str, int] = {}

    def import_division(self, row: dict[str, str | None]) -> None:
        create_division(
            self.session,
            code=self._required(row, "code").upper(),
            name=self._required(row, "name"),
            description=self._optional(row, "description"),
            is_active=self._parse_bool(row.get("is_active"), default=True),
        )
        self._division_ids.pop(self._required(row, "code").upper(), None)

    def import_employee(self, row: dict[str, str | None]) -> None:
        create_employee(
            self.session,
            employee_code=self._required(row, "employee_code").upper(),
            full_name=self._required(row, "full_name"),
            email=self._optional(row, "email"),
            job_title=self._required(row, "job_title"),
            division_id=self._get_division_id(self._required(row, "division_code")),
            manager_name=self._optional(row, "manager_name"),
            employment_status=self._parse_choice(
                row.get("employment_status"),
                EMPLOYMENT_STATUSES,
                default="Active",
                field_name="employment_status",
            ),
            joined_date=self._parse_date(row.get("joined_date")),
            is_active=self._parse_bool(row.get("is_active"), default=True),
        )
        self._employee_ids.pop(self._required(row, "employee_code").upper(), None)

    def import_project(self, row: dict[str, str | None]) -> None:
        create_project(
            self.session,
            project_code=self._required(row, "project_code").upper(),
            name=self._required(row, "name"),
            description=self._optional(row, "description"),
            owner_division_id=self._get_division_id(self._required(row, "owner_division_code")),
            priority=self._parse_choice(
                row.get("priority"),
                PRIORITY_LEVELS,
                default="Medium",
                field_name="priority",
            ),
            status=self._parse_choice(
                row.get("status"),
                PROJECT_STATUSES,
                default="Planned",
                field_name="status",
            ),
            start_date=self._parse_date(row.get("start_date")),
            target_end_date=self._parse_date(row.get("target_end_date")),
            changed_by=self.imported_by,
        )
        self._project_ids.pop(self._required(row, "project_code").upper(), None)

    def import_work_item(self, row: dict[str, str | None]) -> None:
        owner_employee_code = self._optional(row, "owner_employee_code")
        owner_employee_id = self._get_employee_id(owner_employee_code) if owner_employee_code else None
        assignee_ids = [self._get_employee_id(code) for code in self._parse_multi_codes(row.get("assignee_codes"))]

        create_work_item(
            self.session,
            project_id=self._get_project_id(row.get("project_code")),
            division_id=self._get_division_id(self._required(row, "division_code")),
            title=self._required(row, "title"),
            description=self._optional(row, "description"),
            category=self._optional(row, "category"),
            priority=self._parse_choice(
                row.get("priority"),
                PRIORITY_LEVELS,
                default="Medium",
                field_name="priority",
            ),
            status=self._parse_choice(
                row.get("status"),
                WORK_ITEM_STATUSES,
                default="Not Started",
                field_name="status",
            ),
            owner_employee_id=owner_employee_id,
            planned_start_date=self._parse_date(row.get("planned_start_date")),
            due_date=self._parse_date(row.get("due_date")),
            progress_pct=self._parse_int(row.get("progress_pct"), default=0, field_name="progress_pct"),
            assignee_ids=assignee_ids,
            changed_by=self.imported_by,
        )

    def import_activity_log(self, row: dict[str, str | None]) -> None:
        project_code = self._optional(row, "project_code")
        work_item_title = self._optional(row, "work_item_title")

        create_activity_log(
            self.session,
            activity_date=self._parse_date(self._required(row, "activity_date"), field_name="activity_date"),
            employee_id=self._get_employee_id(self._required(row, "employee_code")),
            work_item_id=self._get_work_item_id(work_item_title, project_code) if work_item_title else None,
            project_id=self._get_project_id(project_code),
            activity_type=self._parse_choice(
                row.get("activity_type"),
                ACTIVITY_TYPES,
                default="Execution",
                field_name="activity_type",
            ),
            summary=self._required(row, "summary"),
            details=self._optional(row, "details"),
            hours_spent=self._parse_float(row.get("hours_spent"), field_name="hours_spent"),
            status=self._parse_choice(
                row.get("status"),
                WORK_ITEM_STATUSES,
                default="In Progress",
                field_name="status",
            ),
            progress_pct=self._parse_int(row.get("progress_pct"), default=None, field_name="progress_pct"),
            blocker_note=self._optional(row, "blocker_note"),
            next_action=self._optional(row, "next_action"),
            created_by=self._optional(row, "created_by") or self.imported_by,
        )

    def _get_division_id(self, division_code: str) -> int:
        normalized_code = division_code.strip().upper()
        if normalized_code not in self._division_ids:
            division = self.session.scalar(select(Division).where(Division.code == normalized_code))
            if division is None:
                raise ValueError(f"Unknown division_code: {normalized_code}")
            self._division_ids[normalized_code] = division.id
        return self._division_ids[normalized_code]

    def _get_employee_id(self, employee_code: str | None) -> int:
        if not employee_code:
            raise ValueError("employee_code is required.")
        normalized_code = employee_code.strip().upper()
        if normalized_code not in self._employee_ids:
            employee = self.session.scalar(select(Employee).where(Employee.employee_code == normalized_code))
            if employee is None:
                raise ValueError(f"Unknown employee_code: {normalized_code}")
            self._employee_ids[normalized_code] = employee.id
        return self._employee_ids[normalized_code]

    def _get_project_id(self, project_code: str | None) -> int | None:
        if not project_code:
            return None
        normalized_code = project_code.strip().upper()
        if normalized_code not in self._project_ids:
            project = self.session.scalar(select(Project).where(Project.project_code == normalized_code))
            if project is None:
                raise ValueError(f"Unknown project_code: {normalized_code}")
            self._project_ids[normalized_code] = project.id
        return self._project_ids[normalized_code]

    def _get_work_item_id(self, title: str, project_code: str | None) -> int:
        statement = select(WorkItem).where(WorkItem.title == title)
        project_id = self._get_project_id(project_code)
        if project_id is not None:
            statement = statement.where(WorkItem.project_id == project_id)
        matches = self.session.scalars(statement).all()
        if not matches:
            raise ValueError(f"Unknown work_item_title: {title}")
        if len(matches) > 1:
            raise ValueError(
                f"Ambiguous work_item_title: {title}. Add project_code to disambiguate."
            )
        return matches[0].id

    @staticmethod
    def _required(row: dict[str, str | None], key: str) -> str:
        value = row.get(key)
        if value in (None, ""):
            raise ValueError(f"{key} is required.")
        return value

    @staticmethod
    def _optional(row: dict[str, str | None], key: str) -> str | None:
        value = row.get(key)
        if value in (None, ""):
            return None
        return value

    @staticmethod
    def _parse_bool(value: str | None, *, default: bool) -> bool:
        if value in (None, ""):
            return default
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y"}:
            return True
        if normalized in {"0", "false", "no", "n"}:
            return False
        raise ValueError(f"Invalid boolean value: {value}")

    @staticmethod
    def _parse_date(value: str | None, *, field_name: str = "date") -> date | None:
        if value in (None, ""):
            return None
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            raise ValueError(f"Invalid {field_name}: {value}. Use YYYY-MM-DD.")
        return parsed.date()

    @staticmethod
    def _parse_int(value: str | None, *, default: int | None, field_name: str) -> int | None:
        if value in (None, ""):
            return default
        try:
            return int(float(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc

    @staticmethod
    def _parse_float(value: str | None, *, field_name: str) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc

    @staticmethod
    def _parse_choice(
        value: str | None,
        options: tuple[str, ...],
        *,
        default: str,
        field_name: str,
    ) -> str:
        if value in (None, ""):
            return default
        normalized_options = {item.lower(): item for item in options}
        normalized_value = value.strip().lower()
        if normalized_value not in normalized_options:
            raise ValueError(f"Invalid {field_name}: {value}. Allowed: {', '.join(options)}")
        return normalized_options[normalized_value]

    @staticmethod
    def _parse_multi_codes(value: str | None) -> list[str]:
        if value in (None, ""):
            return []
        normalized = value.replace(";", ",")
        return [item.strip().upper() for item in normalized.split(",") if item.strip()]


def _read_csv(file_bytes: bytes) -> pd.DataFrame:
    if not file_bytes:
        raise ValueError("CSV file is empty.")
    try:
        return pd.read_csv(BytesIO(file_bytes), dtype=str, keep_default_na=False)
    except Exception as exc:
        raise ValueError("Unable to read CSV file.") from exc


def _normalize_cell(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text
