import logging
from typing import Literal

import anthropic
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("session-1")

MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 1024

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = anthropic.Anthropic(timeout=20.0, max_retries=3)


class Question(BaseModel):
    question: str = Field(max_length=4000)
    context: str | None = Field(default=None, max_length=4000)


class Answer(BaseModel):
    answer: str
    sources: list[str]
    confidence: float


class Document(BaseModel):
    text: str = Field(max_length=8000)


class Summary(BaseModel):
    summary: str
    key_points: list[str]


class SentimentResult(BaseModel):
    sentiment: Literal["positive", "negative", "neutral"]
    score: float
    reasoning: str


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=503, content={"error": "internal error"})


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask(q: Question):
    kwargs = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": q.question}],
        "output_format": Answer,
    }
    if q.context:
        # context is passed as the system prompt to scope the model's behaviour
        kwargs["system"] = q.context

    try:
        message = client.messages.parse(**kwargs)
    except anthropic.APITimeoutError:
        logger.exception("Timeout on /ask")
        return JSONResponse(status_code=504, content={"error": "request to Anthropic timed out."})
    except anthropic.RateLimitError:
        logger.exception("Rate limit on /ask")
        return JSONResponse(status_code=429, content={"error": "Anthropic rate limit exceeded."})
    except anthropic.APIConnectionError:
        logger.exception("Connection error on /ask")
        return JSONResponse(status_code=502, content={"error": "could not reach the Anthropic API."})
    except anthropic.APIStatusError as exc:
        logger.exception("API status error on /ask: HTTP %s", exc.status_code)
        return JSONResponse(status_code=502, content={"error": f"Anthropic API returned HTTP {exc.status_code}."})

    if message.parsed_output is None:
        logger.error("Empty parsed output on /ask")
        return JSONResponse(status_code=502, content={"error": "model did not return a valid structured response."})
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
            logger.exception("Timeout on /ask/stream")
            yield "Error: request to Anthropic timed out."
        except anthropic.RateLimitError:
            logger.exception("Rate limit on /ask/stream")
            yield "Error: Anthropic rate limit exceeded."
        except anthropic.APIConnectionError:
            logger.exception("Connection error on /ask/stream")
            yield "Error: could not reach the Anthropic API."
        except anthropic.APIStatusError as exc:
            logger.exception("API status error on /ask/stream: HTTP %s", exc.status_code)
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
        logger.exception("Timeout on /summarize")
        return JSONResponse(status_code=504, content={"error": "request to Anthropic timed out."})
    except anthropic.RateLimitError:
        logger.exception("Rate limit on /summarize")
        return JSONResponse(status_code=429, content={"error": "Anthropic rate limit exceeded."})
    except anthropic.APIConnectionError:
        logger.exception("Connection error on /summarize")
        return JSONResponse(status_code=502, content={"error": "could not reach the Anthropic API."})
    except anthropic.APIStatusError as exc:
        logger.exception("API status error on /summarize: HTTP %s", exc.status_code)
        return JSONResponse(status_code=502, content={"error": f"Anthropic API returned HTTP {exc.status_code}."})

    if message.parsed_output is None:
        logger.error("Empty parsed output on /summarize")
        return JSONResponse(status_code=502, content={"error": "model did not return a valid structured response."})
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
        logger.exception("Timeout on /analyze-sentiment")
        return JSONResponse(status_code=504, content={"error": "request to Anthropic timed out."})
    except anthropic.RateLimitError:
        logger.exception("Rate limit on /analyze-sentiment")
        return JSONResponse(status_code=429, content={"error": "Anthropic rate limit exceeded."})
    except anthropic.APIConnectionError:
        logger.exception("Connection error on /analyze-sentiment")
        return JSONResponse(status_code=502, content={"error": "could not reach the Anthropic API."})
    except anthropic.APIStatusError as exc:
        logger.exception("API status error on /analyze-sentiment: HTTP %s", exc.status_code)
        return JSONResponse(status_code=502, content={"error": f"Anthropic API returned HTTP {exc.status_code}."})

    if message.parsed_output is None:
        logger.error("Empty parsed output on /analyze-sentiment")
        return JSONResponse(status_code=502, content={"error": "model did not return a valid structured response."})
    return message.parsed_output
