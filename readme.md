# Kinsu Health Backend

A modern FastAPI-based health tracking backend with Firebase authentication, async SQLAlchemy, and support for both local and S3 storage.

## Features

- **Authentication**: Firebase Admin SDK for secure user authentication
- **Database**: Async SQLAlchemy with support for PostgreSQL (via asyncpg) and SQLite
- **Storage**: Flexible storage backend (local filesystem or AWS S3)
- **API**: RESTful API with automatic OpenAPI documentation
- **Migrations**: Alembic for database schema management

## Project Structure

```
kinsu-health-backend/
├── app/
│   ├── api/
│   │   ├── deps.py              # FastAPI dependencies (auth, etc.)
│   │   ├── user_sync.py         # User synchronization helpers
│   │   └── v1/                  # API v1 routes
│   │       ├── auth.py
│   │       ├── vitals.py
│   │       ├── symptoms.py
│   │       ├── illness.py
│   │       ├── medications.py
│   │       ├── reminders.py
│   │       ├── homescreen.py
│   │       └── vault.py
│   ├── core/
│   │   ├── config.py            # Unified configuration
│   │   ├── database.py          # Database setup (async)
│   │   └── firebase.py          # Firebase initialization
│   ├── models/                  # SQLAlchemy ORM models
│   ├── schemas/                 # Pydantic schemas
│   ├── services/                # Business logic services
│   └── main.py                  # FastAPI application entry point
├── alembic/                     # Database migrations
├── tests/                       # Test suite
└── requirements.txt             # Python dependencies
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
# Database (async PostgreSQL recommended for production)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/kinsu_health
# For SQLite (development only):
# DATABASE_URL=sqlite+aiosqlite:///./kinsu.db

# Firebase
FIREBASE_CREDENTIALS_PATH=./firebase-service-account.json

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
CORS_ORIGIN_REGEX=^https?://(localhost|127\.0\.0\.1)(:\d+)?$

# API
API_V1_PREFIX=/api/v1
PROJECT_NAME=Kinsu Health API
BASE_URL=http://localhost:8000

# Storage (local or s3)
STORAGE_BACKEND=local
FILE_STORAGE_PATH=./uploads

# AWS S3 (only if STORAGE_BACKEND=s3)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
S3_BUCKET_NAME=kinsu-health-vault
S3_PRESIGNED_URL_EXPIRATION=3600
```

### 3. Setup Firebase

1. Create a Firebase project
2. Download the service account key JSON file
3. Save it as `firebase-service-account.json` in the project root
4. Update `FIREBASE_CREDENTIALS_PATH` in `.env` if using a different path

### 4. Database Migrations

Apply all migrations to set up the database schema:

```bash
alembic upgrade head
```

To create a new migration after modifying models:

```bash
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

To rollback the last migration:

```bash
alembic downgrade -1
```

## Running the Application

### Development

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at:
- Main API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

### Production

Use a production ASGI server like Gunicorn with Uvicorn workers:

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login with Firebase token

### Health Tracking
- `POST /api/v1/vitals` - Log vital signs
- `GET /api/v1/vitals` - List vitals with filters
- `GET /api/v1/vitals/trends` - Get trend data for charts

### Symptoms
- `POST /api/v1/symptoms` - Add chronic symptom
- `GET /api/v1/symptoms` - List symptoms
- `PUT /api/v1/symptoms/{id}` - Update symptom
- `DELETE /api/v1/symptoms/{id}` - Delete symptom

### Medications
- `POST /api/v1/medications` - Add medication
- `GET /api/v1/medications` - List medications
- `PUT /api/v1/medications/{id}` - Update medication
- `DELETE /api/v1/medications/{id}` - Delete medication

### Reminders
- `POST /api/v1/reminders` - Create reminder
- `GET /api/v1/reminders` - List reminders
- `GET /api/v1/reminders/timeline` - Get timeline view
- `PUT /api/v1/reminders/{id}` - Update reminder
- `DELETE /api/v1/reminders/{id}` - Delete reminder

### Illness Episodes
- `POST /api/v1/illness` - Create illness episode
- `GET /api/v1/illness` - List episodes
- `GET /api/v1/illness/{id}` - Get detailed episode
- `POST /api/v1/illness/{id}/details` - Add detail to episode

### Homescreen
- `GET /api/v1/homescreen/overview` - Get home overview
- `GET /api/v1/homescreen/search` - Search across records
- `GET /api/v1/homescreen/notifications` - List notifications
- `GET /api/v1/homescreen/preferences` - Get user preferences

### Vault (Health Records)
- `GET /vault/records` - List health records
- `POST /vault/records` - Create records
- `POST /vault/records/{id}/upload` - Upload file
- `GET /vault/files/{record_id}/{filename}` - Download file

## Storage Options

### Local Storage (Development)

Set in `.env`:
```bash
STORAGE_BACKEND=local
FILE_STORAGE_PATH=./uploads
```

Files are stored in the local filesystem under `./uploads/`.

### AWS S3 (Production)

Set in `.env`:
```bash
STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
```

Files are stored in S3 with presigned URL support for secure uploads/downloads.

## Testing

Run tests with pytest:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=app tests/
```

## Development

### Code Style

The codebase follows PEP 8 with some additional conventions:
- Async/await for all database operations
- Type hints for function signatures
- Pydantic models for request/response validation

### Database

- All database operations use async SQLAlchemy (AsyncSession)
- Transactions are automatically handled by the `get_db` dependency
- Use Alembic for schema changes, never modify the database manually

## License

Proprietary - All rights reserved
