import json
from urllib.parse import urljoin
import httpx
from src.state import get_users_list, record_user

# --- TOOL 1: REST API Enumeration ---
def check_rest_api(base_url: str) -> str:
    base = base_url.rstrip("/") + "/"
    vulnerable_endpoints = ["wp-json/wp/v2/users", "?rest_route=/wp/v2/users"]
    attempts = []
    exposed_endpoints = []

    for endpoint in vulnerable_endpoints:
        url = urljoin(base, endpoint)

        try:
            response = httpx.get(url, timeout=10)
            status = response.status_code

            if status == 200:
                try:
                    users_data = response.json()
                except ValueError:
                    attempts.append({"endpoint": endpoint, "http_code": 200, "note": "Non-JSON response"})
                    continue

                if isinstance(users_data, list) and len(users_data) > 0:
                    exposed_endpoints.append(url)
                    attempts.append({"endpoint": endpoint, "http_code": 200, "note": "Exposed users"})
                    for user in users_data:
                        uid = user.get("id")
                        slug = user.get("slug") or user.get("name")
                        record_user(slug, f"/{endpoint}", user_id=uid)
                else:
                    attempts.append({"endpoint": endpoint, "http_code": 200, "note": "Empty user list"})

            elif status in (401, 403, 404):
                attempts.append({"endpoint": endpoint, "http_code": status, "note": "Blocked or route disabled"})

            else:
                attempts.append({"endpoint": endpoint, "http_code": status, "note": "Unexpected HTTP status"})

        except httpx.RequestError as e:
            attempts.append({"endpoint": endpoint, "error": str(e)})

    if exposed_endpoints:
        return json.dumps({
            "target": base_url.rstrip("/"),
            "status": "vulnerable",
            "techniques": ["rest-api"],
            "users": get_users_list(),
            "attempts": attempts,
        })

    return json.dumps({
        "target": base_url.rstrip("/"),
        "status": "blocked_or_not_found",
        "techniques": ["rest-api"],
        "users": get_users_list(),
        "attempts": attempts,
        "message": "Neither REST API endpoint exposed users. Try author archive enumeration next.",
    })