# Cloud File Storage: AWS and Azure

[![Cloud CI](https://github.com/asad6426/cloud-file-storage-aws-azure/actions/workflows/ci.yml/badge.svg)](https://github.com/asad6426/cloud-file-storage-aws-azure/actions/workflows/ci.yml)

A small file storage REST API that runs on either AWS or Azure through one interface. Set `CLOUD_PROVIDER=aws` or `CLOUD_PROVIDER=azure`, and the same application code stores files and their metadata in that cloud.

| | AWS | Azure |
| --- | --- | --- |
| File content | Amazon S3 | Azure Blob Storage |
| Metadata | Amazon DynamoDB | Azure Table Storage |
| SDK | boto3 | azure-storage-blob, azure-data-tables |
| Provisioning | Terraform | Created by the app at startup |

## What it does

- `POST /files` uploads a file and records its size, type and SHA-256 checksum.
- `GET /files` lists stored files.
- `GET /files/<id>` downloads a file and refuses with 502 if the stored bytes no longer match the checksum.
- Filenames are sanitised, so `../../etc/passwd` is stored as `passwd`.
- Empty files and files over 5 MB are rejected.

## Tests

All 9 tests run once against AWS and once against Azure: **18 passed** in the latest CI run. Terraform created the S3 bucket, its public access block and the DynamoDB table before the tests ran.

## How it is tested, and the limits

There is no paid cloud account behind this project, so CI uses emulators that implement the cloud APIs:

- [moto](https://github.com/getmoto/moto) for S3 and DynamoDB
- [Azurite](https://github.com/Azure/Azurite), Microsoft's official emulator, for Blob and Table Storage

The application uses the real AWS and Azure SDKs, and the Terraform configuration targets real AWS when `aws_endpoint` is left empty. It has not been deployed to a live AWS or Azure account, so IAM permissions, networking and costs on a real account are untested.

## Run it

```bash
pip install -r requirements.txt "moto[server]"
moto_server -p 5000 &
docker run -d -p 10000:10000 -p 10002:10002 mcr.microsoft.com/azure-storage/azurite \
  azurite --blobHost 0.0.0.0 --tableHost 0.0.0.0 --skipApiVersionCheck --loose
```

Then set the environment variables shown in [`.github/workflows/ci.yml`](.github/workflows/ci.yml), run `terraform -chdir=terraform apply -var aws_endpoint=http://127.0.0.1:5000` and `python -m pytest -v`.

To use real AWS, configure your AWS credentials, run `terraform -chdir=terraform apply` without `aws_endpoint`, and unset `AWS_ENDPOINT_URL`.

Built with Claude Code.
