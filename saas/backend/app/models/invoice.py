import json
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class EnergyInvoiceBatch(Base):
    __tablename__ = "energy_invoice_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    uploaded_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="manual_batch")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="processing")
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ignored_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["EnergyInvoiceBatchItem"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="EnergyInvoiceBatchItem.id",
    )


class EnergyInvoiceBatchItem(Base):
    __tablename__ = "energy_invoice_batch_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("energy_invoice_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invoice_import_id: Mapped[int | None] = mapped_column(
        ForeignKey("energy_invoice_imports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    archive_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    batch: Mapped[EnergyInvoiceBatch] = relationship(back_populates="items")
    invoice_import: Mapped["EnergyInvoiceImport | None"] = relationship(back_populates="batch_items")


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

    batch_items: Mapped[list[EnergyInvoiceBatchItem]] = relationship(back_populates="invoice_import")
    normalized_invoice: Mapped["EnergyInvoice | None"] = relationship(
        back_populates="invoice_import",
        cascade="all, delete-orphan",
        uselist=False,
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

    @property
    def contract_holder(self) -> str | None:
        if self.normalized_invoice is not None and self.normalized_invoice.contract_holder:
            return self.normalized_invoice.contract_holder

        result = self.analysis_result
        invoice = result.get("invoice") if result else None
        value = invoice.get("contract_holder") if isinstance(invoice, dict) else None
        return value if isinstance(value, str) and value.strip() else None


class EnergyInvoice(Base):
    __tablename__ = "energy_invoices"
    __table_args__ = (UniqueConstraint("import_id", name="uq_energy_invoices_import_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("energy_invoice_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    supplier: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    invoice_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(120), nullable=True)
    global_customer_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contract_holder: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contract_siret: Mapped[str | None] = mapped_column(String(80), nullable=True)
    market_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    regroupement: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    chorus_ej: Mapped[str | None] = mapped_column(String(120), nullable=True)
    chorus_service_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    total_consumption_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_taxes: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_vat: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_ttc: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(12), nullable=False, default="EUR")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    invoice_import: Mapped[EnergyInvoiceImport] = relationship(back_populates="normalized_invoice")
    sites: Mapped[list["EnergyInvoiceSite"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
    )
    checks: Mapped[list["EnergyInvoiceCheck"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
    )


class EnergyInvoiceSite(Base):
    __tablename__ = "energy_invoice_sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("energy_invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prm_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    site_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_address: Mapped[str | None] = mapped_column(String(600), nullable=True)
    meter_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    meter_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    local_customer_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    segment: Mapped[str | None] = mapped_column(String(30), nullable=True)
    tariff_option_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    regroupement: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    summary_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    summary_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    summary_total_ttc: Mapped[float | None] = mapped_column(Float, nullable=True)

    invoice: Mapped[EnergyInvoice] = relationship(back_populates="sites")
    periods: Mapped[list["EnergyInvoicePeriod"]] = relationship(
        back_populates="invoice_site",
        cascade="all, delete-orphan",
    )


class EnergyInvoicePeriod(Base):
    __tablename__ = "energy_invoice_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_site_id: Mapped[int] = mapped_column(
        ForeignKey("energy_invoice_sites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fic_number: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    pdf_page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pdf_page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_vat: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_ttc: Mapped[float | None] = mapped_column(Float, nullable=True)
    subscribed_power_kva: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_reached_power_kva: Mapped[float | None] = mapped_column(Float, nullable=True)

    invoice_site: Mapped[EnergyInvoiceSite] = relationship(back_populates="periods")
    lines: Mapped[list["EnergyInvoiceLine"]] = relationship(
        back_populates="invoice_period",
        cascade="all, delete-orphan",
    )
    meter_reads: Mapped[list["EnergyInvoiceMeterRead"]] = relationship(
        back_populates="invoice_period",
        cascade="all, delete-orphan",
    )


class EnergyInvoiceLine(Base):
    __tablename__ = "energy_invoice_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_period_id: Mapped[int] = mapped_column(
        ForeignKey("energy_invoice_periods.id", ondelete="CASCADE"), nullable=False, index=True
    )
    family: Mapped[str | None] = mapped_column(String(120), nullable=True)
    label: Mapped[str | None] = mapped_column(String(600), nullable=True)
    normalized_code: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    poste: Mapped[str | None] = mapped_column(String(60), nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity_unit: Mapped[str | None] = mapped_column(String(60), nullable=True)
    unit_price_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_price_unit: Mapped[str | None] = mapped_column(String(60), nullable=True)
    amount_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    vat_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_line: Mapped[str | None] = mapped_column(Text, nullable=True)

    invoice_period: Mapped[EnergyInvoicePeriod] = relationship(back_populates="lines")


class EnergyInvoiceMeterRead(Base):
    __tablename__ = "energy_invoice_meter_reads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_period_id: Mapped[int] = mapped_column(
        ForeignKey("energy_invoice_periods.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    meter_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    previous_read_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    previous_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_read_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    reading_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    difference: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    subscribed_power_kva: Mapped[float | None] = mapped_column(Float, nullable=True)
    reached_power_kva: Mapped[float | None] = mapped_column(Float, nullable=True)

    invoice_period: Mapped[EnergyInvoicePeriod] = relationship(back_populates="meter_reads")


class EnergyInvoiceCheck(Base):
    __tablename__ = "energy_invoice_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("energy_invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str | None] = mapped_column(String(255), nullable=True)

    invoice: Mapped[EnergyInvoice] = relationship(back_populates="checks")
