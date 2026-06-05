import os
from pathlib import Path
from dotenv import load_dotenv
import uvicorn

# Load environment variables from parent directory .env
parent_dir = Path(__file__).parent.parent
load_dotenv(parent_dir / ".env")


async def app(scope, receive, send):
    """
    Basic ASGI application
    """
    assert scope["type"] == "http"

    # Get API key status
    openai_key = os.getenv("OPENAI_API_KEY")
    key_status = f"✓ OpenAI API key loaded: {openai_key[:10]}..." if openai_key else "⚠ OpenAI API key not found in .env"

    # Build response
    body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Session 1 Server</title>
        <style>
            body {{
                font-family: system-ui, -apple-system, sans-serif;
                max-width: 800px;
                margin: 40px auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #333; }}
            .status {{ 
                padding: 10px;
                background: #e8f5e9;
                border-radius: 4px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Session 1 - Uvicorn Server</h1>
            <p>Server is running successfully!</p>
            <div class="status">
                <strong>Environment Status:</strong><br>
                {key_status}
            </div>
            <p><strong>Path:</strong> {scope['path']}</p>
            <p><strong>Method:</strong> {scope['method']}</p>
        </div>
    </body>
    </html>
    """.encode("utf-8")

    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [
            [b"content-type", b"text/html"],
        ],
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })


def main():
    print("Starting Uvicorn server...")
    print("Visit http://127.0.0.1:8001 in your browser")
    
    # Check environment variables
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print(f"✓ OpenAI API key loaded: {openai_key[:10]}...")
    else:
        print("⚠ OpenAI API key not found in .env")
    
    # Start the server
    uvicorn.run(app, host="127.0.0.1", port=8001)


if __name__ == "__main__":
    main()
