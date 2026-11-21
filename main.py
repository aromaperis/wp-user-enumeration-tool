import os
import sys
import json
import uuid
import httpx
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from src.registry import TOOL_MAP
from src.schema import TOOL_SCHEMAS
from src.state import DISCOVERED_USERS, reset_state

load_dotenv()

MODEL_NAME = os.getenv("LLM_MODEL")
API_KEY = os.getenv("GEMINI_API_KEY")
BASE_MODEL_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

client = OpenAI(
    base_url=BASE_MODEL_URL,
    api_key=API_KEY,
)
console = Console()


def run_enumeration(target_url: str):
    reset_state()
    task_id = str(uuid.uuid4())[:8]

    console.print(
        Panel.fit(
            f"[bold cyan]WordPress User Enumeration Audit[/bold cyan]\n"
            f"[dim]Task ID:[/dim] [white]{task_id}[/white]  |  "
            f"[dim]Target:[/dim] [bold yellow]{target_url}[/bold yellow]  |  "
            f"[dim]Model:[/dim] [green]{MODEL_NAME}[/green]",
            border_style="cyan",
        )
    )

    messages = [
        {
            "role": "system",
            "content": """You are a WordPress User Enumeration Audit Agent.
                You have three non-destructive auditing tools:
                1. `check_rest_api(base_url)`: Checks `/wp-json/wp/v2/users` and `/?rest_route=/wp/v2/users` for exposed users. Returns `status` ("vulnerable" or "blocked_or_not_found"), `users`, and `attempts`.
                2. `check_author_archives(base_url, start_id, end_id)`: Probes `/?author=<id>` across numeric IDs for HTTP 301/302 redirect leaks or HTML author class leaks. Returns `status`, `users`, and `attempts`.
                3. `check_error_leak(base_url, username_to_check)`: Compares `/wp-login.php` error text (`fake_user_error` vs. `checked_user_error`) using dummy credentials to verify if the login form leaks account existence.

                Reasoning Rules:
                1. Always call `check_rest_api(base_url)` first.
                2. Remember the REST API limitation: WordPress hides users who have zero published posts (such as contributors or subscribers), and security plugins may block the REST API (`status: "blocked_or_not_found"`).
                3. Next, determine which IDs to probe with `check_author_archives(base_url, start_id, end_id)`:
                - If `check_rest_api` returned users, do NOT re-check confirmed IDs. Instead, probe any missing IDs in the sequence AND the next sequential IDs after the highest returned ID (e.g., if IDs 1-3 are returned, probe `start_id=4, end_id=6`) to uncover unpublished users.
                - If `check_rest_api` returned `blocked_or_not_found`, probe `start_id=1, end_id=5`.
                4. Review `attempts` from `check_author_archives`. Stop probing if you see consecutive 404 responses or a 403/429 block note.
                5. Once at least one valid username is discovered (such as `admin`), call `check_error_leak(base_url, username_to_check)` once on that username. Compare `fake_user_error` and `checked_user_error` semantically to determine whether `/wp-login.php` reveals valid usernames via distinct error wording.
                6. Output a concise Audit Report listing:
                - **Discovered Users:** ID, Slug, and Discovery Vector
                - **Login Error Posture:** Whether `/wp-login.php` leaks usernames via error messages (quoting the observed error strings)
                - **Root Cause:** Crisp one-liner explanation of why the exposure occurs
                - **Remediation:** One or two short, actionable fixes"""
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

        with console.status(f"[bold cyan][Step {step}/{max_steps}] Agent reasoning...[/bold cyan]", spinner="dots"):
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=0.0,
            )

        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            console.print(f"[bold green]✔[/bold green] [dim][Task {task_id}] Completed in {step} step(s).[/dim]")
            return msg.content

        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)

            console.print(
                f"  [bold yellow]⚡ [Step {step}][/bold yellow] Calling [bold white]{fn_name}[/bold white]"
                f"[dim]({fn_args})[/dim]"
            )

            with console.status(f"[dim]Running {fn_name}...[/dim]", spinner="line"):
                if fn_name in TOOL_MAP:
                    tool_result = TOOL_MAP[fn_name](**fn_args)
                else:
                    tool_result = json.dumps({"error": f"Unknown tool: {fn_name}"})

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": fn_name,
                    "content": tool_result,
                }
            )

    return "Stopped: reached maximum step limit."


if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("[bold red]Usage:[/bold red] python main.py <target_url>")
        sys.exit(1)

    target_url = sys.argv[-1]

    try:
        with console.status(f"[dim]Checking connectivity to {target_url}...[/dim]", spinner="dots"):
            response = httpx.get(target_url, timeout=5, follow_redirects=True)
        console.print(f"[bold green][+][/bold green] Server is reachable ([cyan]HTTP {response.status_code}[/cyan]). Starting enumeration...\n")
    except httpx.ConnectError:
        console.print(
            Panel(
                f"[bold red]Connection Failed:[/bold red] Could not reach [yellow]{target_url}[/yellow].\n"
                "Make sure your Docker container is running: [cyan]docker compose up -d[/cyan]",
                border_style="red",
            )
        )
        sys.exit(1)
    except httpx.RequestError as e:
        console.print(f"[bold red][!] Failed to reach {target_url}:[/bold red] {e}")
        sys.exit(1)

    final_report = run_enumeration(target_url)

    console.print("\n")
    console.print(
        Panel(
            Markdown(final_report),
            title="[bold green]FINAL ENUMERATION REPORT[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )

    summary_table = Table(show_header=False, box=None)
    console.print(summary_table)