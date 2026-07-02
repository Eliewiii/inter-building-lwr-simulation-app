"""Authentication middleware interception and token validation boundaries."""

import pytest

from app.services.auth import get_current_user_id

pytestmark = [pytest.mark.integration]


def test_real_auth_rejects_missing_token(api_client, upload_url):
    """Ensure the real security layer drops a 403 or 401 when no token is present.

    Asserts that the framework-level security dependency intercepts incoming
    requests before business route entry if authorization metadata headers are missing.

    Args:
        api_client (TestClient): Active application runtime client instance.
        upload_url (str): Endpoint routing address under evaluation.
    """
    # 1. TEMPORARILY UNMOCK: Clear the override for this specific test run
    if get_current_user_id in api_client.app.dependency_overrides:
        del api_client.app.dependency_overrides[get_current_user_id]

    # 2. Make a request completely naked without an Authorization header
    response = api_client.post(upload_url, data={"config_str": "{}"})

    # 3. Assert that the real security system blocks the request
    assert response.status_code in [401, 403]


def test_real_auth_accepts_valid_signed_token(
    api_client,
    valid_zip_payload,
    valid_config_form_string,
    upload_url,
    valid_auth_token,
):
    """Ensure the encryption processing logic validates a pristine token string.

    Verifies that real cryptographic signature decoding succeeds when supplied
    with matching environmental variables and proper bearer schema headers.

    Args:
        api_client (TestClient): Active application runtime client instance.
        valid_zip_payload (str): File system path pointing to a verifiable ZIP archive.
        valid_config_form_string (str): Serialized mock parameters configuration data.
        upload_url (str): Endpoint routing address under evaluation.
        valid_auth_token (str): Cryptographically signed JSON Web Token string payload.
    """
    # 1. TEMPORARILY UNMOCK: Clear the override for this specific test run
    if get_current_user_id in api_client.app.dependency_overrides:
        del api_client.app.dependency_overrides[get_current_user_id]

    # 2. Open structural tracking files within localized context boundaries
    with open(valid_zip_payload, "rb") as f:
        # 3. Dispatch multipart request attaching the dynamic cryptographic authorization signature
        response = api_client.post(
            upload_url,
            files={"file": ("assets.zip", f, "application/zip")},
            data={"config_str": valid_config_form_string},
            headers={"Authorization": f"Bearer {valid_auth_token}"},
        )

    # 4. Assert full validation traversal and operational endpoint resolution
    assert response.status_code == 200
