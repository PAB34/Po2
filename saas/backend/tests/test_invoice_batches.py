from io import BytesIO
from zipfile import ZipFile

from app.models.invoice import EnergyInvoiceBatch, EnergyInvoiceBatchItem
from app.services import invoices


def test_refresh_batch_counts_tracks_each_batch_result() -> None:
    batch = EnergyInvoiceBatch(city_id=1, uploaded_by_user_id=7)
    batch.items = [
        EnergyInvoiceBatchItem(original_filename="a.pdf", status="imported"),
        EnergyInvoiceBatchItem(original_filename="b.pdf", status="duplicate"),
        EnergyInvoiceBatchItem(original_filename="notes.txt", status="ignored"),
        EnergyInvoiceBatchItem(original_filename="broken.pdf", status="error"),
    ]

    invoices._refresh_batch_counts(batch)

    assert batch.file_count == 4
    assert batch.imported_count == 1
    assert batch.duplicate_count == 1
    assert batch.ignored_count == 1
    assert batch.error_count == 1
    assert batch.status == "completed_with_errors"


def test_zip_batch_ignores_non_pdf_members_and_processes_pdfs(monkeypatch) -> None:
    data = BytesIO()
    with ZipFile(data, "w") as archive:
        archive.writestr("FACTURES/engie.pdf", b"%PDF-1.7")
        archive.writestr("FACTURES/readme.txt", b"hors perimetre")

    processed: list[tuple[str, str | None, bytes]] = []

    def fake_append_pdf_item(
        _db,
        _batch,
        _city_id,
        _uploaded_by_user_id,
        filename,
        _content_type,
        member_data,
        *,
        source,
        archive_filename=None,
    ) -> None:
        assert source == "manual_zip"
        processed.append((filename, archive_filename, member_data))

    monkeypatch.setattr(invoices, "_append_pdf_item", fake_append_pdf_item)

    batch = EnergyInvoiceBatch(city_id=1, uploaded_by_user_id=7)
    invoices._append_zip_members(None, batch, 1, 7, "lot.zip", data.getvalue())

    assert processed == [("engie.pdf", "lot.zip", b"%PDF-1.7")]
    assert len(batch.items) == 1
    assert batch.items[0].original_filename == "readme.txt"
    assert batch.items[0].archive_filename == "lot.zip"
    assert batch.items[0].status == "ignored"
