import os

import anthropic

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-5"


class AnthropicError(Exception):
    """Base error for failures at the Anthropic client boundary."""


class AnthropicTimeoutError(AnthropicError):
    """The request exceeded the configured timeout."""


class AnthropicRateLimitError(AnthropicError):
    """Anthropic returned HTTP 429. ``retry_after`` is the suggested wait in seconds, if provided."""

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


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
        self.client = anthropic.Anthropic(api_key=self.api_key, timeout=self.timeout)

    def send_message(self, message, max_tokens=1024):
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": message}],
            )
        except anthropic.APITimeoutError as exc:
            raise AnthropicTimeoutError(f"Request timed out after {self.timeout}s") from exc
        except anthropic.RateLimitError as exc:
            retry_after = exc.response.headers.get("retry-after")
            raise AnthropicRateLimitError(
                "Anthropic rate limit exceeded (HTTP 429)",
                retry_after=float(retry_after) if retry_after else None,
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise AnthropicError(f"Could not reach Anthropic API: {exc}") from exc
        except anthropic.APIStatusError as exc:
            raise AnthropicError(
                f"Anthropic API returned HTTP {exc.status_code}: {exc.message}"
            ) from exc

        return response.model_dump()


if __name__ == "__main__":
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent / ".env")

    client = AnthropicClient()
    result = client.send_message("What is the capital of France?")

    # The Messages API returns content as a list of blocks.
    for block in result.get("content", []):
        if block.get("type") == "text":
            print(block["text"])
