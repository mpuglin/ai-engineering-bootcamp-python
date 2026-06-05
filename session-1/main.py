from typing import Literal

import anthropic
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 1024

app = FastAPI()
client = anthropic.Anthropic(timeout=20.0, max_retries=3)


class Question(BaseModel):
    question: str
    context: str | None = None


class Answer(BaseModel):
    answer: str
    sources: list[str]
    confidence: float


class Document(BaseModel):
    text: str


class Summary(BaseModel):
    summary: str
    key_points: list[str]


class SentimentResult(BaseModel):
    sentiment: Literal["positive", "negative", "neutral"]
    score: float
    reasoning: str


@app.get("/")
def health():
    return {"status": "ok"}

@app.get("/health")
def health_check():
    return {"status": "health is okay"}

@app.post("/ask")
def ask(q: Question):
    kwargs = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": q.question}],
        "output_format": Answer,
    }
    if q.context:
        kwargs["system"] = q.context

    try:
        message = client.messages.parse(**kwargs)
    except anthropic.APITimeoutError:
        return {"error": "request to Anthropic timed out."}
    except anthropic.RateLimitError:
        return {"error": "Anthropic rate limit exceeded."}
    except anthropic.APIConnectionError:
        return {"error": "could not reach the Anthropic API."}
    except anthropic.APIStatusError as exc:
        return {"error": f"Anthropic API returned HTTP {exc.status_code}."}

    if message.parsed_output is None:
        return {"error": "model did not return a valid structured response."}
    return message.parsed_output


@app.post("/ask/stream")
def ask_stream(q: Question):
    kwargs = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": q.question}],
    }
    if q.context:
        kwargs["system"] = q.context

    def generate():
        try:
            with client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    yield text
        except anthropic.APITimeoutError:
            yield "Error: request to Anthropic timed out."
        except anthropic.RateLimitError:
            yield "Error: Anthropic rate limit exceeded."
        except anthropic.APIConnectionError:
            yield "Error: could not reach the Anthropic API."
        except anthropic.APIStatusError as exc:
            yield f"Error: Anthropic API returned HTTP {exc.status_code}."

    return StreamingResponse(generate(), media_type="text/plain")


@app.post("/summarize")
def summarize(doc: Document):
    try:
        message = client.messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system="Summarize the user's text concisely while preserving the key points.",
            messages=[{"role": "user", "content": doc.text}],
            output_format=Summary,
        )
    except anthropic.APITimeoutError:
        return {"error": "request to Anthropic timed out."}
    except anthropic.RateLimitError:
        return {"error": "Anthropic rate limit exceeded."}
    except anthropic.APIConnectionError:
        return {"error": "could not reach the Anthropic API."}
    except anthropic.APIStatusError as exc:
        return {"error": f"Anthropic API returned HTTP {exc.status_code}."}

    if message.parsed_output is None:
        return {"error": "model did not return a valid structured response."}
    return message.parsed_output


@app.post("/analyze-sentiment")
def analyze_sentiment(doc: Document):
    try:
        message = client.messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system="Analyze the sentiment of the user's text. Provide the overall sentiment, a score from -1.0 (very negative) to 1.0 (very positive), and brief reasoning.",
            messages=[{"role": "user", "content": doc.text}],
            output_format=SentimentResult,
        )
    except anthropic.APITimeoutError:
        return {"error": "request to Anthropic timed out."}
    except anthropic.RateLimitError:
        return {"error": "Anthropic rate limit exceeded."}
    except anthropic.APIConnectionError:
        return {"error": "could not reach the Anthropic API."}
    except anthropic.APIStatusError as exc:
        return {"error": f"Anthropic API returned HTTP {exc.status_code}."}

    if message.parsed_output is None:
        return {"error": "model did not return a valid structured response."}
    return message.parsed_output