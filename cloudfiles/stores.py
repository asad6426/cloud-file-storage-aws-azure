"""Storage backends with one interface: AWS S3 + DynamoDB, or Azure Blob + Table Storage."""
from datetime import datetime, timezone

import boto3
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.data.tables import TableServiceClient
from azure.storage.blob import BlobServiceClient, ContentSettings


def now():
    return datetime.now(timezone.utc).isoformat()


class S3BlobStore:
    """File content in Amazon S3. boto3 reads AWS_ENDPOINT_URL, so the same code runs on an emulator."""

    def __init__(self, bucket):
        self.bucket = bucket
        self.client = boto3.client("s3")

    def put(self, key, data, content_type):
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key):
        try:
            return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except self.client.exceptions.NoSuchKey:
            return None


class DynamoIndex:
    """File metadata in a DynamoDB table keyed by file id."""

    def __init__(self, table):
        self.table = boto3.resource("dynamodb").Table(table)

    def add(self, record):
        self.table.put_item(Item={**record, "created_at": now()})

    def get(self, file_id):
        item = self.table.get_item(Key={"id": file_id}).get("Item")
        return {**item, "size": int(item["size"])} if item else None

    def all(self):
        items = self.table.scan()["Items"]
        return sorted(({**i, "size": int(i["size"])} for i in items), key=lambda i: i["created_at"])


class AzureBlobStore:
    """File content in an Azure Blob Storage container."""

    def __init__(self, connection_string, container):
        service = BlobServiceClient.from_connection_string(connection_string)
        self.container = service.get_container_client(container)
        try:
            self.container.create_container()
        except ResourceExistsError:
            pass

    def put(self, key, data, content_type):
        self.container.upload_blob(
            key, data, overwrite=True, content_settings=ContentSettings(content_type=content_type)
        )

    def get(self, key):
        try:
            return self.container.download_blob(key).readall()
        except ResourceNotFoundError:
            return None


class AzureTableIndex:
    """File metadata in Azure Table Storage."""

    PARTITION = "files"

    def __init__(self, connection_string, table):
        service = TableServiceClient.from_connection_string(connection_string)
        self.table = service.create_table_if_not_exists(table)

    def add(self, record):
        self.table.create_entity({"PartitionKey": self.PARTITION, "RowKey": record["id"], **record, "created_at": now()})

    @staticmethod
    def _clean(entity):
        return {k: v for k, v in entity.items() if k not in ("PartitionKey", "RowKey")}

    def get(self, file_id):
        try:
            return self._clean(self.table.get_entity(self.PARTITION, file_id))
        except ResourceNotFoundError:
            return None

    def all(self):
        rows = self.table.query_entities(f"PartitionKey eq '{self.PARTITION}'")
        return sorted((self._clean(r) for r in rows), key=lambda r: r["created_at"])
