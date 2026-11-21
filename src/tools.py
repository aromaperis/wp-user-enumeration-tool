import json
from urllib.parse import urljoin
import httpx

# Stores discovered users: { "username": {"id": 1, "sources": ["REST API"]} }
DISCOVERED_USERS = {}

def _record_user(username: str, source: str, user_id=None):
    """Helper to store unique usernames and track which method found them."""
    if not username:
        return
    if username not in DISCOVERED_USERS:
        DISCOVERED_USERS[username] = {"id": user_id, "sources": []}
    if source not in DISCOVERED_USERS[username]["sources"]:
        DISCOVERED_USERS[username]["sources"].append(source)
    if user_id and not DISCOVERED_USERS[username]["id"]:
        DISCOVERED_USERS[username]["id"] = user_id


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
                users_data = response.json()

                if isinstance(users_data, list) and len(users_data) > 0:
                    exposed_endpoints.append(url)
                    attempts.append({"endpoint": endpoint, "http_code": 200, "note": "Exposed users"})
                    for user in users_data:
                        uid = user.get("id")
                        slug = user.get("slug") or user.get("name")
                        _record_user(slug, "REST API", user_id=uid)
                else:
                    attempts.append({"endpoint": endpoint, "http_code": 200, "note": "Empty user list"})

            elif status in (401, 403, 404):
                attempts.append({"endpoint": endpoint, "http_code": status, "note": "Blocked or route disabled"})

            else:
                attempts.append({"endpoint": endpoint, "http_code": status, "note": "Unexpected HTTP status"})

        except httpx.exceptions.RequestException as e:
            attempts.append({"endpoint": endpoint, "error": str(e)})

    if exposed_endpoints:
        return json.dumps({
            "status": "vulnerable",
            "exposed_endpoints": exposed_endpoints,
            "discovered_users": DISCOVERED_USERS,
            "total_unique_users": len(DISCOVERED_USERS),
            "attempts": attempts
        })

    return json.dumps({
        "status": "blocked_or_not_found",
        "attempts": attempts,
        "message": "Neither REST API endpoint exposed users. Try author archive enumeration next."
    })

# --- TOOL SCHEMAS ---
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "check_rest_api",
            "description": (
                "Check WordPress REST API (/wp-json/wp/v2/users) for exposed usernames. "
                "Always call this FIRST."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "base_url": {"type": "string", "description": "Target base URL"}
                },
                "required": ["base_url"]
            }
        }
    },
]

TOOL_MAP = {
    "check_rest_api": check_rest_api,
}