"""Baseline ingest: all PDFs under data/ -> OpenAI embeddings -> ChromaDB."""
import os
import re
import tiktoken
import openai as openai_client
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv, find_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

SESSION = Path(__file__).resolve().parent
if SESSION.name == "scripts":
    SESSION = SESSION.parent
os.chdir(SESSION)

load_dotenv(find_dotenv())

EMBEDDING_MODEL = "text-embedding-3-small"
COLLECTION = "regulations_openai_baseline"
DATA_DIR = Path("data")
CHROMA_PATH = "./data/chroma_store"
BATCH_SIZE = 500
MAX_TOKENS = 7_500

_HEADING_RE = re.compile(
    r"(?:Chapter\s+[A-Z]?\d+[^\n]*|ARTICLE\s+[IVXLC]+[^\n]*|§\s*[A-Z]?\d+[-\w]*\.[^\n]*)",
    re.MULTILINE,
)
_enc = tiktoken.get_encoding("cl100k_base")


def extract_heading(text: str, page: int) -> str:
    match = _HEADING_RE.search(text)
    if match:
        return match.group(0).strip()[:80]
    return f"p. {page + 1}"


def sanitize(text: str, max_tokens: int | None = None) -> str:
    text = text.replace("\x00", "").encode("utf-8", errors="ignore").decode("utf-8").strip()
    if max_tokens:
        toks = _enc.encode(text)
        if len(toks) > max_tokens:
            text = _enc.decode(toks[:max_tokens])
    return text


def main() -> None:
    pdf_paths = sorted(DATA_DIR.glob("**/*.pdf"))
    print(f"Found {len(pdf_paths)} PDFs under {DATA_DIR}")

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    embed_fn = OpenAIEmbeddingFunction(
        api_key=os.environ["OPENAI_API_KEY"], model_name=EMBEDDING_MODEL
    )
    col = client.get_or_create_collection(name=COLLECTION, embedding_function=embed_fn)
    print(f"Collection '{COLLECTION}' currently has {col.count():,} chunks")

    indexed = set()
    if col.count() > 0:
        indexed = {m["source"] for m in col.get(include=["metadatas"])["metadatas"]}
    indexed_names = {Path(s).name for s in indexed}

    def source_key(p: Path) -> str:
        return str(p.relative_to(DATA_DIR))

    missing = [
        p for p in pdf_paths
        if source_key(p) not in indexed and p.name not in indexed_names
    ]
    print(f"To index: {len(missing)} PDFs")
    if not missing:
        print("Already up to date.")
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500, chunk_overlap=200, separators=["\n\n", "\n", " ", ""]
    )
    oa = openai_client.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    raw_docs = []
    for p in missing:
        print(f"  loading {source_key(p)}")
        raw_docs.extend(PyPDFLoader(str(p)).load())
    print(f"Loaded {len(raw_docs)} pages")

    chunks = splitter.split_documents(raw_docs)
    next_index = col.count()
    sections = []
    for doc in chunks:
        sp = Path(doc.metadata.get("source", ""))
        try:
            source = str(sp.relative_to(DATA_DIR.resolve()))
        except ValueError:
            source = sp.name
        sections.append(
            {
                "text": doc.page_content,
                "source": source,
                "chunk_index": next_index,
                "heading": extract_heading(doc.page_content, doc.metadata.get("page", 0)),
            }
        )
        next_index += 1

    print(f"Split into {len(sections):,} chunks; embedding...")
    texts = [sanitize(s["text"], MAX_TOKENS) for s in sections]
    embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        resp = oa.embeddings.create(input=batch, model=EMBEDDING_MODEL)
        embeddings.extend([r.embedding for r in resp.data])
        print(f"  Embedded {min(i + BATCH_SIZE, len(texts))}/{len(texts)}")

    col.add(
        documents=texts,
        embeddings=embeddings,
        metadatas=[
            {"source": s["source"], "chunk_index": s["chunk_index"], "heading": s["heading"]}
            for s in sections
        ],
        ids=[
            f"{s['source'].replace('/', '__')}_chunk_{s['chunk_index']}" for s in sections
        ],
    )
    print(f"Done. Collection '{COLLECTION}' now has {col.count():,} chunks.")

    sources = sorted({m["source"] for m in col.get(include=["metadatas"])["metadatas"]})
    allegh = [s for s in sources if "allegheny" in s.lower()]
    print(f"Unique sources: {len(sources)} | alleghanycounty: {len(allegh)}")


if __name__ == "__main__":
    main()
