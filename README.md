# AI Engineering Bootcamp - Python

Python projects and experiments from the AI Engineering Bootcamp, including vector databases, agent systems, and multi-agent architectures.

## Requirements

- Python >= 3.14
- uv (Python package manager)

## Dependencies

This project uses the following key dependencies:

- **pinecone** (>=9.0.1) - Vector database for AI applications

Additional installed packages:
- anyio (4.13.0)
- certifi (2026.5.20)
- httpx (0.28.1)
- httpcore (1.0.9)
- h2 (4.3.0)
- msgspec (0.21.1)
- orjson (3.11.9)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd pinecone-experiment-1
```

2. Install dependencies using uv:
```bash
uv sync
```

This will create a virtual environment at `.venv` and install all required packages.

## Usage

```python
import pinecone

# Your Pinecone code here
```

## Development

To add new dependencies:
```bash
uv add <package-name>
```

To remove dependencies:
```bash
uv remove <package-name>
```

## License

Add your license information here.