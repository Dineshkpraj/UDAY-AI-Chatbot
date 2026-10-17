"""Deployment-focused API tests; run with python -m unittest discover -s tests."""

import os
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

import httpx

import api
from database import get_engine, get_session_factory, initialize_database


class DeploymentApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="uday-test-")
        os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(self.temp_dir.name, "test.db").replace("\\", "/")
        os.environ["JWT_SECRET_KEY"] = "test-only-secret-" + ("x" * 48)
        os.environ.pop("UDAY_REQUIRE_DATABASE", None)
        for cached in (get_engine, get_session_factory, initialize_database, api.get_user_manager):
            cached.cache_clear()
        initialize_database()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url="http://test")
        self.email = "person@example.com"
        self.password = "Strong-test-password-987"

    async def asyncTearDown(self):
        await self.client.aclose()
        try:
            get_engine().dispose()
        except Exception:
            pass
        for cached in (get_engine, get_session_factory, initialize_database, api.get_user_manager):
            cached.cache_clear()
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("JWT_SECRET_KEY", None)
        self.temp_dir.cleanup()

    async def register(self, email=None):
        return await self.client.post("/users", json={
            "email": email or self.email, "name": "Test Person", "age": 30,
            "gender": "Other", "profession": "Other", "focus_area": "stress",
            "password": self.password, "privacy_consent": True,
        })

    async def token(self, email=None):
        response = await self.client.post("/token", data={"username": email or self.email, "password": self.password})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["access_token"]

    async def test_registration_validation_and_jwt_lifetime(self):
        self.assertEqual((await self.register()).status_code, 201)
        token = await self.token()
        payload = api.jwt.decode(token, os.environ["JWT_SECRET_KEY"], algorithms=["HS256"])
        self.assertEqual(payload["exp"] - payload["iat"], 900)
        self.assertEqual((await self.client.post("/users", json={"email": "minor@example.com", "name": "Minor", "age": 17,
                         "gender": "Other", "profession": "Other", "focus_area": "", "password": self.password,
                         "privacy_consent": True})).status_code, 422)
        self.assertEqual((await self.client.post("/users", json={"email": "no-consent@example.com", "name": "No", "age": 30,
                         "gender": "Other", "profession": "Other", "focus_area": "x", "password": self.password,
                         "privacy_consent": False})).status_code, 422)

    async def test_screening_state_persists_between_requests(self):
        await self.register()
        headers = {"Authorization": "Bearer " + await self.token()}
        first = await self.client.post("/chat", headers=headers, json={"message": "start screening"})
        self.assertEqual(first.status_code, 200)
        self.assertIn("Question 1", first.json()["response"])
        second = await self.client.post("/chat", headers=headers, json={"message": "2"})
        self.assertEqual(second.status_code, 200)
        self.assertIn("Question 2", second.json()["response"])

    async def test_gemini_failure_is_not_reported_as_a_successful_chat(self):
        await self.register()
        headers = {"Authorization": "Bearer " + await self.token()}
        with patch("api.get_api_key", return_value="test-key"), patch("api.Chatbot", side_effect=RuntimeError("provider unavailable")):
            response = await self.client.post("/chat", headers=headers, json={"message": "I had a difficult day."})
        self.assertEqual(response.status_code, 503)
        self.assertIn("temporarily unavailable", response.json()["detail"])

    async def test_privacy_export_memory_and_account_deletion(self):
        await self.register()
        headers = {"Authorization": "Bearer " + await self.token()}
        self.assertEqual((await self.client.put("/memory", headers=headers, json={"facts": ["likes quiet walks"]})).status_code, 200)
        exported = (await self.client.get("/export", headers=headers)).json()
        self.assertEqual(exported["memories"], ["likes quiet walks"])
        self.assertNotIn("password_hash", exported["profile"])
        self.assertEqual((await self.client.delete("/account", headers=headers)).status_code, 204)
        self.assertEqual((await self.client.get("/export", headers=headers)).status_code, 401)

    async def test_rate_limit_is_database_backed(self):
        now = datetime.now(timezone.utc)
        first = api.bump_rate_limit("test-bucket", now)
        second = api.bump_rate_limit("test-bucket", now)
        self.assertEqual((first, second), (1, 2))


if __name__ == "__main__":
    unittest.main()
