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
    {
        "type": "function",
        "function": {
            "name": "check_author_archives",
            "description": (
                "Probe WordPress author archives (/?author=<id>) across a range of numeric IDs "
                "to discover usernames via 301/302 Location redirects—especially useful for finding "
                "unpublished users missed by the REST API."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "base_url": {"type": "string", "description": "Target base URL"},
                    "start_id": {"type": "integer", "description": "Starting user ID to probe (default 1)"},
                    "end_id": {"type": "integer", "description": "Ending user ID to probe (default 5)"},
                },
                "required": ["base_url"],
            },
        },
    }
]