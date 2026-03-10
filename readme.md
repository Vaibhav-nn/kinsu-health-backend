## Setup

1. Create database:
```bash
createdb kinsu_health
```

2. Configure .env:
```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/kinsu_health
STORAGE_BACKEND=local
FILE_STORAGE_PATH=./uploads
BASE_URL=http://localhost:8000

# For S3 (when ready):
# STORAGE_BACKEND=s3
# AWS_ACCESS_KEY_ID=your-key
# AWS_SECRET_ACCESS_KEY=your-secret
# AWS_REGION=us-east-1
# S3_BUCKET_NAME=kinsu-health-vault
```

3. Install dependencies:
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

4. Run server:
```bash
uvicorn app.main:app --reload
```

## Endpoints

### Local Storage Mode (default)
- POST /vault/records - Create health record
- POST /vault/records/{record_id}/upload - Upload file directly
- GET /vault/files/{record_id}/{filename} - Download file

### S3 Mode (set STORAGE_BACKEND=s3)
- POST /vault/records - Create health record
- POST /vault/records/upload-url - Get presigned S3 URL
- POST /vault/records/confirm-upload - Confirm file uploaded

## Switching to S3

When ready to use S3:
1. Update .env: `STORAGE_BACKEND=s3`
2. Add AWS credentials to .env
3. Setup S3 bucket with CORS (see cors.json)
4. Restart server