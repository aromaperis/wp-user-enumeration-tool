import os
from dotenv import load_dotenv
import sys
import json
import uuid
import httpx
from openai import OpenAI
from src.registry import TOOL_MAP
from src.schema import TOOL_SCHEMAS
from src.state import DISCOVERED_USERS, reset_state

load_dotenv()

MODEL_NAME = os.getenv("LLM_MODEL")
API_KEY=os.getenv("GEMINI_API_KEY")
BASE_MODEL_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

client = OpenAI(
    base_url=BASE_MODEL_URL,
    api_key=API_KEY
)

def run_enumeration(target_url: str):
    reset_state()
    task_id = str(uuid.uuid4())[:8]
    print(f"[Task {task_id}] Starting enumeration on: {target_url}\n")

    messages = [
        {
            "role": "system",
            "content": """You are a WordPress User Enumeration Audit Agent.
                You have two tools:
                1. `check_rest_api(base_url)`: Fetches published users from /wp-json/wp/v2/users.
                2. `check_author_archives(base_url, start_id, end_id)`: Probes /?author=<id> across a range of numeric IDs to detect username exposure via HTTP redirects.

                Reasoning Rules:
                1. Always call `check_rest_api` first to discover exposed authors.
                2. Remember the REST API limitation: WordPress hides users who have zero published posts (such as contributors or subscribers).
                3. Analyze the IDs returned by the REST API. Do NOT re-check IDs already confirmed by the REST API. Instead, call `check_author_archives` with `start_id` and `end_id` covering any missing IDs in the sequence AND the next sequential IDs after the highest returned ID (e.g., if IDs 1-3 are returned, probe `start_id=4, end_id=6`) to uncover unpublished users.
                4. Review the `newly_found` usernames, `location` headers, and `attempts` returned by `check_author_archives`. Stop probing once you hit 404 responses on consecutive IDs.
                5. Output a concise Audit Report listing:
                - Discovered Users (ID, Slug, Discovery Vector)
                - Give crisp one liner explanation to the reason of vulnerability.
                - Remediation Steps one or two in short""",
        },
        {
            "role": "user",
            "content": f"Audit {target_url} for WordPress user enumeration exposure and summarize the evidence.",
        },
    ]

    step = 0
    max_steps = 5

    while step < max_steps:
        step += 1

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.0
        )

        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            print(f"\n[Task {task_id}] Completed in {step} step(s).")
            return msg.content

        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)

            print(f"[Task {task_id} | Step {step}] Running {fn_name}({fn_args})")

            if fn_name in TOOL_MAP:
                tool_result = TOOL_MAP[fn_name](**fn_args)
            else:
                tool_result = json.dumps({"error": f"Unknown tool: {fn_name}"})

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": fn_name,
                "content": tool_result
            })

    return "Stopped: reached maximum step limit."


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <target_url>")
        sys.exit(1)

    target_url = sys.argv[-1]

    try:
        response = httpx.get(target_url, timeout=5, follow_redirects=True)
        print(f"[+] Server is up ({response.status_code}). Starting enumeration...")
    except httpx.ConnectError:
        print(f"[!] Could not connect to {target_url}. Please make sure your Docker container or server is running (e.g., `docker compose up -d`).")
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"[!] Failed to reach {target_url}: {e}")
        sys.exit(1)

    final_report = run_enumeration(target_url)

    print("\n" + "=" * 50)
    print("FINAL ENUMERATION REPORT")
    print("=" * 50)
    print(final_report)
    print("\nStored User Count:", len(DISCOVERED_USERS))