import os
import pytest
from src.adapters.storage.local_storage_adapter import LocalStorageAdapter
from src.adapters.storage.gcs_storage_adapter import GcsStorageAdapter


def test_local_storage_adapter(tmp_path):
    base_dir = tmp_path / "storage"
    adapter = LocalStorageAdapter(base_dir=str(base_dir), base_url="https://api.michito.co/files")

    # Create dummy file
    source_file = tmp_path / "prospects.csv"
    source_file.write_text("name,nit\nAcme,900123456", encoding="utf-8")

    # Upload
    dest_path = "orders/ord_123/prospects.csv"
    uri = adapter.upload_file(str(source_file), dest_path)
    assert uri.startswith("file://")
    assert adapter.file_exists(dest_path)

    # Download URL
    url = adapter.generate_download_url(dest_path)
    assert url == "https://api.michito.co/files/orders/ord_123/prospects.csv"


def test_gcs_storage_adapter_mock_fallback(tmp_path):
    adapter = GcsStorageAdapter(bucket_name="michito-test-bucket", force_mock=True)

    # Create dummy file
    source_file = tmp_path / "dossier.md"
    source_file.write_text("# Executive Dossier\nContent here", encoding="utf-8")

    dest_path = "orders/ord_456/dossier.md"
    uri = adapter.upload_file(str(source_file), dest_path, content_type="text/markdown")
    assert uri == "gs://michito-test-bucket/orders/ord_456/dossier.md"
    assert adapter.file_exists(dest_path)
    assert not adapter.file_exists("non_existent_file.csv")

    signed_url = adapter.generate_download_url(dest_path, expiration_hours=48)
    assert "https://storage.googleapis.com/michito-test-bucket/orders/ord_456/dossier.md" in signed_url
    assert "X-Goog-Algorithm=GOOG4-RSA-SHA256" in signed_url
    assert "X-Goog-Expires=172800" in signed_url


def test_gcs_storage_adapter_emulator_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_EMULATOR_HOST", "localhost:9199")
    adapter = GcsStorageAdapter(bucket_name="emulator-bucket", force_mock=False)

    source_file = tmp_path / "prospects.csv"
    source_file.write_text("name,city\nAlpha,Medellin", encoding="utf-8")

    dest_path = "campaigns/test/prospects.csv"
    uri = adapter.upload_file(str(source_file), dest_path)
    assert uri == "gs://emulator-bucket/campaigns/test/prospects.csv"

    url = adapter.generate_download_url(dest_path)
    assert "http://localhost:9199/v0/b/emulator-bucket/o/campaigns%2Ftest%2Fprospects.csv?alt=media" == url

