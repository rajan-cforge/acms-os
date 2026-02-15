#!/usr/bin/env python3
"""Test Plaid API connection with sandbox credentials."""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

def test_plaid_connection():
    client_id = os.getenv("PLAID_CLIENT_ID")
    secret = os.getenv("PLAID_SECRET")
    env = os.getenv("PLAID_ENV", "sandbox")

    print("=" * 50)
    print("PLAID CONNECTION TEST")
    print("=" * 50)

    print(f"\nClient ID: {client_id[:8]}...{client_id[-4:]}" if client_id else "Client ID: NOT SET")
    print(f"Secret: {secret[:8]}...{secret[-4:]}" if secret else "Secret: NOT SET")
    print(f"Environment: {env}")

    if not client_id or not secret:
        print("\n❌ Missing credentials in .env file")
        return False

    # Test Plaid connection
    import plaid
    from plaid.api import plaid_api
    from plaid.model.link_token_create_request import LinkTokenCreateRequest
    from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
    from plaid.model.products import Products
    from plaid.model.country_code import CountryCode

    # Configure client
    host_map = {
        "sandbox": plaid.Environment.Sandbox,
        "development": plaid.Environment.Sandbox,  # Use sandbox for dev
        "production": plaid.Environment.Production,
    }

    configuration = plaid.Configuration(
        host=host_map.get(env, plaid.Environment.Sandbox),
        api_key={
            "clientId": client_id,
            "secret": secret,
        }
    )

    api_client = plaid.ApiClient(configuration)
    client = plaid_api.PlaidApi(api_client)

    # Test 1: Create a link token
    print("\n--- Test 1: Create Link Token ---")
    request = LinkTokenCreateRequest(
        user=LinkTokenCreateRequestUser(client_user_id="test_user"),
        client_name="ACMS Financial",
        products=[Products("investments")],
        country_codes=[CountryCode("US")],
        language="en",
    )

    try:
        response = client.link_token_create(request)
        print(f"✅ Link Token Created")
        print(f"   Token: {response.link_token[:50]}...")
        print(f"   Expires: {response.expiration}")
        print(f"   Request ID: {response.request_id}")

        # Save link token for manual testing
        print(f"\n📋 Full Link Token (for testing in browser):")
        print(f"   {response.link_token}")

        return True

    except plaid.ApiException as e:
        print(f"❌ API Error:")
        print(f"   Status: {e.status}")
        print(f"   Body: {e.body}")
        return False


if __name__ == "__main__":
    success = test_plaid_connection()
    print("\n" + "=" * 50)
    if success:
        print("✅ PLAID CONNECTION TEST PASSED")
    else:
        print("❌ PLAID CONNECTION TEST FAILED")
    print("=" * 50)
    sys.exit(0 if success else 1)
