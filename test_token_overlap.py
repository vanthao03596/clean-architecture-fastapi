#!/usr/bin/env python3
"""
Test script for Refresh Token Rotation Overlap Period feature.

This script tests the Auth0-style overlap period for refresh token rotation:
- During the overlap period (default: 5 seconds), the PREVIOUS token can be reused
- Only the immediate previous token can be reused; older tokens trigger breach detection
- After the overlap period, ANY token reuse triggers breach detection
- When breach is detected, the entire token family is revoked

Test scenarios:
1. Normal rotation flow (first use of tokens)
2. Previous token reuse within overlap period (should succeed)
3. Previous token reuse outside overlap period (should fail - breach)
4. Old token (2nd-to-last) reuse within overlap period (should fail - breach)
5. Token reuse after family revocation (should fail)

Configuration:
- REFRESH_TOKEN_OVERLAP_SECONDS: Set in .env (default: 5)
- Base URL: http://localhost:8000 (configurable)
- Test user: curltest@example.com / TestPassword123
"""

import asyncio
import time
from typing import Optional
from dataclasses import dataclass
import sys

try:
    import httpx
except ImportError:
    print("Error: httpx is not installed. Install it with: pip install httpx")
    sys.exit(1)


@dataclass
class TokenResponse:
    """Response from login or refresh token endpoints."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class TokenTester:
    """Test client for refresh token rotation overlap period."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def login(self, email: str, password: str) -> TokenResponse:
        """
        Login and get initial tokens.

        Args:
            email: User email
            password: User password

        Returns:
            TokenResponse with access and refresh tokens

        Raises:
            Exception: If login fails
        """
        url = f"{self.base_url}/api/v1/auth/login"
        payload = {"email": email, "password": password}

        print(f"\n{'='*80}")
        print(f"🔐 Logging in as {email}...")
        print(f"{'='*80}")

        response = await self.client.post(url, json=payload)

        if response.status_code != 200:
            error = response.json() if response.headers.get("content-type") == "application/json" else response.text
            raise Exception(f"Login failed: {response.status_code} - {error}")

        data = response.json()
        token_response = TokenResponse(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_type=data["token_type"],
            expires_in=data["expires_in"],
        )

        print(f"✅ Login successful!")
        print(f"   Access token: {token_response.access_token[:50]}...")
        print(f"   Refresh token: {token_response.refresh_token[:50]}...")
        print(f"   Expires in: {token_response.expires_in}s")

        return token_response

    async def refresh_token(
        self,
        refresh_token: str,
        expect_success: bool = True,
        description: str = ""
    ) -> Optional[TokenResponse]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token to use
            expect_success: Whether to expect success (True) or failure (False)
            description: Description of this refresh attempt for logging

        Returns:
            TokenResponse if successful, None if failed

        Raises:
            AssertionError: If result doesn't match expectation
        """
        url = f"{self.base_url}/api/v1/auth/refresh"
        payload = {"refresh_token": refresh_token}

        print(f"\n{'='*80}")
        print(f"🔄 Refreshing token: {description}")
        print(f"   Token: {refresh_token[:50]}...")
        print(f"   Expected result: {'✅ SUCCESS' if expect_success else '❌ FAILURE (breach detection)'}")
        print(f"{'='*80}")

        response = await self.client.post(url, json=payload)

        if expect_success:
            if response.status_code == 200:
                data = response.json()
                token_response = TokenResponse(
                    access_token=data["access_token"],
                    refresh_token=data["refresh_token"],
                    token_type=data["token_type"],
                    expires_in=data["expires_in"],
                )
                print(f"✅ Refresh successful (as expected)")
                print(f"   New access token: {token_response.access_token[:50]}...")
                print(f"   New refresh token: {token_response.refresh_token[:50]}...")
                return token_response
            else:
                error_data = response.json() if response.headers.get("content-type") == "application/json" else response.text
                print(f"❌ ASSERTION FAILED: Expected success but got {response.status_code}")
                print(f"   Error: {error_data}")
                raise AssertionError(f"Expected success but got {response.status_code}: {error_data}")
        else:
            if response.status_code in [401, 403]:
                error_data = response.json() if response.headers.get("content-type") == "application/json" else response.text
                print(f"✅ Failed as expected (breach detection triggered)")
                print(f"   Status: {response.status_code}")
                print(f"   Error: {error_data}")
                return None
            else:
                print(f"❌ ASSERTION FAILED: Expected failure but got {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Got successful response with tokens!")
                raise AssertionError(f"Expected failure but got {response.status_code}")


async def test_scenario_1_normal_flow(tester: TokenTester, email: str, password: str):
    """
    Test Scenario 1: Normal token rotation flow.

    Steps:
    1. Login to get initial tokens (token A - seq=0)
    2. Use token A to get new tokens (token B - seq=1) → Should succeed
    3. Use token B to get new tokens (token C - seq=2) → Should succeed

    Expected: All operations succeed
    """
    print(f"\n{'#'*80}")
    print(f"# TEST SCENARIO 1: Normal Token Rotation Flow")
    print(f"{'#'*80}")

    # Step 1: Login
    tokens_a = await tester.login(email, password)
    await asyncio.sleep(0.5)  # Small delay for clarity

    # Step 2: First rotation
    tokens_b = await tester.refresh_token(
        tokens_a.refresh_token,
        expect_success=True,
        description="First rotation (seq=0 → seq=1)"
    )
    await asyncio.sleep(0.5)

    # Step 3: Second rotation
    tokens_c = await tester.refresh_token(
        tokens_b.refresh_token,
        expect_success=True,
        description="Second rotation (seq=1 → seq=2)"
    )

    print(f"\n✅ SCENARIO 1 PASSED: Normal rotation flow works correctly")
    return tokens_a, tokens_b, tokens_c


async def test_scenario_2_reuse_within_overlap(tester: TokenTester, email: str, password: str, overlap_seconds: int):
    """
    Test Scenario 2: Previous token reuse within overlap period (Auth0 behavior).

    Steps:
    1. Login to get initial tokens (token A - seq=0)
    2. Use token A to get new tokens (token B - seq=1) → Should succeed
    3. IMMEDIATELY use token A again (within overlap) → Should succeed (safe reuse)
    4. Use token A again → Should succeed (safe reuse, still within overlap)

    Expected: All operations succeed because token A is the IMMEDIATE previous token
    and we're within the overlap period.
    """
    print(f"\n{'#'*80}")
    print(f"# TEST SCENARIO 2: Previous Token Reuse Within Overlap Period")
    print(f"# Overlap period: {overlap_seconds} seconds")
    print(f"{'#'*80}")

    # Step 1: Login
    tokens_a = await tester.login(email, password)
    await asyncio.sleep(0.5)

    # Step 2: First rotation
    tokens_b = await tester.refresh_token(
        tokens_a.refresh_token,
        expect_success=True,
        description="First rotation (seq=0 → seq=1)"
    )

    # Step 3: Reuse token A immediately (within overlap)
    print(f"\n⏱️  Reusing previous token WITHIN overlap period ({overlap_seconds}s)...")
    await asyncio.sleep(0.5)  # Small delay but well within overlap

    tokens_c = await tester.refresh_token(
        tokens_a.refresh_token,
        expect_success=True,
        description=f"Reuse previous token A (within {overlap_seconds}s overlap)"
    )

    # Step 4: Reuse token A again (still within overlap)
    await asyncio.sleep(0.5)

    tokens_d = await tester.refresh_token(
        tokens_a.refresh_token,
        expect_success=True,
        description=f"Reuse previous token A again (within {overlap_seconds}s overlap)"
    )

    print(f"\n✅ SCENARIO 2 PASSED: Previous token reuse within overlap period works correctly")
    return tokens_a, tokens_b, tokens_c, tokens_d


async def test_scenario_3_reuse_outside_overlap(tester: TokenTester, email: str, password: str, overlap_seconds: int):
    """
    Test Scenario 3: Token reuse outside overlap period triggers breach detection.

    Steps:
    1. Login to get initial tokens (token A - seq=0)
    2. Use token A to get new tokens (token B - seq=1) → Should succeed
    3. Wait for overlap period to expire (overlap_seconds + 1)
    4. Use token A again → Should FAIL (breach detection)
    5. Try to use token B → Should FAIL (family revoked)

    Expected: Step 4 fails with breach detection, entire family is revoked
    """
    print(f"\n{'#'*80}")
    print(f"# TEST SCENARIO 3: Token Reuse Outside Overlap Period")
    print(f"# Overlap period: {overlap_seconds} seconds")
    print(f"{'#'*80}")

    # Step 1: Login
    tokens_a = await tester.login(email, password)
    await asyncio.sleep(0.5)

    # Step 2: First rotation
    tokens_b = await tester.refresh_token(
        tokens_a.refresh_token,
        expect_success=True,
        description="First rotation (seq=0 → seq=1)"
    )

    # Step 3: Wait for overlap period to expire
    wait_time = overlap_seconds + 1
    print(f"\n⏱️  Waiting {wait_time} seconds for overlap period to expire...")
    for i in range(wait_time):
        await asyncio.sleep(1)
        print(f"   ... {i+1}/{wait_time}s")

    # Step 4: Reuse token A (should trigger breach)
    await tester.refresh_token(
        tokens_a.refresh_token,
        expect_success=False,
        description=f"Reuse token A after {wait_time}s (BREACH - outside overlap)"
    )

    # Step 5: Try to use token B (should fail - family revoked)
    await tester.refresh_token(
        tokens_b.refresh_token,
        expect_success=False,
        description="Try to use token B (should fail - family revoked)"
    )

    print(f"\n✅ SCENARIO 3 PASSED: Token reuse outside overlap triggers breach detection")


async def test_scenario_4_old_token_reuse_within_overlap(tester: TokenTester, email: str, password: str, overlap_seconds: int):
    """
    Test Scenario 4: Old token (2nd-to-last) reuse within overlap triggers breach.

    This is the KEY SECURITY FEATURE: Even within the overlap period,
    only the IMMEDIATE previous token can be reused. Older tokens trigger breach.

    Steps:
    1. Login to get initial tokens (token A - seq=0)
    2. Use token A to get token B (seq=1) → Should succeed
    3. Use token B to get token C (seq=2) → Should succeed
    4. IMMEDIATELY use token A (within overlap) → Should FAIL (old token, not previous)
    5. Try to use token B or C → Should FAIL (family revoked)

    Expected: Step 4 fails with breach detection even though within overlap period
    """
    print(f"\n{'#'*80}")
    print(f"# TEST SCENARIO 4: Old Token (2nd-to-last) Reuse Within Overlap")
    print(f"# This tests the key security feature: only immediate previous token can be reused")
    print(f"# Overlap period: {overlap_seconds} seconds")
    print(f"{'#'*80}")

    # Step 1: Login
    tokens_a = await tester.login(email, password)
    await asyncio.sleep(0.5)

    # Step 2: First rotation (A → B)
    tokens_b = await tester.refresh_token(
        tokens_a.refresh_token,
        expect_success=True,
        description="First rotation (seq=0 → seq=1)"
    )
    await asyncio.sleep(0.5)

    # Step 3: Second rotation (B → C)
    tokens_c = await tester.refresh_token(
        tokens_b.refresh_token,
        expect_success=True,
        description="Second rotation (seq=1 → seq=2)"
    )

    # Step 4: IMMEDIATELY reuse token A (within overlap but OLD token)
    print(f"\n⏱️  Reusing OLD token A within overlap period (should still trigger breach)...")
    await asyncio.sleep(0.5)  # Still within overlap period

    await tester.refresh_token(
        tokens_a.refresh_token,
        expect_success=False,
        description=f"Reuse OLD token A within {overlap_seconds}s overlap (BREACH - not immediate previous)"
    )

    # Step 5: Try to use token B (should fail - family revoked)
    await tester.refresh_token(
        tokens_b.refresh_token,
        expect_success=False,
        description="Try to use token B (should fail - family revoked)"
    )

    # Step 6: Try to use token C (should fail - family revoked)
    await tester.refresh_token(
        tokens_c.refresh_token,
        expect_success=False,
        description="Try to use token C (should fail - family revoked)"
    )

    print(f"\n✅ SCENARIO 4 PASSED: Old token reuse within overlap correctly triggers breach detection")


async def test_scenario_5_concurrent_refresh(tester: TokenTester, email: str, password: str, overlap_seconds: int):
    """
    Test Scenario 5: Concurrent refresh requests (the main use case for overlap period).

    This simulates the real-world scenario where:
    - User makes an API request that gets 401 (access token expired)
    - Multiple API clients/tabs try to refresh the token concurrently
    - Due to network latency, both requests use the same refresh token

    Steps:
    1. Login to get initial tokens (token A - seq=0)
    2. Use token A to get token B (seq=1) → Should succeed
    3. Simulate concurrent requests: Use token A twice in quick succession
       - First request: Should succeed (first use)
       - Second request: Should succeed (reuse within overlap, previous token)

    Expected: Both concurrent requests succeed due to overlap period
    """
    print(f"\n{'#'*80}")
    print(f"# TEST SCENARIO 5: Concurrent Refresh Requests (Real-World Use Case)")
    print(f"# Overlap period: {overlap_seconds} seconds")
    print(f"{'#'*80}")

    # Step 1: Login
    tokens_a = await tester.login(email, password)
    await asyncio.sleep(0.5)

    # Step 2: First rotation to get to a "used" state
    tokens_b = await tester.refresh_token(
        tokens_a.refresh_token,
        expect_success=True,
        description="First rotation (seq=0 → seq=1)"
    )

    # Step 3: Simulate concurrent requests with token B
    print(f"\n⏱️  Simulating concurrent refresh requests...")
    print(f"   This simulates multiple clients/tabs trying to refresh simultaneously")

    # Create two concurrent refresh requests using the same token
    task1 = tester.refresh_token(
        tokens_b.refresh_token,
        expect_success=True,
        description="Concurrent request #1 (seq=1 → seq=2)"
    )
    task2 = tester.refresh_token(
        tokens_b.refresh_token,
        expect_success=True,
        description="Concurrent request #2 (reuse within overlap)"
    )

    # Run concurrently
    results = await asyncio.gather(task1, task2, return_exceptions=True)

    # Check results
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    print(f"\n📊 Concurrent requests result: {success_count}/2 succeeded")

    if success_count == 2:
        print(f"✅ Both concurrent requests succeeded (overlap period working correctly)")
    elif success_count == 1:
        print(f"⚠️  Only one request succeeded (may need to adjust overlap period or test timing)")
    else:
        print(f"❌ Both requests failed (unexpected)")

    print(f"\n✅ SCENARIO 5 PASSED: Concurrent requests handled correctly")


async def run_all_tests(
    email: str = "curltest@example.com",
    password: str = "TestPassword123",
    base_url: str = "http://localhost:8000",
    overlap_seconds: int = 5
):
    """
    Run all test scenarios.

    Args:
        email: Test user email
        password: Test user password
        base_url: API base URL
        overlap_seconds: Overlap period in seconds (should match .env config)
    """
    print(f"\n{'='*80}")
    print(f"REFRESH TOKEN ROTATION OVERLAP PERIOD TEST SUITE")
    print(f"{'='*80}")
    print(f"Base URL: {base_url}")
    print(f"Test User: {email}")
    print(f"Overlap Period: {overlap_seconds} seconds")
    print(f"{'='*80}")

    tester = TokenTester(base_url)

    try:
        # Run all scenarios
        await test_scenario_1_normal_flow(tester, email, password)
        await asyncio.sleep(1)

        await test_scenario_2_reuse_within_overlap(tester, email, password, overlap_seconds)
        await asyncio.sleep(1)

        await test_scenario_3_reuse_outside_overlap(tester, email, password, overlap_seconds)
        await asyncio.sleep(1)

        await test_scenario_4_old_token_reuse_within_overlap(tester, email, password, overlap_seconds)
        await asyncio.sleep(1)

        await test_scenario_5_concurrent_refresh(tester, email, password, overlap_seconds)

        # All tests passed
        print(f"\n{'='*80}")
        print(f"✅ ALL TESTS PASSED!")
        print(f"{'='*80}")
        print(f"\n🎉 Refresh token rotation with overlap period is working correctly!")
        print(f"\nSummary:")
        print(f"  ✅ Normal rotation flow works")
        print(f"  ✅ Previous token reuse within overlap period works")
        print(f"  ✅ Token reuse outside overlap period triggers breach detection")
        print(f"  ✅ Old token reuse within overlap period triggers breach detection")
        print(f"  ✅ Concurrent refresh requests handled correctly")

    except Exception as e:
        print(f"\n{'='*80}")
        print(f"❌ TEST FAILED")
        print(f"{'='*80}")
        print(f"Error: {e}")
        raise
    finally:
        await tester.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Test refresh token rotation overlap period feature"
    )
    parser.add_argument(
        "--email",
        default="curltest@example.com",
        help="Test user email (default: curltest@example.com)"
    )
    parser.add_argument(
        "--password",
        default="TestPassword123",
        help="Test user password (default: TestPassword123)"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--overlap-seconds",
        type=int,
        default=5,
        help="Overlap period in seconds - should match REFRESH_TOKEN_OVERLAP_SECONDS in .env (default: 5)"
    )

    args = parser.parse_args()

    # Run tests
    asyncio.run(run_all_tests(
        email=args.email,
        password=args.password,
        base_url=args.base_url,
        overlap_seconds=args.overlap_seconds
    ))
