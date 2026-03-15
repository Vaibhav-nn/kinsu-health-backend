# Structured Logging Guide

This document explains the structured logging system implemented in the Kinsu Health backend.

## Overview

The application uses a custom structured logging system that provides:

- **JSON-formatted logs** for production (machine-readable)
- **Colored, human-readable logs** for development
- **Automatic request tracking** with unique request IDs
- **Context injection** (request_id, user_id) in all logs
- **Consistent log levels** across the application

## Configuration

Logging is configured via environment variables in your `.env` file:

```bash
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Log format: "development" or "json"
LOG_FORMAT=development
```

### Log Levels

- **DEBUG**: Detailed diagnostic information (e.g., fetching specific records)
- **INFO**: General informational messages (e.g., user login, file upload)
- **WARNING**: Warning messages (e.g., missing Firebase credentials, invalid tokens)
- **ERROR**: Error messages (e.g., database failures)
- **CRITICAL**: Critical errors that may cause application failure

### Log Formats

#### Development Format (Human-Readable)

```
[ INFO   ] 14:32:45 | app.main | Application startup complete [req=a3f2b1c4]
[WARNING ] 14:33:12 | app.core.firebase | Firebase credentials not found
[ ERROR  ] 14:34:01 | app.api.v1.vault | File not found for download [req=b5e7d8f2, user=c9a1b2d3]
```

Features:
- Color-coded log levels
- Timestamps
- Module names
- Request and user context (when available)

#### JSON Format (Production)

```json
{
  "timestamp": "2026-03-15T14:32:45.123456Z",
  "level": "INFO",
  "logger": "app.main",
  "message": "Application startup complete",
  "module": "main",
  "function": "lifespan",
  "line": 48,
  "request_id": "a3f2b1c4-1234-5678-90ab-cdef12345678",
  "user_id": "c9a1b2d3-4567-89ab-cdef-012345678901"
}
```

## Usage in Code

### Basic Logging

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# Simple log messages
logger.debug("Detailed diagnostic message")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical error")
```

### Logging with Context

Add structured context to your logs using the `extra` parameter:

```python
logger.info(
    "User logged in successfully",
    extra={
        "extra_fields": {
            "user_id": str(user.id),
            "firebase_uid": decoded_token["uid"],
            "email": user.email,
        }
    },
)
```

### Logging Exceptions

Use `logger.exception()` to automatically include stack traces:

```python
try:
    result = dangerous_operation()
except Exception as e:
    logger.exception(
        "Operation failed",
        extra={"extra_fields": {"error": str(e), "input_value": value}},
    )
    raise
```

### Persistent Context with LoggerAdapter

For services or modules that need persistent context across multiple log calls:

```python
from app.core.logging import get_logger_with_context

logger = get_logger_with_context(__name__, service="storage", component="s3")

# All logs from this logger will include service="storage" and component="s3"
logger.info("Processing file", extra={"extra_fields": {"file_id": file_id}})
```

## Request Context

The logging middleware automatically adds context to all logs within a request:

- **request_id**: Unique identifier for each HTTP request
- **user_id**: Authenticated user's ID (when available)

These are automatically included in all log messages during request processing.

The `X-Request-ID` header is also added to all responses for correlation.

## Log Locations

### Application Logs

All application logs go to **stdout** and can be redirected as needed:

```bash
# Run with log redirection
uvicorn app.main:app --reload 2>&1 | tee logs/app.log

# Run in production with JSON logs
LOG_FORMAT=json uvicorn app.main:app
```

### Key Logging Points

The application logs at the following key points:

1. **Application Lifecycle**
   - Startup (Firebase, database initialization)
   - Shutdown

2. **HTTP Requests**
   - Incoming request (method, path, client)
   - Request completion (status code, duration)
   - Request failures (with exception details)

3. **Authentication**
   - Token verification attempts
   - User login/creation
   - Authentication failures

4. **Database Operations**
   - Session commits and rollbacks
   - Database initialization
   - Query errors

5. **File Operations**
   - File uploads (local and S3)
   - File downloads
   - Presigned URL generation

6. **Business Logic**
   - Creating/updating records (vitals, symptoms, medications, etc.)
   - Search operations
   - Data retrieval

## Best Practices

### DO

✅ **Use appropriate log levels**
```python
logger.debug("Fetching user profile")  # Diagnostic
logger.info("User logged in")          # Important event
logger.warning("Rate limit approaching")  # Potential issue
logger.error("Database connection failed")  # Error requiring attention
```

✅ **Include relevant context**
```python
logger.info(
    "Processing payment",
    extra={
        "extra_fields": {
            "user_id": str(user.id),
            "amount": amount,
            "currency": currency,
        }
    },
)
```

✅ **Log exceptions with context**
```python
try:
    process_data()
except Exception as e:
    logger.exception("Data processing failed", extra={"extra_fields": {"data_id": data_id}})
    raise
```

### DON'T

❌ **Don't log sensitive information**
```python
# BAD - logs password
logger.info(f"User login: {email} with password {password}")

# GOOD - no sensitive data
logger.info("User login attempt", extra={"extra_fields": {"email": email}})
```

❌ **Don't log PII without consideration**
```python
# Consider privacy before logging personal information
# Hash or truncate sensitive identifiers when possible
```

❌ **Don't use string formatting in log messages**
```python
# BAD - string formatting happens even if log level is too high
logger.debug(f"Processing {expensive_operation()}")

# GOOD - use extra fields or let the logger handle it
logger.debug("Processing result", extra={"extra_fields": {"result": result}})
```

## Production Deployment

### With Docker

```dockerfile
ENV LOG_FORMAT=json
ENV LOG_LEVEL=INFO
```

### With systemd

```ini
[Service]
Environment="LOG_FORMAT=json"
Environment="LOG_LEVEL=INFO"
StandardOutput=journal
StandardError=journal
```

### Log Aggregation

JSON logs can be easily shipped to log aggregation services:

- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **CloudWatch** (AWS)
- **Datadog**
- **Splunk**
- **Grafana Loki**

Example with Docker + Fluentd:

```yaml
logging:
  driver: "fluentd"
  options:
    fluentd-address: localhost:24224
    tag: kinsu.backend
```

## Monitoring and Alerts

### Key Metrics to Monitor

1. **Error rate**: Count of ERROR/CRITICAL logs per minute
2. **Request latency**: Track `duration_ms` from request completion logs
3. **Authentication failures**: Count of failed token verifications
4. **Database errors**: Count of database rollback events
5. **File operation failures**: Upload/download errors

### Sample Queries

#### CloudWatch Insights

```sql
# Find slow requests
fields @timestamp, request_id, path, duration_ms
| filter level = "INFO" and message = "Request completed"
| filter duration_ms > 1000
| sort duration_ms desc
```

#### Elasticsearch

```json
{
  "query": {
    "bool": {
      "must": [
        {"match": {"level": "ERROR"}},
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ]
    }
  }
}
```

## Troubleshooting

### No logs appearing

1. Check `LOG_LEVEL` in your `.env` file
2. Ensure `setup_logging()` is called in `app/main.py`
3. Verify you're importing logger correctly: `from app.core.logging import get_logger`

### Logs missing context (request_id, user_id)

- Request context is automatically set by the `LoggingMiddleware`
- User context is set when `get_current_user()` is called
- Context only exists within the scope of a request

### Cannot parse JSON logs

- Ensure `LOG_FORMAT=json` is set
- Check that you're not mixing print statements with structured logs
- Verify your log aggregator is configured for newline-delimited JSON

## Examples

### Complete Example: Adding Logging to a New Endpoint

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/example", tags=["Example"])


@router.post("/process")
async def process_data(
    data: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logger.info(
        "Processing data request",
        extra={
            "extra_fields": {
                "user_id": str(user.id),
                "data_size": len(str(data)),
            }
        },
    )
    
    try:
        result = await perform_processing(data)
        
        logger.info(
            "Data processed successfully",
            extra={
                "extra_fields": {
                    "result_id": result.id,
                    "processing_time_ms": result.duration,
                }
            },
        )
        
        return {"status": "success", "result": result}
        
    except ValueError as e:
        logger.warning(
            "Invalid data format",
            extra={"extra_fields": {"error": str(e)}},
        )
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.exception(
            "Unexpected error during processing",
            extra={"extra_fields": {"error": str(e)}},
        )
        raise
```

## Migration from Print Statements

If you have existing `print()` statements, replace them with appropriate logging calls:

```python
# Before
print(f"User {user.id} logged in")

# After
logger.info("User logged in", extra={"extra_fields": {"user_id": str(user.id)}})
```

```python
# Before
print(f"⚠️  Warning: {message}")

# After
logger.warning(message)
```

```python
# Before
print(f"✅ {operation} completed")

# After
logger.info(f"{operation} completed")
```

## Performance Considerations

- Log calls with high log levels (DEBUG) are cheap when the log level is set higher (INFO, WARNING, etc.)
- Avoid expensive operations in log calls (use lazy evaluation)
- The `extra_fields` are only serialized when the log message is actually emitted
- Request context uses `contextvars` for thread-safe, async-safe context storage

## Further Reading

- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)
- [Structured Logging Best Practices](https://www.structlog.org/en/stable/why.html)
- [The Twelve-Factor App: Logs](https://12factor.net/logs)
