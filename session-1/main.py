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
    }
    if q.context:
        kwargs["system"] = q.context

    try:
        message = client.messages.create(**kwargs)
    except anthropic.APITimeoutError:
        return {"answer": "Error: request to Anthropic timed out."}
    except anthropic.RateLimitError:
        return {"answer": "Error: Anthropic rate limit exceeded."}
    except anthropic.APIConnectionError:
        return {"answer": "Error: could not reach the Anthropic API."}
    except anthropic.APIStatusError as exc:
        return {"answer": f"Error: Anthropic API returned HTTP {exc.status_code}."}

    text = "".join(block.text for block in message.content if block.type == "text")
    return {"answer": text}


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
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system="Summarize the user's text concisely while preserving the key points.",
            messages=[{"role": "user", "content": doc.text}],
        )
    except anthropic.APITimeoutError:
        return {"summary": "Error: request to Anthropic timed out."}
    except anthropic.RateLimitError:
        return {"summary": "Error: Anthropic rate limit exceeded."}
    except anthropic.APIConnectionError:
        return {"summary": "Error: could not reach the Anthropic API."}
    except anthropic.APIStatusError as exc:
        return {"summary": f"Error: Anthropic API returned HTTP {exc.status_code}."}

    text = "".join(block.text for block in message.content if block.type == "text")
    return {"summary": text}


@app.post("/analyze-sentiment")
def analyze_sentiment(doc: Document):
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system="Analyze the sentiment of the user's text. State the overall sentiment (positive, negative, or neutral) and briefly explain why.",
            messages=[{"role": "user", "content": doc.text}],
        )
    except anthropic.APITimeoutError:
        return {"sentiment": "Error: request to Anthropic timed out."}
    except anthropic.RateLimitError:
        return {"sentiment": "Error: Anthropic rate limit exceeded."}
    except anthropic.APIConnectionError:
        return {"sentiment": "Error: could not reach the Anthropic API."}
    except anthropic.APIStatusError as exc:
        return {"sentiment": f"Error: Anthropic API returned HTTP {exc.status_code}."}

    text = "".join(block.text for block in message.content if block.type == "text")
    return {"sentiment": text}