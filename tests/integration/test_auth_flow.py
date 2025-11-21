"""Integration tests for authentication flow.

Tests the complete authentication flow with real database and HTTP endpoints:
1. User registration → Login → Access protected endpoint
2. Token refresh flow
3. Invalid credentials handling
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_complete_auth_flow(client: TestClient):
    """Test complete authentication flow: register → login → access protected endpoint."""
    # Step 1: Create a user
    create_response = client.post(
        "/api/v1/users",
        json={
            "email": "test@example.com",
            "name": "Test User",
            "password": "securepassword123",
        },
    )
    assert create_response.status_code == 201
    user_data = create_response.json()
    assert user_data["email"] == "test@example.com"
    user_id = user_data["id"]

    # Step 2: Login with credentials
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "securepassword123"},
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "bearer"
    access_token = token_data["access_token"]

    # Step 3: Access protected endpoint with token
    me_response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == "test@example.com"
    assert me_data["id"] == user_id


def test_login_with_wrong_password(client: TestClient):
    """Test login fails with incorrect password."""
    # Create a user first
    client.post(
        "/api/v1/users",
        json={
            "email": "test@example.com",
            "name": "Test User",
            "password": "correctpassword",
        },
    )

    # Try to login with wrong password
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "wrongpassword"},
    )
    assert login_response.status_code == 401
    assert "Invalid email or password" in login_response.json()["detail"]


def test_login_with_nonexistent_email(client: TestClient):
    """Test login fails with non-existent email."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "anypassword"},
    )
    assert login_response.status_code == 401


def test_access_protected_endpoint_without_token(client: TestClient):
    """Test accessing protected endpoint without token fails."""
    me_response = client.get("/api/v1/auth/me")
    print("hello", me_response.json())
    assert me_response.status_code == 401


def test_access_protected_endpoint_with_invalid_token(client: TestClient):
    """Test accessing protected endpoint with invalid token fails."""
    me_response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"}
    )
    assert me_response.status_code == 401


def test_token_refresh_flow(client: TestClient):
    """Test token refresh flow."""
    # Create user and login
    client.post(
        "/api/v1/users",
        json={
            "email": "test@example.com",
            "name": "Test User",
            "password": "securepassword123",
        },
    )

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "securepassword123"},
    )
    token_data = login_response.json()
    refresh_token = token_data["refresh_token"]
    old_access_token = token_data["access_token"]

    # Refresh the token
    refresh_response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200
    new_token_data = refresh_response.json()
    assert "access_token" in new_token_data
    assert "refresh_token" in new_token_data

    # New tokens should be different
    assert new_token_data["access_token"] != old_access_token
    assert new_token_data["refresh_token"] != refresh_token

    # New access token should work
    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_token_data['access_token']}"},
    )
    assert me_response.status_code == 200


def test_refresh_with_invalid_token(client: TestClient):
    """Test refresh fails with invalid token."""
    refresh_response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "invalid_refresh_token"}
    )
    assert refresh_response.status_code == 401
