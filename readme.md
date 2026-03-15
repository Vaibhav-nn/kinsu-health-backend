# kinsu-health-backend

## Database Migrations (Alembic)

Schema is now migration-driven for PostgreSQL and should not rely on `Base.metadata.create_all()`.

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your DB URL in `.env`:
```bash
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/kinsu_health
```

3. Apply migrations:
```bash
alembic upgrade head
```

4. Roll back one revision if needed:
```bash
alembic downgrade -1
```
