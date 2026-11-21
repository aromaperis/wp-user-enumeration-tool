import json
import re
from urllib.parse import urljoin
import httpx
from src.state import get_users_list, record_user

# --- TOOL 2: Author Archive Enumeration ---
def check_author_archives(base_url: str, start_id: int = 1, end_id: int = 5) -> str:
    base = base_url.rstrip("/") + "/"
    attempts = []
    newly_found = False

    with httpx.Client(follow_redirects=False, timeout=10.0) as client:
        for author_id in range(start_id, end_id + 1):
            endpoint = f"?author={author_id}"
            url = urljoin(base, endpoint)

            try:
                response = client.get(url)
                status = response.status_code

                if status in (301, 302):
                    location = response.headers.get("location", "")
                    match = re.search(r"/author/([^/]+)/?", location)
                    if match:
                        username = match.group(1)
                        record_user(username, f"/{endpoint}", user_id=author_id)
                        newly_found = True
                        attempts.append({"endpoint": endpoint, "http_code": status, "note": f"Exposed slug: {username}"})
                    else:
                        attempts.append({"endpoint": endpoint, "http_code": status, "note": f"Redirected without slug: {location}"})

                elif status == 404:
                    attempts.append({"endpoint": endpoint, "http_code": 404, "note": "No user for this ID"})

                elif status == 200:
                    matches = re.findall(r"author-([a-zA-Z0-9_-]+)", response.text)
                    found_username = None

                    for item in matches:
                        if not item.isdigit():
                            found_username = item
                            break

                    if found_username:
                        record_user(found_username, f"/{endpoint}", user_id=author_id)
                        newly_found = True
                        attempts.append({"endpoint": endpoint, "http_code": 200, "note": f"Found username in HTML: {found_username}"})
                    else:
                        attempts.append({"endpoint": endpoint, "http_code": 200, "note": "User exists (unpublished posts; no redirect)"})
                elif status in (403, 429):
                    attempts.append({"endpoint": endpoint, "http_code": status, "note": "Blocked or rate-limited; stopping probe"})
                    break

                else:
                    attempts.append({"endpoint": endpoint, "http_code": status, "note": "Unexpected HTTP status"})

            except httpx.RequestError as e:
                attempts.append({"endpoint": endpoint, "error": str(e)})

    if newly_found:
        return json.dumps({
            "target": base_url.rstrip("/"),
            "status": "vulnerable",
            "techniques": ["author_archive"],
            "users": get_users_list(),
            "attempts": attempts,
        })

    return json.dumps({
        "target": base_url.rstrip("/"),
        "status": "blocked_or_not_found",
        "techniques": ["author_archive"],
        "users": get_users_list(),
        "attempts": attempts,
        "message": "No new users exposed via author archives.",
    })
