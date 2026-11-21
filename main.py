import os
from dotenv import load_dotenv
import argparse
import json
import uuid
from openai import OpenAI
from src.tools import TOOL_SCHEMAS, TOOL_MAP, DISCOVERED_USERS

load_dotenv()

MODEL_NAME = os.getenv("LLM_MODEL")
API_KEY=os.getenv("GEMINI_API_KEY")
BASE_MODEL_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

client = OpenAI(
    base_url=BASE_MODEL_URL,
    api_key=API_KEY
)

def run_enumeration(target_url: str):
    task_id = str(uuid.uuid4())[:8]
    print(f"[Task {task_id}] Starting enumeration on: {target_url}\n")

    messages = [
        {
            "role": "system",
            "content": (
                "You are a WordPress security auditing assistant. "
                "1. Start by calling check_rest_api. "
                "2. Then run check_author_archives (IDs 1 to 10) to cross-check or discover additional users. "
                "3. Once done, write a clear final report listing every discovered username, "
                "its user ID, and the exact evidence/endpoint that exposed it."
            )
        },
        {
            "role": "user",
            "content": f"Enumerate valid usernames on {target_url} and summarize the evidence."
        }
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
    parser = argparse.ArgumentParser(description="WordPress User Enumeration Agent")
    parser.add_argument("--url", required=True, help="Target WordPress base URL (e.g. http://localhost:8080)")
    args = parser.parse_args()

    final_report = run_enumeration(args.url)

    print("\n" + "=" * 50)
    print("FINAL ENUMERATION REPORT")
    print("=" * 50)
    print(final_report)
    print("\nStored User Count:", len(DISCOVERED_USERS))