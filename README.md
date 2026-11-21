# AI-Driven WordPress User Enumeration Tool

## Description

WordPress has several vulnerabilities due to its default structure and configurations. User enumeration is one such vulnerability where publicly accessible endpoints and URL structures can expose metadata about registered users.

This tool automates the process of finding such vulnerabilities using different enumeration techniques, coordinated by a custom AI agent.

## Enumeration Techniques

1. **REST API:** Checks whether the WordPress users endpoint (`/wp-json/wp/v2/users`) exposes user metadata, including usernames of users who have published posts.

2. **Author Archive:** Uses WordPress author archive URLs to discover usernames. It can also help identify users who haven't published any posts.

3. **Login Response Analysis:** Checks differences in login error responses to identify whether a username is valid.

## Why an AI Agent?

The main reason for using an AI agent is its reasoning capability.

Responses from WordPress are not always predictable or hardcoded. The agent can interpret different responses, decide which tool to call next, and change the execution order based on the findings.

For example, if one technique fails, the agent can decide to try another technique instead of following a fixed sequence.

A custom agent is built using Python, with `state.py` maintaining the assessment state and tracking discovered users across tool executions.

## Architecture

* **Target Lab:** Docker Compose runs WordPress, MariaDB, and a WP-CLI container that pre-seeds test accounts.
* **Entrypoint:** `main.py` checks server reachability and passes the target URL to the custom agent loop.
* **Tool Execution:** The LLM invokes `check_rest_api`, `check_author_archives`, or `check_error_leak` as needed.
* **State & Observation:** Tools log discovered users in `src/state.py` (`DISCOVERED_USERS`) and return JSON evidence to the agent.
* **Agent Loop & Report:** The LLM iteratively selects follow-up checks until complete, then renders a Markdown report via `rich`.

## Tech Stack

- Python
- Google Gemini 3.5 Flash-Lite
- Docker & Docker Compose
- WordPress
- MariaDB
- Rich (Terminal UI)

## Prerequisites
- **Python 3.12** (tested on 3.12)
- Docker & Docker Compose

## Setup

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Configure environment variables**

Copy the example file:

```bash
cp .env.example .env
```

Add your Gemini API key and other required configurations to `.env`.

**3. Start the WordPress environment**

```bash
docker compose up -d
```

This starts WordPress, MariaDB and WP-CLI. WP-CLI also pre-seeds users and posts to provide test cases.

**4. Run the tool**

```bash
python main.py --url http://localhost:8081
```

The agent starts the enumeration process and generates a final report.

## Sample Output

The agent returns a structured JSON report containing the target, vulnerability status, discovered users, evidence and enumeration attempts.

**Schema:**

```json
{
  "target": "string",
  "status": "vulnerable | not_vulnerable",
  "techniques": ["string"],
  "users": [
    {
      "id": "integer",
      "username": "string",
      "evidence": ["string"]
    }
  ],
  "attempts": [
    {
      "endpoint": "string",
      "http_code": "integer",
      "note": "string"
    }
  ]
}
```

**Example:**

```json
{
  "target": "http://localhost:8081",
  "status": "vulnerable",
  "techniques": ["rest-api", "author_archive"],
  "users": [
    {
      "id": 1,
      "username": "admin",
      "evidence": ["/wp-json/wp/v2/users"]
    },
    {
      "id": 4,
      "username": "contributor_sam",
      "evidence": ["/?author=4"]
    }
  ],
  "attempts": [
    {
      "endpoint": "wp-json/wp/v2/users",
      "http_code": 200,
      "note": "Exposed users"
    },
    {
      "endpoint": "?author=4",
      "http_code": 200,
      "note": "Found username in HTML"
    }
  ]
}
```
### Login Error Analysis

**Schema:**

```json
{
  "tool": "string",
  "url": "string",
  "username_checked": "string",
  "fake_user_error": "string",
  "checked_user_error": "string"
}
```

**Example:**

```json
{
  "tool": "check_error_leak",
  "url": "http://localhost:8081/wp-login.php",
  "username_checked": "admin",
  "fake_user_error": "The username is not registered on this site.",
  "checked_user_error": "The password entered for admin is incorrect."
}
```
It then is sent to the LLM to reason out if the login is vulnerable or not.

## Testing

Tested using a self-hosted WordPress environment with pre-seeded users and posts.

The test cases covers three enumeration techniques.

## Limitations

- Currently supports known WordPress URL structures. Automatic discovery of custom site structures is not implemented.
- Brute-force username discovery and password attacks are not supported.
- Tested primarily against the pre-seeded Docker environment.