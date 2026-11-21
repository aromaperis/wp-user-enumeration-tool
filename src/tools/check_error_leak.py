import json
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup

def check_error_leak(base_url: str, username_to_check: str = "admin") -> str:
    base = base_url.rstrip("/") + "/"
    url = urljoin(base, "wp-login.php")

    with httpx.Client(timeout=8.0, follow_redirects=True) as client:
        try:
            client.get(url)

            fake_response = client.post(
                url,
                data={"log": "trying_to_get_in", "pwd": "jfsiuhrubg", "testcookie": "1"},
            )
            real_response = client.post(
                url,
                data={"log": username_to_check, "pwd": "jfsiuhrubg", "testcookie": "1"},
            )

            return json.dumps({
                "tool": "check_error_leak",
                "url": url,
                "username_checked": username_to_check,
                "fake_user_error": get_error_text(fake_response.text),
                "checked_user_error": get_error_text(real_response.text),
            })

        except Exception as e:
            return json.dumps({
                "tool": "check_error_leak",
                "url": url,
                "error": f"Could not check login page: {str(e)}",
            })

def get_error_text(html: str) -> str:
    """Extracts plain text from WordPress's <div id="login_error"> box."""
    soup = BeautifulSoup(html, "html.parser")
    error_box = soup.find("div", id="login_error")
    if not error_box:
        return ""
    return " ".join(error_box.get_text().split())