"""Upload, list and download files, checking integrity with SHA-256."""
import hashlib
import os
import re
import uuid

MAX_BYTES = 5 * 1024 * 1024


class InvalidFile(ValueError):
    pass


class IntegrityError(RuntimeError):
    pass


def safe_name(filename):
    name = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(filename or ""))
    return name.strip("._") or "file"


class FileService:
    def __init__(self, store, index, provider):
        self.store, self.index, self.provider = store, index, provider

    def upload(self, filename, data, content_type="application/octet-stream"):
        if not data:
            raise InvalidFile("The file is empty")
        if len(data) > MAX_BYTES:
            raise InvalidFile(f"The file is larger than {MAX_BYTES} bytes")
        record = {
            "id": uuid.uuid4().hex,
            "filename": safe_name(filename),
            "content_type": content_type,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "provider": self.provider,
        }
        self.store.put(record["id"], data, content_type)
        self.index.add(record)
        return record

    def list(self):
        return self.index.all()

    def download(self, file_id):
        record = self.index.get(file_id)
        if record is None:
            return None, None
        data = self.store.get(file_id)
        if data is None or hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise IntegrityError(f"Stored content for {file_id} does not match its checksum")
        return record, data


def from_environment():
    """Pick the cloud provider from CLOUD_PROVIDER, so the same app deploys to AWS or Azure."""
    from .stores import AzureBlobStore, AzureTableIndex, DynamoIndex, S3BlobStore

    provider = os.environ.get("CLOUD_PROVIDER", "aws")
    if provider == "aws":
        return FileService(
            S3BlobStore(os.environ["S3_BUCKET"]), DynamoIndex(os.environ["DYNAMODB_TABLE"]), "aws"
        )
    if provider == "azure":
        conn = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        return FileService(
            AzureBlobStore(conn, os.environ.get("AZURE_CONTAINER", "files")),
            AzureTableIndex(conn, os.environ.get("AZURE_TABLE", "files")),
            "azure",
        )
    raise ValueError(f"Unknown CLOUD_PROVIDER: {provider}")
