from openai import OpenAI

# .env
import os
from dotenv import load_dotenv

# Raising FastAPI Exception
from fastapi import HTTPException

# Logging
import logging

load_dotenv()

client = None
logger = logging.getLogger("app")

def setup() -> OpenAI:
    # Environment setup
    endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key: str = os.getenv("AZURE_OPENAI_API_KEY")

    # Validate required settings without leaking secrets in logs
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Azure OpenAI API key not configured. Please check environment variables."
        )
    if not endpoint:
        raise HTTPException(
            status_code=500,
            detail="Azure OpenAI endpoint not configured. Please check environment variables."
        )
    global client
    
    client = OpenAI(base_url=endpoint, api_key=api_key)
    
    return client

def send_input(prompt: str, user_input: str) -> str:
    deployment_name: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "Michael-Web-Search-Test")
    completion = client.responses.create(
            model=deployment_name,
            tools=[
                {
                    "type": "web_search_preview",
                    "user_location": {
                        "type": "approximate",
                        "country": "HK"
                    }
                }
            ],
            input=prompt + user_input,
            timeout=30,
            max_output_tokens=75
        )
    return getattr(completion, "output_text", None)


def health_check_openai(timeout: int = 5) -> tuple[bool, str | None]:
    """Perform a lightweight request to verify OpenAI connectivity."""
    try:
        setup()
        deployment_name: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "Michael-Web-Search-Test")

        # Keep this request minimal to reduce latency and token usage in health checks.
        client.responses.create(
            model=deployment_name,
            input="health-check",
            timeout=timeout,
            max_output_tokens=16,
        )
        return True, None
    except HTTPException as e:
        return False, str(e.detail)
    except Exception as e:
        logger.exception("OpenAI health check failed")
        return False, str(e)