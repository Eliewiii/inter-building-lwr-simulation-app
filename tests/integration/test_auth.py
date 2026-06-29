"""Test Authentication."""

from app.services.auth import get_current_user_id


def test_real_auth_rejects_missing_token(api_client, upload_url):
    """Ensure the real security layer drops a 403 or 401 when no token is present."""
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
    valid_auth_token,  # <-- Inject your newly created dynamic token fixture
):
    """Ensure the real encryption/signature processing logic validates a pristine token string."""
    if get_current_user_id in api_client.app.dependency_overrides:
        del api_client.app.dependency_overrides[get_current_user_id]

    with open(valid_zip_payload, "rb") as f:
        response = api_client.post(
            upload_url,
            files={"file": ("assets.zip", f, "application/zip")},
            data={"config_str": valid_config_form_string},
            # Attach the dynamic cryptographically signed token string
            headers={"Authorization": f"Bearer {valid_auth_token}"},
        )

    # The real verification layer matches the key/signature signature perfectly!
    assert response.status_code == 200
