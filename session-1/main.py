import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from parent directory .env
parent_dir = Path(__file__).parent.parent
load_dotenv(parent_dir / ".env")


def main():
    print("Hello from session-1!")
    
    # Example: Access API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print(f"✓ OpenAI API key loaded: {openai_key[:10]}...")
    else:
        print("⚠ OpenAI API key not found in .env")


if __name__ == "__main__":
    main()
