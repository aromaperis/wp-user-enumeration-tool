import os
from dotenv import load_dotenv
from run_agent import AIAgent

load_dotenv()

agent = AIAgent(
    model=os.getenv("LLM_MODEL", "gemini-3.5-flash-lite"),
    provider=os.getenv("LLM_PROVIDER", "gemini"),
    quiet_mode=True,
)

response = agent.chat("What is France?")
print(response)