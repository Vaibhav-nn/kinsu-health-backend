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

        trends = self.client.get(
            "/api/v1/vitals/trends?vital_type=heart_rate",
            headers=self._headers(),
        )
        self.assertEqual(trends.status_code, 200)
        self.assertEqual(trends.json()["count"], 1)

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

        bad_context = self.client.get(
            "/api/v1/vitals?limit=50&offset=0",
            headers={**self._headers(), "X-Profile-Id": "9999"},
        )
        self.assertEqual(bad_context.status_code, 404)


if __name__ == "__main__":
    unittest.main()
