"""Tests for local/demo auth bypass mode."""

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app


class TestAuthBypassMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.SessionLocal = sessionmaker(bind=cls.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(cls.engine)

        cls._orig_auth_bypass = settings.AUTH_BYPASS
        cls._orig_auth_bypass_uid = settings.AUTH_BYPASS_UID
        cls._orig_auth_bypass_email = settings.AUTH_BYPASS_EMAIL
        cls._orig_auth_bypass_name = settings.AUTH_BYPASS_NAME

        settings.AUTH_BYPASS = True
        settings.AUTH_BYPASS_UID = "demo-test-user"
        settings.AUTH_BYPASS_EMAIL = "demo-test@kinsu.local"
        settings.AUTH_BYPASS_NAME = "Demo Test User"

        def override_get_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

        settings.AUTH_BYPASS = cls._orig_auth_bypass
        settings.AUTH_BYPASS_UID = cls._orig_auth_bypass_uid
        settings.AUTH_BYPASS_EMAIL = cls._orig_auth_bypass_email
        settings.AUTH_BYPASS_NAME = cls._orig_auth_bypass_name

    def setUp(self) -> None:
        with self.SessionLocal() as db:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            db.commit()

    def test_auth_login_works_without_authorization_header_in_bypass_mode(self) -> None:
        response = self.client.post("/api/v1/auth/login")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["user"]["firebase_uid"], "demo-test-user")
        self.assertEqual(body["user"]["email"], "demo-test@kinsu.local")

    def test_protected_route_works_without_authorization_header_in_bypass_mode(self) -> None:
        self.client.post("/api/v1/auth/login")
        response = self.client.get("/api/v1/vitals?limit=50&offset=0")
        self.assertEqual(response.status_code, 200)

