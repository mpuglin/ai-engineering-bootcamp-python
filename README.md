# AI Engineering Bootcamp - Python

Classwork and projects from an AI Engineering course covering multi-agent systems, vector databases, and agent architectures.

## Structure

Each class session has its own directory with isolated dependencies:

- `session-1/` - Session 1 classwork
- `session-2/` - Session 2 classwork
- (more sessions to be added)

## Requirements

- Python >= 3.14
- uv (Python package manager)

## Setup

1. **Clone the repository**
2. **Copy `.env.example` to `.env` and add your API keys:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys
   ```
3. **The `.env` file is shared across all sessions** - no need to duplicate keys!

## Working with Sessions

Each session directory is self-contained:

```bash
# Navigate to a session
cd session-1

# Install dependencies for that session
uv sync

# Run the code
python main.py
```

## Development Workflow

1. Work in the specific session directory
2. Commit changes from the repository root:
   ```bash
   cd /path/to/ai-engineering-bootcamp-python
   git add session-x/
   git commit -m "feat: Complete session-x exercises"
   git push
   ```
