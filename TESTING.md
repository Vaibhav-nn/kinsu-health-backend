## Local File Storage Testing

### Using curl

1. **Create a record:**
```bash
curl -X POST http://localhost:8000/vault/records \
  -H "Content-Type: application/json" \
  -d '{
    "records": [{
      "record_type": "lab_report",
      "record_date": "2024-03-10",
      "title": "Blood Test Results",
      "notes": "Annual checkup"
    }]
  }'
```

Response:
```json
{
  "created": 1,
  "record_ids": ["550e8400-e29b-41d4-a716-446655440000"]
}
```

2. **Upload a file:**
```bash
curl -X POST http://localhost:8000/vault/records/{record_id}/upload \
  -F "file=@test.pdf"
```

Response:
```json
{
  "success": true,
  "message": "File uploaded successfully",
  "file_url": "http://localhost:8000/vault/files/{record_id}/{unique-id}.pdf",
  "file_size": 12345
}
```

3. **Download the file:**
```bash
curl http://localhost:8000/vault/files/{record_id}/{unique-id}.pdf \
  --output downloaded.pdf
```

Or just open in browser:
```
http://localhost:8000/vault/files/{record_id}/{unique-id}.pdf
```

### Using Postman

1. **Create Record:**
   - Method: POST
   - URL: `http://localhost:8000/vault/records`
   - Body: JSON (raw)
   ```json
   {
     "records": [{
       "record_type": "lab_report",
       "record_date": "2024-03-10",
       "title": "Test Record"
     }]
   }
   ```

2. **Upload File:**
   - Method: POST
   - URL: `http://localhost:8000/vault/records/{record_id}/upload`
   - Body: form-data
   - Key: `file` (type: File)
   - Select your file

3. **Download File:**
   - Method: GET
   - URL: Copy the `file_url` from upload response
   - Or: `http://localhost:8000/vault/files/{record_id}/{filename}`

### File Structure

Files are stored locally in:
```
./uploads/
  └── {record-id}/
      ├── {uuid}.pdf
      ├── {uuid}.jpg
      └── {uuid}.png
```

### Switching to S3

When ready:
1. Update `.env`: `STORAGE_BACKEND=s3`
2. Add AWS credentials
3. Restart server
4. API automatically switches to presigned URL flow
