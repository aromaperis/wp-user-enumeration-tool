# state.py
DISCOVERED_USERS: dict[str, dict] = {}

def record_user(username: str, evidence: str, user_id: int | None = None) -> None:
    """Store unique usernames and merge evidence paths across tools."""
    if not username:
        return

    if username not in DISCOVERED_USERS:
        DISCOVERED_USERS[username] = {
            "id": user_id,
            "username": username,
            "evidence": [],
        }

    if evidence not in DISCOVERED_USERS[username]["evidence"]:
        DISCOVERED_USERS[username]["evidence"].append(evidence)

    if user_id is not None and DISCOVERED_USERS[username]["id"] is None:
        DISCOVERED_USERS[username]["id"] = user_id


def get_users_list() -> list[dict]:
    """Return discovered users as a flat list of objects."""
    return list(DISCOVERED_USERS.values())

def reset_state() -> None:
    DISCOVERED_USERS.clear()