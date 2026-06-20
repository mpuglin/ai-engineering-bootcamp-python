"""Contextual ingest: Claude situates each chunk, then OpenAI embeds -> ChromaDB."""
import json
import os
import sys
from pathlib import Path

SESSION = Path(__file__).resolve().parent
if SESSION.name == "scripts":
    SESSION = SESSION.parent
os.chdir(SESSION)
sys.path.insert(0, str(SESSION))

NOTEBOOK = SESSION / "ragexperiment-7-class-architecture.ipynb"


def _exec_notebook_cells(indices: list[int]) -> None:
    nb = json.loads(NOTEBOOK.read_text())
    for idx in indices:
        code = "".join(nb["cells"][idx]["source"])
        exec(compile(code, f"cell_{idx}", "exec"), globals())


def main() -> None:
    _exec_notebook_cells([1, 2, 3])
    db = ContextualVectorDB(  # noqa: F821
        name="regulations_openai_contextual",
        data_dir=Path("data"),
        recursive=True,
    )
    db.load_data()


if __name__ == "__main__":
    main()
