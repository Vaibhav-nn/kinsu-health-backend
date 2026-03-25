"""Unit tests for Firebase bearer token dependency behavior."""

import asyncio
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.api.deps import verify_firebase_token


class TestAuthDependencies(unittest.TestCase):
    def test_verify_firebase_token_parses_bearer_header(self) -> None:
        with patch(
            "app.api.deps.firebase_auth.verify_id_token",
            return_value={"uid": "abc123", "email": "demo@test.com"},
        ) as mock_verify:
            decoded = asyncio.run(
                verify_firebase_token(authorization="Bearer test-id-token-123")
            )

        mock_verify.assert_called_once_with("test-id-token-123")
        self.assertEqual(decoded["uid"], "abc123")

    def test_verify_firebase_token_rejects_non_bearer_headers(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(verify_firebase_token(authorization="Token something"))

        self.assertEqual(ctx.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
