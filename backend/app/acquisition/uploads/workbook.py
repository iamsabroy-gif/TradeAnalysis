"""
Workbook Upload Adapter for Phase 1 Gatekeeper.
Strictly maps to Phase1-PhaseC-Scraper-Implementation-Plan.md §5A.
Parses and validates analyst workbooks (.xlsx and .csv) with formulas disabled.
"""

import csv
import io
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional
import openpyxl

from backend.app.acquisition.base import SourceAdapter
from backend.app.acquisition.types import (
    AdapterError,
    AdapterResult,
    CompanyIdentity,
    ExtractedField,
    RawPage,
)
from backend.app.models.coverage import FIELD_COVERAGE_MATRIX
from backend.app.models.enums import (
    AuditOpinion,
    Confidence,
    ExtractionMethod,
    ReportingBasis,
)


class WorkbookUploadAdapter(SourceAdapter):
    name = "WorkbookUploadAdapter"
    owns_fields: FrozenSet[str] = frozenset(FIELD_COVERAGE_MATRIX.keys())

    def __init__(self, uploader: str = "analyst"):
        self.uploader = uploader

    def fetch(self, ident: CompanyIdentity, basis: ReportingBasis) -> List[RawPage]:
        # Uploads are provided directly via memory/storage
        return []

    def parse(self, pages: List[RawPage]) -> AdapterResult:
        # Default parse interface if raw page is passed
        if not pages:
            return AdapterResult(adapter=self.name)
        return self.parse_bytes(pages[0].content.encode("utf-8"), filename=pages[0].url)

    def parse_bytes(self, content_bytes: bytes, filename: str) -> AdapterResult:
        """
        Parses workbook bytes (.xlsx or .csv) and validates per §5A.2.
        """
        ext = Path(filename).suffix.lower()
        rows: List[Dict[str, str]] = []

        if ext == ".csv":
            text = content_bytes.decode("utf-8", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            for r in reader:
                rows.append({k.strip().lower(): v.strip() for k, v in r.items() if k})
        else:
            # openpyxl with data_only=True disables formula execution
            wb = openpyxl.load_workbook(io.BytesIO(content_bytes), data_only=True)
            ws: Any = wb.active
            if ws is None:
                return AdapterResult(
                    adapter=self.name,
                    fields=[],
                    errors=[AdapterError(field_name="file", message="Empty workbook", fatal=True)],
                )
            header = [str(cell.value or "").strip().lower() for cell in ws[1]]
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not any(row):
                    continue
                row_dict = {}
                for idx, val in enumerate(row):
                    if idx < len(header) and header[idx]:
                        row_dict[header[idx]] = str(val if val is not None else "").strip()
                rows.append(row_dict)

        extracted_fields: List[ExtractedField] = []
        errors: List[AdapterError] = []

        for row in rows:
            f_name = row.get("field_name")
            if not f_name:
                continue

            # 1. Unknown field_name (§5A.2)
            if f_name not in FIELD_COVERAGE_MATRIX:
                errors.append(
                    AdapterError(
                        field_name=f_name,
                        message=f"Unknown field_name '{f_name}' not present in CompanyInput schema",
                        fatal=False,
                    )
                )
                continue

            raw_val = row.get("value", "")
            if not raw_val:
                # Blank field is legitimate missing data
                continue

            source = row.get("source", "")
            # 2. Missing source on populated row (§5A.2)
            if not source:
                errors.append(
                    AdapterError(
                        field_name=f_name,
                        message=f"Missing required 'source' citation for populated field '{f_name}'",
                        fatal=False,
                    )
                )
                continue

            period = row.get("period", "FY24")
            raw_basis = row.get("basis", "").upper()
            if "CONSOLIDATED" in raw_basis:
                basis = ReportingBasis.CONSOLIDATED
            elif "STANDALONE" in raw_basis:
                basis = ReportingBasis.STANDALONE
            else:
                basis = ReportingBasis.NOT_APPLICABLE

            # Type conversion
            parsed_value, err_msg = self._parse_field_value(f_name, raw_val)
            if err_msg:
                errors.append(
                    AdapterError(
                        field_name=f_name,
                        message=f"Value validation failed for '{f_name}': {err_msg}",
                        fatal=False,
                    )
                )
                continue

            extracted_fields.append(
                ExtractedField(
                    field_name=f_name,
                    value=parsed_value,
                    confidence=Confidence.MANUAL,
                    extraction_method=ExtractionMethod.MANUAL,
                    source=f"{source} (Uploaded by {self.uploader})",
                    period=period,
                    basis=basis,
                    raw_snippet=f"{f_name}: {raw_val} [{source}]",
                )
            )

        return AdapterResult(
            adapter=self.name,
            fields=extracted_fields,
            errors=errors,
        )

    def _parse_field_value(self, f_name: str, raw: str) -> tuple[Any, Optional[str]]:
        # Array fields
        if f_name in {"cfo_last_5y", "pat_last_5y"}:
            parts = [p.strip() for p in raw.replace("[", "").replace("]", "").split(",") if p.strip()]
            if len(parts) != 5:
                return None, f"Expected exactly 5 years of numbers, found {len(parts)}"
            try:
                nums = [float(p) for p in parts]
                return nums, None
            except ValueError:
                return None, "All elements in series must be numeric"

        if f_name == "pledged_pct_history_last_4q":
            parts = [p.strip() for p in raw.replace("[", "").replace("]", "").split(",") if p.strip()]
            if len(parts) < 4:
                return None, f"Expected at least 4 quarters of numbers, found {len(parts)}"
            try:
                nums = [float(p) for p in parts]
                return nums, None
            except ValueError:
                return None, "All elements in history must be numeric"

        # Boolean fields
        if f_name in {
            "auditor_resigned_mid_tenure_last_3y",
            "unusual_affiliate_dealings",
            "restatement_of_past_accounts",
        }:
            norm = raw.strip().lower()
            if norm in {"true", "1", "yes", "y"}:
                return True, None
            if norm in {"false", "0", "no", "n"}:
                return False, None
            return None, f"Expected boolean (true/false), got '{raw}'"

        # Enum fields
        if f_name == "audit_opinion":
            norm = raw.strip().upper()
            try:
                return AuditOpinion(norm), None
            except ValueError:
                return None, f"Invalid audit opinion '{raw}'. Expected CLEAN, QUALIFIED, ADVERSE, or DISCLAIMER"

        # Integer fields
        if f_name in {"cfo_changes_last_3y", "years_of_track_record_available"}:
            try:
                return int(float(raw)), None
            except ValueError:
                return None, f"Expected integer, got '{raw}'"

        # Float fields
        try:
            val = float(raw.replace("%", "").replace(",", "").strip())
            return val, None
        except ValueError:
            return None, f"Expected numeric value, got '{raw}'"

    def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "mode": "in-process workbook parser"}
