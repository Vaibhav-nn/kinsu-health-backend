# Quick Logging Reference

## Import

```python
from app.core.logging import get_logger

logger = get_logger(__name__)
```

## Common Patterns

### 1. API Endpoint Entry
```python
logger.info(
    "Creating new vital",
    extra={"extra_fields": {"user_id": str(user.id), "vital_type": payload.vital_type}},
)
```

### 2. Successful Operation
```python
logger.info(
    "Vital created successfully",
    extra={"extra_fields": {"vital_id": vital.id, "value": vital.value}},
)
```

### 3. Query/Fetch Operation
```python
logger.debug(
    "Fetching vitals list",
    extra={"extra_fields": {"user_id": str(user.id), "limit": limit, "offset": offset}},
)
```

### 4. Delete Operation
```python
logger.info(
    "Deleting record",
    extra={"extra_fields": {"record_id": record_id, "user_id": str(user.id)}},
)
```

### 5. Warning (Missing Resource)
```python
logger.warning(
    "Resource not found",
    extra={"extra_fields": {"resource_id": resource_id}},
)
```

### 6. Error with Exception
```python
try:
    result = await operation()
except Exception as e:
    logger.exception(
        "Operation failed",
        extra={"extra_fields": {"error": str(e), "resource_id": resource_id}},
    )
    raise
```

### 7. File Operations
```python
logger.info(
    "Saving file to storage",
    extra={"extra_fields": {"file_path": file_path, "size_bytes": len(content)}},
)
```

### 8. Authentication Events
```python
logger.info(
    "User authenticated",
    extra={"extra_fields": {"firebase_uid": uid, "created": created}},
)
```

### 9. Service Initialization
```python
logger.info(
    "Service initialized",
    extra={"extra_fields": {"bucket_name": bucket_name, "region": region}},
)
```

### 10. Performance Tracking
```python
logger.info(
    "Request completed",
    extra={
        "extra_fields": {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        }
    },
)
```

## Log Levels Guide

| Level    | Use For                                      | Example                                    |
|----------|----------------------------------------------|--------------------------------------------|
| DEBUG    | Detailed diagnostic info                     | "Querying database with filters: ..."      |
| INFO     | Important business events                    | "User created", "File uploaded"            |
| WARNING  | Recoverable issues                           | "File not found", "Rate limit approaching" |
| ERROR    | Errors that need attention                   | "Database connection failed"               |
| CRITICAL | System-critical failures                     | "Cannot start application"                 |

## Context Variables

Context is automatically available in logs:
- `request_id`: Set by LoggingMiddleware for every request
- `user_id`: Set by get_current_user() after authentication

## Environment Variables

```bash
# .env file
LOG_LEVEL=INFO          # or DEBUG, WARNING, ERROR, CRITICAL
LOG_FORMAT=development  # or json
```

## Testing Your Logs

```bash
# Start the server
uvicorn app.main:app --reload

# Watch logs in another terminal
tail -f <your-log-file>

# Or with JSON parsing
tail -f <your-log-file> | jq '.'
```

## Quick Checklist

When adding logging to a new endpoint:

- [ ] Import logger at the top
- [ ] Log entry point with relevant parameters
- [ ] Log successful completion
- [ ] Log any errors with exception details
- [ ] Include user_id when available
- [ ] Include resource IDs for tracking
- [ ] Use appropriate log level

## Example: Complete Endpoint

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

@router.post("/items", status_code=201)
async def create_item(
    payload: ItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logger.info(
        "Creating new item",
        extra={"extra_fields": {"user_id": str(user.id), "item_type": payload.type}},
    )
    
    try:
        item = Item(user_id=user.id, **payload.model_dump())
        db.add(item)
        await db.flush()
        await db.refresh(item)
        
        logger.info(
            "Item created successfully",
            extra={"extra_fields": {"item_id": item.id}},
        )
        
        return ItemResponse.model_validate(item)
        
    except Exception as e:
        logger.exception(
            "Failed to create item",
            extra={"extra_fields": {"error": str(e)}},
        )
        raise
```
