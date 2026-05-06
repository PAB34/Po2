import json
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class EnergyInvoiceImport(Base):
    __tablename__ = "energy_invoice_imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    uploaded_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="manual_upload")
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(120), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(600), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    supplier_guess: Mapped[str | None] = mapped_column(String(120), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    regroupement: Mapped[str | None] = mapped_column(String(120), nullable=True)
    total_ttc: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_consumption_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    site_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="imported")
    analysis_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    control_status: Mapped[str] = mapped_column(String(30), nullable=False, default="not_checked")
    control_errors_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    control_warnings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    decision_status: Mapped[str] = mapped_column(String(30), nullable=False, default="to_review")
    decision_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    decision_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analysis_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    control_report_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    @property
    def control_issues(self) -> list[dict]:
        if not self.control_report_json:
            return []
        try:
            report = json.loads(self.control_report_json)
        except json.JSONDecodeError:
            return []
        issues = report.get("issues")
        return issues if isinstance(issues, list) else []

    @property
    def analysis_result(self) -> dict | None:
        if not self.analysis_result_json:
            return None
        try:
            result = json.loads(self.analysis_result_json)
        except json.JSONDecodeError:
            return None
        return result if isinstance(result, dict) else None

    @property
    def control_report(self) -> dict | None:
        if not self.control_report_json:
            return None
        try:
            report = json.loads(self.control_report_json)
        except json.JSONDecodeError:
            return None
        return report if isinstance(report, dict) else None
