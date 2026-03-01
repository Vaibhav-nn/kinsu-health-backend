1. Start PostgreSQL and Create Database
Ensure PostgreSQL is running, then create the database:
createdb kinsu_health
If using GUI or Docker, ensure PostgreSQL is reachable at localhost:5432 with DB name
kinsu_health.

2. Configure Environment Variables
Navigate to backend folder:
cd
/Users/vaibhavtiwari/Downloads/Projects/kinsu-health/kinsu-health-backend
Copy environment template:
cp .env.example .env
Edit .env and set DATABASE_URL:
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/kinsu_
health

3. Create Virtual Environment and Install Dependencies
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

4. Run the FastAPI Service
Activate venv and run:
. .venv/bin/activate
uvicorn app.main:app --reload

5. Endpoints
• Health Check: http://127.0.0.1:8000/health
• Swagger Docs: http://127.0.0.1:8000/docs
• Vault Upload: POST /vault/records