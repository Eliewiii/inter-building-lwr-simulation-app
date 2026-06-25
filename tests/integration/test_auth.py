# """Test Authentication."""

# from app.services.auth import get_current_user_id


# def test_real_auth_rejects_missing_token(api_client):
#     """Ensure the real security layer drops a 403 or 401 when no token is present."""
#     # 1. TEMPORARILY UNMOCK: Clear the override for this specific test run
#     if get_current_user_id in api_client.app.dependency_overrides:
#         del api_client.app.dependency_overrides[get_current_user_id]

#     upload_url = api_client.app.url_path_for("initialize_simulation")

#     # 2. Make a request completely naked without an Authorization header
#     response = api_client.post(upload_url, data={"config_str": "{}"})

#     # 3. Assert that the real security system blocks the request
#     assert response.status_code in [401, 403]


# def test_real_auth_accepts_valid_signed_token(
#     api_client, valid_zip_payload, valid_config_form_string
# ):
#     """Ensure the real encryption/signature processing logic validates a pristine token string."""
#     # Unmock for this test block
#     if get_current_user_id in api_client.app.dependency_overrides:
#         del api_client.app.dependency_overrides[get_current_user_id]

#     upload_url = api_client.app.url_path_for("initialize_simulation")

#     # Generate a realistic mock signed token using your app's security utility functions
#     # (e.g., app.core.security.create_access_token)
#     fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyX2Rldl80MiJ9..."

#     with open(valid_zip_payload, "rb") as f:
#         response = api_client.post(
#             upload_url,
#             files={"file": ("assets.zip", f, "application/zip")},
#             data={"config_str": valid_config_form_string},
#             # Send the real header your production code expects!
#             headers={"Authorization": f"Bearer {fake_token}"},
#         )

#     # If encryption & signatures match, it unlocks the path!
#     assert response.status_code == 200
