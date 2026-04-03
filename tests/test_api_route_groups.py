"""HTTP route tests covering all frontend-required API groups."""

import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.deps import verify_firebase_token
from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.services.storage import storage_service


class TestApiRouteGroups(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(cls.engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):  # type: ignore[no-redef]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        cls.SessionLocal = sessionmaker(bind=cls.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(cls.engine)

        cls._orig_storage_backend = settings.STORAGE_BACKEND
        cls._orig_file_storage_path = settings.FILE_STORAGE_PATH
        cls._orig_base_url = settings.BASE_URL

        cls._upload_dir = tempfile.mkdtemp(prefix="kinsu-upload-tests-")
        settings.STORAGE_BACKEND = "local"
        settings.FILE_STORAGE_PATH = cls._upload_dir
        settings.BASE_URL = "http://testserver"
        storage_service.storage_dir = Path(cls._upload_dir)
        storage_service.storage_dir.mkdir(parents=True, exist_ok=True)

        def override_get_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        async def override_verify_firebase_token():
            return {
                "uid": "firebase-route-user",
                "email": "routes@test.com",
                "name": "Routes Test",
            }

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[verify_firebase_token] = override_verify_firebase_token
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

        settings.STORAGE_BACKEND = cls._orig_storage_backend
        settings.FILE_STORAGE_PATH = cls._orig_file_storage_path
        settings.BASE_URL = cls._orig_base_url

        shutil.rmtree(cls._upload_dir, ignore_errors=True)

    def setUp(self) -> None:
        with self.SessionLocal() as db:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            db.commit()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer fake-firebase-id-token"}

    def test_auth_login(self) -> None:
        response = self.client.post("/api/v1/auth/login", headers=self._headers())
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn(body["message"], {"User created successfully.", "Login successful."})
        self.assertEqual(body["user"]["firebase_uid"], "firebase-route-user")

    def test_auth_profile_and_consent_routes(self) -> None:
        login = self.client.post("/api/v1/auth/login", headers=self._headers())
        self.assertEqual(login.status_code, 200)

        initial_profile = self.client.get("/api/v1/auth/profile", headers=self._headers())
        self.assertEqual(initial_profile.status_code, 200)
        self.assertIsNone(initial_profile.json()["user"]["onboarding_completed_at"])

        consent = self.client.post(
            "/api/v1/auth/consent",
            headers=self._headers(),
            json={"accepted": True},
        )
        self.assertEqual(consent.status_code, 200)
        self.assertIsNotNone(consent.json()["user"]["consent_accepted_at"])

        updated = self.client.put(
            "/api/v1/auth/profile",
            headers=self._headers(),
            json={
                "display_name": "Priya Sharma",
                "gender": "female",
                "date_of_birth": "1992-03-15",
                "blood_group": "B+",
                "height_cm": 162,
                "weight_kg": 65,
                "profession": "Engineer",
                "health_goals": ["bp", "weight"],
                "mark_onboarding_complete": True,
            },
        )
        self.assertEqual(updated.status_code, 200)
        body = updated.json()["user"]
        today = date.today()
        expected_age = today.year - 1992 - (
            1 if (today.month, today.day) < (3, 15) else 0
        )
        self.assertEqual(body["display_name"], "Priya Sharma")
        self.assertEqual(body["profession"], "Engineer")
        self.assertEqual(body["health_goals"], ["bp", "weight"])
        self.assertEqual(body["age"], expected_age)
        self.assertIsNotNone(body["onboarding_completed_at"])

        out_of_range = self.client.put(
            "/api/v1/auth/profile",
            headers=self._headers(),
            json={
                "height_cm": 251,
                "weight_kg": 201,
            },
        )
        self.assertEqual(out_of_range.status_code, 422)

    def test_vitals_routes(self) -> None:
        create = self.client.post(
            "/api/v1/vitals",
            headers=self._headers(),
            json={
                "vital_type": "heart_rate",
                "value": 74,
                "value_secondary": None,
                "unit": "bpm",
                "recorded_at": "2026-03-21T09:10:00Z",
                "notes": "morning check",
            },
        )
        self.assertEqual(create.status_code, 201)
        vital_id = create.json()["id"]

        listed = self.client.get("/api/v1/vitals?limit=50&offset=0", headers=self._headers())
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

        snapshot = self.client.post(
            "/api/v1/vitals/snapshot",
            headers=self._headers(),
            json={
                "recorded_at": "2026-03-21T10:00:00Z",
                "blood_pressure_systolic": 128,
                "blood_pressure_diastolic": 84,
                "blood_sugar": 142,
            },
        )
        self.assertEqual(snapshot.status_code, 201)
        self.assertEqual(len(snapshot.json()), 2)

        trends = self.client.get(
            "/api/v1/vitals/trends?vital_type=heart_rate",
            headers=self._headers(),
        )
        self.assertEqual(trends.status_code, 200)
        self.assertEqual(trends.json()["count"], 1)

        today_cards = self.client.get("/api/v1/vitals/today-cards", headers=self._headers())
        self.assertEqual(today_cards.status_code, 200)
        self.assertGreaterEqual(len(today_cards.json()), 6)

        get_one = self.client.get(f"/api/v1/vitals/{vital_id}", headers=self._headers())
        self.assertEqual(get_one.status_code, 200)

        delete = self.client.delete(f"/api/v1/vitals/{vital_id}", headers=self._headers())
        self.assertEqual(delete.status_code, 204)

    def test_symptoms_routes(self) -> None:
        create = self.client.post(
            "/api/v1/symptoms",
            headers=self._headers(),
            json={
                "symptom_name": "headache",
                "severity": 4,
                "frequency": "daily",
                "body_area": "head",
                "triggers": "screen",
                "first_noticed": "2026-03-01",
                "is_active": True,
                "notes": "mild",
            },
        )
        self.assertEqual(create.status_code, 201)
        symptom_id = create.json()["id"]

        listed = self.client.get("/api/v1/symptoms?limit=50&offset=0", headers=self._headers())
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

        quick_log = self.client.post(
            "/api/v1/symptoms/quick-log",
            headers=self._headers(),
            json={
                "symptom_name": "fatigue",
                "severity": 5,
                "notes": "Afternoon dip",
            },
        )
        self.assertEqual(quick_log.status_code, 201)

        dashboard = self.client.get("/api/v1/symptoms/dashboard", headers=self._headers())
        self.assertEqual(dashboard.status_code, 200)
        self.assertGreaterEqual(len(dashboard.json()), 1)

        updated = self.client.put(
            f"/api/v1/symptoms/{symptom_id}",
            headers=self._headers(),
            json={"severity": 6, "notes": "worse in evening"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["severity"], 6)

        delete = self.client.delete(f"/api/v1/symptoms/{symptom_id}", headers=self._headers())
        self.assertEqual(delete.status_code, 204)

    def test_illness_routes(self) -> None:
        create = self.client.post(
            "/api/v1/illness",
            headers=self._headers(),
            json={
                "title": "Seasonal Flu",
                "description": "Fever and cough",
                "start_date": "2026-03-10",
                "status": "active",
            },
        )
        self.assertEqual(create.status_code, 201)
        episode_id = create.json()["id"]

        add_detail = self.client.post(
            f"/api/v1/illness/{episode_id}/details",
            headers=self._headers(),
            json={
                "detail_type": "note",
                "content": "Improved with hydration",
                "recorded_at": "2026-03-11T08:00:00Z",
            },
        )
        self.assertEqual(add_detail.status_code, 201)

        detailed = self.client.get(f"/api/v1/illness/{episode_id}", headers=self._headers())
        self.assertEqual(detailed.status_code, 200)
        self.assertEqual(len(detailed.json().get("details", [])), 1)

        listed = self.client.get("/api/v1/illness?limit=50&offset=0", headers=self._headers())
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

        dashboard = self.client.get("/api/v1/illness/dashboard", headers=self._headers())
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(len(dashboard.json()), 1)

        delete = self.client.delete(f"/api/v1/illness/{episode_id}", headers=self._headers())
        self.assertEqual(delete.status_code, 204)

    def test_medications_routes(self) -> None:
        create = self.client.post(
            "/api/v1/medications",
            headers=self._headers(),
            json={
                "name": "Metformin",
                "dosage": "500mg",
                "frequency": "twice_daily",
                "route": "oral",
                "start_date": "2026-03-01",
                "prescribing_doctor": "Dr. K",
                "is_active": True,
                "notes": "After meals",
            },
        )
        self.assertEqual(create.status_code, 201)
        med_id = create.json()["id"]

        listed = self.client.get("/api/v1/medications?limit=50&offset=0", headers=self._headers())
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

        dose = self.client.post(
            f"/api/v1/medications/{med_id}/doses",
            headers=self._headers(),
            json={
                "scheduled_for": "2026-03-21",
                "scheduled_time": "09:00:00",
                "status": "taken",
                "taken_at": "2026-03-21T09:05:00Z",
            },
        )
        self.assertEqual(dose.status_code, 201)

        overwritten = self.client.post(
            f"/api/v1/medications/{med_id}/doses",
            headers=self._headers(),
            json={
                "scheduled_for": "2026-03-21",
                "scheduled_time": "09:00:00",
                "status": "missed",
            },
        )
        self.assertEqual(overwritten.status_code, 201)
        self.assertEqual(overwritten.json()["id"], dose.json()["id"])
        self.assertEqual(overwritten.json()["status"], "missed")

        dashboard = self.client.get("/api/v1/medications/dashboard", headers=self._headers())
        self.assertEqual(dashboard.status_code, 200)
        self.assertGreaterEqual(len(dashboard.json()["items"]), 1)

        adherence = self.client.get(
            "/api/v1/medications/adherence?view=weekly",
            headers=self._headers(),
        )
        self.assertEqual(adherence.status_code, 200)
        self.assertEqual(adherence.json()["view"], "weekly")

        updated = self.client.put(
            f"/api/v1/medications/{med_id}",
            headers=self._headers(),
            json={"is_active": False},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertFalse(updated.json()["is_active"])

        delete = self.client.delete(f"/api/v1/medications/{med_id}", headers=self._headers())
        self.assertEqual(delete.status_code, 204)

    def test_reminders_routes_and_timeline(self) -> None:
        create = self.client.post(
            "/api/v1/reminders",
            headers=self._headers(),
            json={
                "title": "Evening dose",
                "reminder_type": "medication",
                "linked_medication_id": None,
                "scheduled_time": "20:00:00",
                "recurrence": "daily",
                "is_enabled": True,
                "notes": "After dinner",
            },
        )
        self.assertEqual(create.status_code, 201)
        reminder_id = create.json()["id"]

        listed = self.client.get("/api/v1/reminders?limit=50&offset=0", headers=self._headers())
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

        timeline = self.client.get("/api/v1/reminders/timeline", headers=self._headers())
        self.assertEqual(timeline.status_code, 200)
        self.assertEqual(len(timeline.json()), 1)

        updated = self.client.put(
            f"/api/v1/reminders/{reminder_id}",
            headers=self._headers(),
            json={"is_enabled": False},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertFalse(updated.json()["is_enabled"])

        delete = self.client.delete(f"/api/v1/reminders/{reminder_id}", headers=self._headers())
        self.assertEqual(delete.status_code, 204)

    def test_homescreen_dashboard_routes(self) -> None:
        self.client.post("/api/v1/auth/login", headers=self._headers())
        self.client.post(
            "/api/v1/medications",
            headers=self._headers(),
            json={
                "name": "Amlodipine",
                "dosage": "5mg",
                "frequency": "once_daily",
                "route": "oral",
                "start_date": "2026-03-01",
                "prescribing_doctor": "Dr. Reddy",
                "is_active": True,
            },
        )
        self.client.post(
            "/api/v1/vault/records",
            headers=self._headers(),
            json={
                "records": [
                    {
                        "record_type": "lab_report",
                        "record_date": "2026-03-20",
                        "title": "CBC",
                        "provider_name": "Apollo Hospital",
                    }
                ]
            },
        )
        self.client.post(
            "/api/v1/appointments",
            headers=self._headers(),
            json={
                "doctor_name": "Dr. Kapoor",
                "specialty": "Cardiology",
                "appointment_at": "2026-03-25T10:30:00Z",
                "location": "Apollo Hospital",
            },
        )
        self.client.post(
            "/api/v1/homescreen/notifications",
            headers=self._headers(),
            json={
                "title": "AI Health Insight",
                "body": "Blood sugar has been above 140 this week.",
                "notification_type": "ai",
            },
        )

        overview = self.client.get("/api/v1/homescreen/overview", headers=self._headers())
        self.assertEqual(overview.status_code, 200)

        dashboard = self.client.get("/api/v1/homescreen/dashboard", headers=self._headers())
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(len(dashboard.json()["appointments"]), 1)
        self.assertEqual(len(dashboard.json()["recent_records"]), 1)

        search = self.client.get("/api/v1/homescreen/search?q=Apollo", headers=self._headers())
        self.assertEqual(search.status_code, 200)
        sections = {item["section"] for item in search.json()["results"]}
        self.assertIn("records", sections)
        self.assertIn("appointments", sections)

        notifications = self.client.get("/api/v1/homescreen/notifications", headers=self._headers())
        self.assertEqual(notifications.status_code, 200)
        self.assertGreaterEqual(len(notifications.json()), 1)

    def test_family_dashboard_routes(self) -> None:
        login = self.client.post("/api/v1/auth/login", headers=self._headers())
        self.assertEqual(login.status_code, 200)

        created = self.client.post(
            "/api/v1/family/members",
            headers=self._headers(),
            json={
                "display_name": "Lakshmi Sharma",
                "phone_e164": "+919999999999",
                "relation": "Mother",
                "date_of_birth": "1964-07-10",
                "blood_group": "A+",
                "health_conditions": ["type_2_diabetes", "thyroid"],
            },
        )
        self.assertEqual(created.status_code, 201)
        member_id = created.json()["id"]

        profiles = self.client.get("/api/v1/family/profiles", headers=self._headers())
        self.assertEqual(profiles.status_code, 200)
        self.assertGreaterEqual(len(profiles.json()), 2)

        dashboard = self.client.get("/api/v1/family/dashboard", headers=self._headers())
        self.assertEqual(dashboard.status_code, 200)
        self.assertGreaterEqual(len(dashboard.json()), 2)

        permissions = self.client.get(
            f"/api/v1/family/members/{member_id}/permissions",
            headers=self._headers(),
        )
        self.assertEqual(permissions.status_code, 200)
        self.assertGreaterEqual(len(permissions.json()), 1)

    def test_exercise_routes(self) -> None:
        self.client.post("/api/v1/auth/login", headers=self._headers())

        catalog = self.client.get("/api/v1/exercise/catalog", headers=self._headers())
        self.assertEqual(catalog.status_code, 200)
        self.assertGreaterEqual(len(catalog.json()), 1)

        created = self.client.post(
            "/api/v1/exercise/logs",
            headers=self._headers(),
            json={
                "category": "walk_run",
                "activity_name": "Brisk Walking",
                "duration_minutes": 30,
                "distance_km": 2.5,
            },
        )
        self.assertEqual(created.status_code, 201)
        activity_id = created.json()["id"]

        listed = self.client.get("/api/v1/exercise/logs", headers=self._headers())
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

        summary = self.client.get("/api/v1/exercise/summary", headers=self._headers())
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["activities_done"], 1)

        history = self.client.get("/api/v1/exercise/history", headers=self._headers())
        self.assertEqual(history.status_code, 200)
        self.assertIn("weekly_calories", history.json())

        recommendations = self.client.get(
            "/api/v1/exercise/recommendations",
            headers=self._headers(),
        )
        self.assertEqual(recommendations.status_code, 200)
        self.assertGreaterEqual(len(recommendations.json()["items"]), 1)

        delete = self.client.delete(
            f"/api/v1/exercise/logs/{activity_id}",
            headers=self._headers(),
        )
        self.assertEqual(delete.status_code, 204)

    def test_vault_routes(self) -> None:
        created = self.client.post(
            "/api/v1/vault/records",
            headers=self._headers(),
            json={
                "records": [
                    {
                        "record_type": "lab_report",
                        "record_date": "2026-03-20",
                        "title": "CBC",
                        "notes": "Baseline",
                    }
                ]
            },
        )
        self.assertEqual(created.status_code, 201)
        record_id = created.json()["record_ids"][0]

        created_two = self.client.post(
            "/api/v1/vault/records",
            headers=self._headers(),
            json={
                "records": [
                    {
                        "record_type": "prescription",
                        "record_date": "2026-01-15",
                        "title": "Metformin Rx",
                        "notes": "Refill plan",
                    }
                ]
            },
        )
        self.assertEqual(created_two.status_code, 201)

        listed = self.client.get("/api/v1/vault/records?page=1&limit=50", headers=self._headers())
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["total"], 2)

        connected_services = self.client.get(
            "/api/v1/vault/connected-services",
            headers=self._headers(),
        )
        self.assertEqual(connected_services.status_code, 200)

        get_one = self.client.get(f"/api/v1/vault/records/{record_id}", headers=self._headers())
        self.assertEqual(get_one.status_code, 200)

        searched = self.client.get(
            "/api/v1/vault/records?q=metformin&sort_by=title&sort_order=asc",
            headers=self._headers(),
        )
        self.assertEqual(searched.status_code, 200)
        self.assertEqual(searched.json()["total"], 1)
        self.assertEqual(searched.json()["records"][0]["title"], "Metformin Rx")

        filtered_dates = self.client.get(
            "/api/v1/vault/records?start_date=2026-03-01&end_date=2026-03-31",
            headers=self._headers(),
        )
        self.assertEqual(filtered_dates.status_code, 200)
        self.assertEqual(filtered_dates.json()["total"], 1)

        lab_trend = self.client.get(
            "/api/v1/vault/lab-parameters/trends?parameter_key=hemoglobin",
            headers=self._headers(),
        )
        self.assertEqual(lab_trend.status_code, 200)
        self.assertEqual(lab_trend.json()["parameter_key"], "hemoglobin")
        self.assertIn("history", lab_trend.json())

        upload_url = self.client.post(
            "/api/v1/vault/records/upload-url",
            headers=self._headers(),
            json={
                "record_id": record_id,
                "file_name": "report.pdf",
                "content_type": "application/pdf",
            },
        )
        self.assertEqual(upload_url.status_code, 400)

        confirm = self.client.post(
            "/api/v1/vault/records/confirm-upload",
            headers=self._headers(),
            json={
                "record_id": record_id,
                "s3_key": "key",
                "file_name": "report.pdf",
            },
        )
        self.assertEqual(confirm.status_code, 400)

        uploaded = self.client.post(
            f"/api/v1/vault/records/{record_id}/upload",
            headers=self._headers(),
            files={"file": ("report.txt", b"abc123", "text/plain")},
        )
        self.assertEqual(uploaded.status_code, 200)
        self.assertEqual(uploaded.json()["file_size"], 6)

        has_file = self.client.get(
            "/api/v1/vault/records?has_file=true",
            headers=self._headers(),
        )
        self.assertEqual(has_file.status_code, 200)
        self.assertEqual(has_file.json()["total"], 1)

        legacy = self.client.get("/vault/records?page=1&limit=50", headers=self._headers())
        self.assertEqual(legacy.status_code, 200)

        deleted = self.client.delete(f"/api/v1/vault/records/{record_id}", headers=self._headers())
        self.assertEqual(deleted.status_code, 204)

        missing = self.client.get(f"/api/v1/vault/records/{record_id}", headers=self._headers())
        self.assertEqual(missing.status_code, 404)

    def test_family_profiles_and_scoped_tracking(self) -> None:
        created_member = self.client.post(
            "/api/v1/family/members",
            headers=self._headers(),
            json={
                "display_name": "Lakshmi Sharma",
                "phone_e164": "+919876543210",
                "relation": "Mother",
                "date_of_birth": "1965-06-12",
                "notes": "Type 2 diabetes",
            },
        )
        self.assertEqual(created_member.status_code, 201)
        member_id = created_member.json()["id"]

        profiles = self.client.get("/api/v1/family/profiles", headers=self._headers())
        self.assertEqual(profiles.status_code, 200)
        self.assertEqual(len(profiles.json()), 2)

        self_vital = self.client.post(
            "/api/v1/vitals",
            headers=self._headers(),
            json={
                "vital_type": "heart_rate",
                "value": 71,
                "value_secondary": None,
                "unit": "bpm",
                "recorded_at": "2026-03-22T09:00:00Z",
                "notes": "self",
            },
        )
        self.assertEqual(self_vital.status_code, 201)
        self.assertIsNone(self_vital.json()["family_member_id"])

        member_headers = {**self._headers(), "X-Profile-Id": str(member_id)}
        family_vital = self.client.post(
            "/api/v1/vitals",
            headers=member_headers,
            json={
                "vital_type": "heart_rate",
                "value": 83,
                "value_secondary": None,
                "unit": "bpm",
                "recorded_at": "2026-03-22T09:05:00Z",
                "notes": "family profile",
            },
        )
        self.assertEqual(family_vital.status_code, 201)
        self.assertEqual(family_vital.json()["family_member_id"], member_id)

        self_list = self.client.get("/api/v1/vitals?limit=50&offset=0", headers=self._headers())
        self.assertEqual(self_list.status_code, 200)
        self.assertEqual(len(self_list.json()), 1)
        self.assertIsNone(self_list.json()[0]["family_member_id"])

        family_list = self.client.get(
            "/api/v1/vitals?limit=50&offset=0",
            headers=member_headers,
        )
        self.assertEqual(family_list.status_code, 200)
        self.assertEqual(len(family_list.json()), 1)
        self.assertEqual(family_list.json()[0]["family_member_id"], member_id)

        self_record = self.client.post(
            "/api/v1/vault/records",
            headers=self._headers(),
            json={
                "records": [
                    {
                        "record_type": "lab_report",
                        "record_date": "2026-03-22",
                        "title": "Self Lipid Profile",
                    }
                ]
            },
        )
        self.assertEqual(self_record.status_code, 201)

        member_record = self.client.post(
            "/api/v1/vault/records",
            headers=member_headers,
            json={
                "records": [
                    {
                        "record_type": "lab_report",
                        "record_date": "2026-03-22",
                        "title": "Family Glucose Report",
                    }
                ]
            },
        )
        self.assertEqual(member_record.status_code, 201)

        self_records = self.client.get(
            "/api/v1/vault/records?page=1&limit=50",
            headers=self._headers(),
        )
        self.assertEqual(self_records.status_code, 200)
        self.assertEqual(self_records.json()["total"], 1)
        self.assertIsNone(self_records.json()["records"][0]["family_member_id"])

        family_records = self.client.get(
            "/api/v1/vault/records?page=1&limit=50",
            headers=member_headers,
        )
        self.assertEqual(family_records.status_code, 200)
        self.assertEqual(family_records.json()["total"], 1)
        self.assertEqual(family_records.json()["records"][0]["family_member_id"], member_id)

        family_dashboard = self.client.get("/api/v1/family/dashboard", headers=self._headers())
        self.assertEqual(family_dashboard.status_code, 200)
        self.assertEqual(len(family_dashboard.json()), 2)

        permissions = self.client.get(
            f"/api/v1/family/members/{member_id}/permissions",
            headers=self._headers(),
        )
        self.assertEqual(permissions.status_code, 200)
        self.assertGreaterEqual(len(permissions.json()), 1)

        updated_permissions = self.client.put(
            f"/api/v1/family/members/{member_id}/permissions",
            headers=self._headers(),
            json=[{"permission_key": "receive_sos", "is_enabled": False}],
        )
        self.assertEqual(updated_permissions.status_code, 200)

        bad_context = self.client.get(
            "/api/v1/vitals?limit=50&offset=0",
            headers={**self._headers(), "X-Profile-Id": "9999"},
        )
        self.assertEqual(bad_context.status_code, 404)

    def test_appointments_and_exercise_routes(self) -> None:
        appointment = self.client.post(
            "/api/v1/appointments",
            headers=self._headers(),
            json={
                "doctor_name": "Dr. Mehta",
                "specialty": "Endocrinology",
                "appointment_at": "2026-03-30T14:00:00Z",
                "location": "Max Hospital",
                "status": "scheduled",
            },
        )
        self.assertEqual(appointment.status_code, 201)
        appointment_id = appointment.json()["id"]

        listed = self.client.get("/api/v1/appointments", headers=self._headers())
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

        updated = self.client.put(
            f"/api/v1/appointments/{appointment_id}",
            headers=self._headers(),
            json={"status": "completed"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["status"], "completed")

        catalog = self.client.get("/api/v1/exercise/catalog", headers=self._headers())
        self.assertEqual(catalog.status_code, 200)
        self.assertGreaterEqual(len(catalog.json()), 1)

        logged = self.client.post(
            "/api/v1/exercise/logs",
            headers=self._headers(),
            json={
                "category": "walk_run",
                "activity_name": "Brisk Walking",
                "duration_minutes": 30,
                "distance_km": 2.5,
            },
        )
        self.assertEqual(logged.status_code, 201)

        summary = self.client.get("/api/v1/exercise/summary", headers=self._headers())
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["activities_done"], 1)

        history = self.client.get("/api/v1/exercise/history", headers=self._headers())
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()["weekly_calories"]), 7)

        recommendations = self.client.get("/api/v1/exercise/recommendations", headers=self._headers())
        self.assertEqual(recommendations.status_code, 200)
        self.assertGreaterEqual(len(recommendations.json()["items"]), 1)


if __name__ == "__main__":
    unittest.main()
