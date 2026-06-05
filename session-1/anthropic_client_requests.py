import os

import requests

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-5"


class AnthropicClient:
    """
    Thin wrapper around the Anthropic Messages HTTP endpoint.

    Kept deliberately minimal so the provider can be swapped, mocked in tests,
    and reasoned about (cost, retries, auth) from a single boundary.
    """

    def __init__(self, api_key=None, model=DEFAULT_MODEL, timeout=30):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set (pass api_key or add it to .env)")
        self.model = model
        self.timeout = timeout

    def send_message(self, message, max_tokens=1024):
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": message}],
        }

        response = requests.post(
            ANTHROPIC_API_URL,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent / ".env")

    client = AnthropicClient()
    result = client.send_message("hello claude")

    # The Messages API returns content as a list of blocks.
    for block in result.get("content", []):
        if block.get("type") == "text":
            print(block["text"])
