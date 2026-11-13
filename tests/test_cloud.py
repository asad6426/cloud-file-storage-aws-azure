"""The same tests run against AWS (S3 + DynamoDB) and Azure (Blob + Table Storage) emulators."""
import io
import uuid

import pytest

from cloudfiles.api import create_app
from cloudfiles.service import MAX_BYTES, from_environment


@pytest.fixture(params=["aws", "azure"])
def service(request, monkeypatch):
    monkeypatch.setenv("CLOUD_PROVIDER", request.param)
    if request.param == "azure":
        # A fresh container and table per test keeps the Azure tests independent.
        suffix = uuid.uuid4().hex[:10]
        monkeypatch.setenv("AZURE_CONTAINER", f"files{suffix}")
        monkeypatch.setenv("AZURE_TABLE", f"files{suffix}")
    return from_environment()


@pytest.fixture
def client(service):
    return create_app(service).test_client()


def upload(client, name="report.txt", body=b"hello cloud"):
    return client.post("/files", data={"file": (io.BytesIO(body), name)}, content_type="multipart/form-data")


def test_health_reports_provider(client, service):
    assert client.get("/healthz").get_json() == {"status": "ok", "provider": service.provider}


def test_upload_then_download_returns_same_bytes(client):
    record = upload(client).get_json()
    response = client.get(f"/files/{record['id']}")
    assert response.status_code == 200
    assert response.data == b"hello cloud"
    assert 'filename="report.txt"' in response.headers["Content-Disposition"]


def test_metadata_is_stored_in_the_index(client, service):
    record = upload(client).get_json()
    stored = service.index.get(record["id"])
    assert stored["sha256"] == record["sha256"]
    assert stored["size"] == len(b"hello cloud")
    assert stored["provider"] == service.provider


def test_list_includes_uploaded_file(client):
    record = upload(client).get_json()
    assert record["id"] in [f["id"] for f in client.get("/files").get_json()]


def test_path_traversal_in_filename_is_neutralised(client):
    record = upload(client, name="../../etc/passwd").get_json()
    assert record["filename"] == "passwd"


def test_empty_file_is_rejected(client):
    assert upload(client, body=b"").status_code == 400


def test_oversized_file_is_rejected(client):
    assert upload(client, body=b"x" * (MAX_BYTES + 1)).status_code == 400


def test_unknown_file_returns_404(client):
    assert client.get("/files/does-not-exist").status_code == 404


def test_tampered_content_is_detected(client, service):
    record = upload(client).get_json()
    service.store.put(record["id"], b"changed outside the API", "text/plain")
    assert client.get(f"/files/{record['id']}").status_code == 502
