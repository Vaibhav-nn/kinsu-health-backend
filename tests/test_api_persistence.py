"""Persistence tests for track/home APIs and Firebase user bootstrap flow."""

import asyncio
from datetime import datetime, timezone
import unittest

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.deps import get_current_user
from app.api.v1.auth import login
from app.api.v1.homescreen import (
    create_home_notification,
    get_home_preferences,
    homescreen_overview,
    list_home_notifications,
    update_home_theme_preference,
)
from app.api.v1.vitals import list_vitals, log_vital
from app.core.database import Base
from app.models.home import HomeNotification, HomePreference
from app.models.user import User
from app.models.vital import VitalLog
from app.schemas.health import VitalLogCreate
from app.schemas.homescreen import HomeNotificationCreate, HomeThemeUpdate


def _sqlite_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):  # type: ignore[no-redef]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


class TestApiPersistence(unittest.TestCase):
    """Validate DB persistence behavior of core route functions."""

    def setUp(self) -> None:
        self.engine = _sqlite_engine()
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = self.SessionLocal()
        self.decoded_token = {
            "uid": "firebase-user-1",
            "email": "user1@test.com",
            "name": "User One",
        }

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _get_user(self) -> User:
        return asyncio.run(get_current_user(decoded_token=self.decoded_token, db=self.db))

    def test_first_protected_call_bootstraps_user(self) -> None:
        user = self._get_user()
        self.assertEqual(user.firebase_uid, "firebase-user-1")

        vitals = asyncio.run(
            list_vitals(
                vital_type=None,
                start_date=None,
                end_date=None,
                limit=50,
                offset=0,
                user=user,
                db=self.db,
            )
        )
        self.assertEqual(vitals, [])

        row = self.db.query(User).filter(User.firebase_uid == "firebase-user-1").first()
        self.assertIsNotNone(row)
        self.assertEqual(row.email, "user1@test.com")

    def test_auth_login_upsert_behavior(self) -> None:
        first = asyncio.run(login(decoded_token=self.decoded_token, db=self.db))
        self.assertEqual(first.message, "User created successfully.")

        second = asyncio.run(login(decoded_token=self.decoded_token, db=self.db))
        self.assertEqual(second.message, "Login successful.")

    def test_track_and_home_persistence(self) -> None:
        user = self._get_user()

        created_vital = asyncio.run(
            log_vital(
                payload=VitalLogCreate(
                    vital_type="heart_rate",
                    value=73.0,
                    value_secondary=None,
                    unit="bpm",
                    recorded_at=datetime.now(timezone.utc),
                    notes="post-walk",
                ),
                user=user,
                db=self.db,
            )
        )
        self.assertEqual(created_vital.vital_type, "heart_rate")

        vitals = asyncio.run(
            list_vitals(
                vital_type=None,
                start_date=None,
                end_date=None,
                limit=50,
                offset=0,
                user=user,
                db=self.db,
            )
        )
        self.assertEqual(len(vitals), 1)
        self.assertEqual(vitals[0].unit, "bpm")

        updated_pref = asyncio.run(
            update_home_theme_preference(
                payload=HomeThemeUpdate(theme_mode="dark"),
                user=user,
                db=self.db,
            )
        )
        self.assertEqual(updated_pref.theme_mode, "dark")

        created_notification = asyncio.run(
            create_home_notification(
                payload=HomeNotificationCreate(
                    title="Medication reminder",
                    body="Take evening dose",
                    notification_type="medication",
                    action_route="/tracking/medications",
                ),
                user=user,
                db=self.db,
            )
        )
        self.assertEqual(created_notification.notification_type, "medication")

        notifications = asyncio.run(
            list_home_notifications(
                is_read=None,
                limit=50,
                offset=0,
                user=user,
                db=self.db,
            )
        )
        self.assertEqual(len(notifications), 1)
        self.assertFalse(notifications[0].is_read)

        pref = asyncio.run(get_home_preferences(user=user, db=self.db))
        self.assertEqual(pref.theme_mode, "dark")

        overview = asyncio.run(homescreen_overview(user=user, db=self.db))
        self.assertEqual(overview.top_bar.notification_unread_count, 1)

        self.assertEqual(self.db.query(VitalLog).count(), 1)
        self.assertEqual(self.db.query(HomePreference).count(), 1)
        self.assertEqual(self.db.query(HomeNotification).count(), 1)


if __name__ == "__main__":
    unittest.main()
