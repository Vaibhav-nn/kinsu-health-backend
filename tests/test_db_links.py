"""Database link tests for ORM relationships, FKs, and constraints."""

from datetime import date, datetime, time, timezone
import unittest

from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import (
    ChronicSymptom,
    HomeNotification,
    HomePreference,
    IllnessDetail,
    IllnessEpisode,
    Medication,
    Reminder,
    User,
    VitalLog,
)


def _sqlite_engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):  # type: ignore[no-redef]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


class TestDatabaseLinks(unittest.TestCase):
    """Ensure DB links are correctly enforced across entities."""

    def setUp(self) -> None:
        self.engine = _sqlite_engine()
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.session = self.Session()

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _create_user(self) -> User:
        user = User(firebase_uid="uid-1", email="test@example.com", display_name="Test User")
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def test_user_links_and_cascade_delete(self) -> None:
        user = self._create_user()

        vital = VitalLog(
            user_id=user.id,
            vital_type="heart_rate",
            value=72.0,
            value_secondary=None,
            unit="bpm",
            recorded_at=datetime.now(timezone.utc),
            notes="resting",
        )
        symptom = ChronicSymptom(
            user_id=user.id,
            symptom_name="migraine",
            severity=4,
            frequency="weekly",
            body_area="head",
            triggers="stress",
            first_noticed=date(2026, 1, 10),
            is_active=True,
            notes="mild",
        )
        episode = IllnessEpisode(
            user_id=user.id,
            title="Flu",
            description="seasonal flu",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 7),
            status="recovered",
        )
        medication = Medication(
            user_id=user.id,
            name="Metformin",
            dosage="500mg",
            frequency="twice_daily",
            route="oral",
            start_date=date(2026, 1, 1),
            end_date=None,
            prescribing_doctor="Dr. Reddy",
            is_active=True,
            notes="after meals",
        )
        reminder = Reminder(
            user_id=user.id,
            title="Morning dose",
            reminder_type="medication",
            linked_medication_id=None,
            scheduled_time=time(8, 0),
            recurrence="daily",
            is_enabled=True,
            notes=None,
        )
        pref = HomePreference(user_id=user.id, theme_mode="system")
        notification = HomeNotification(
            user_id=user.id,
            notification_type="general",
            title="Welcome",
            body="Profile setup complete",
            action_route="/home",
            is_read=False,
            read_at=None,
        )

        self.session.add_all([vital, symptom, episode, medication, reminder, pref, notification])
        self.session.commit()

        detail = IllnessDetail(
            episode_id=episode.id,
            detail_type="note",
            content="Recovered after rest",
            recorded_at=datetime.now(timezone.utc),
        )
        self.session.add(detail)
        self.session.commit()

        self.assertEqual(len(user.vital_logs), 1)
        self.assertEqual(len(user.chronic_symptoms), 1)
        self.assertEqual(len(user.illness_episodes), 1)
        self.assertEqual(len(user.medications), 1)
        self.assertEqual(len(user.reminders), 1)
        self.assertIsNotNone(user.home_preference)
        self.assertEqual(len(user.home_notifications), 1)

        self.session.delete(user)
        self.session.commit()

        self.assertEqual(self.session.query(User).count(), 0)
        self.assertEqual(self.session.query(VitalLog).count(), 0)
        self.assertEqual(self.session.query(ChronicSymptom).count(), 0)
        self.assertEqual(self.session.query(IllnessEpisode).count(), 0)
        self.assertEqual(self.session.query(IllnessDetail).count(), 0)
        self.assertEqual(self.session.query(Medication).count(), 0)
        self.assertEqual(self.session.query(Reminder).count(), 0)
        self.assertEqual(self.session.query(HomePreference).count(), 0)
        self.assertEqual(self.session.query(HomeNotification).count(), 0)

    def test_medication_delete_sets_reminder_link_to_null(self) -> None:
        user = self._create_user()

        medication = Medication(
            user_id=user.id,
            name="Amlodipine",
            dosage="5mg",
            frequency="once_daily",
            route="oral",
            start_date=date(2026, 1, 1),
            end_date=None,
            prescribing_doctor="Dr. Kapoor",
            is_active=True,
            notes=None,
        )
        self.session.add(medication)
        self.session.commit()
        self.session.refresh(medication)

        reminder = Reminder(
            user_id=user.id,
            title="BP medicine",
            reminder_type="medication",
            linked_medication_id=medication.id,
            scheduled_time=time(9, 0),
            recurrence="daily",
            is_enabled=True,
            notes=None,
        )
        self.session.add(reminder)
        self.session.commit()
        self.session.refresh(reminder)

        self.assertEqual(reminder.linked_medication_id, medication.id)

        self.session.delete(medication)
        self.session.commit()
        self.session.refresh(reminder)

        self.assertIsNone(reminder.linked_medication_id)

    def test_theme_mode_constraint(self) -> None:
        user = self._create_user()

        self.session.add(HomePreference(user_id=user.id, theme_mode="unknown"))
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_symptom_severity_constraint(self) -> None:
        user = self._create_user()

        self.session.add(
            ChronicSymptom(
                user_id=user.id,
                symptom_name="joint_pain",
                severity=11,
                frequency="daily",
                body_area="knee",
                triggers="running",
                first_noticed=date(2026, 1, 15),
                is_active=True,
                notes=None,
            )
        )
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_episode_date_range_constraint(self) -> None:
        user = self._create_user()

        self.session.add(
            IllnessEpisode(
                user_id=user.id,
                title="Viral fever",
                description=None,
                start_date=date(2026, 2, 10),
                end_date=date(2026, 2, 1),
                status="active",
            )
        )
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()


if __name__ == "__main__":
    unittest.main()
