from document_loader import load_documents
from sentence_transformers import SentenceTransformer
import faiss
import json
from pathlib import Path
import hashlib


# -----------------------------
# Configuration
# -----------------------------


EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_embedding_model = None

def get_embedding_model():
    global _embedding_model

    if _embedding_model is None:
        print("Loading embedding model...")

        _embedding_model = SentenceTransformer(
            EMBEDDING_MODEL,
            device="cpu"
        )

    return _embedding_model

CACHE_DIR = Path("data")
INDEX_FILE = CACHE_DIR / "maintenance.index"
CHUNKS_FILE = CACHE_DIR / "chunks.json"
HASH_FILE = CACHE_DIR / "documents.hash"


# -----------------------------
# Chunk documents
# -----------------------------

def chunk_text(text, chunk_size=500, overlap=100):
    chunks = []

    start = 0

    while start < len(text):
        end = start + chunk_size

        chunks.append(text[start:end])

        start += chunk_size - overlap

    return chunks


# -----------------------------
# Detect document changes
# -----------------------------

def get_documents_hash(documents):
    content = ""

    for document in sorted(documents, key=lambda x: x["filename"]):
        content += document["filename"]
        content += document["text"]

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


# -----------------------------
# Build knowledge base
# -----------------------------

def build_knowledge_base():

    documents = load_documents()

    CACHE_DIR.mkdir(exist_ok=True)

    current_hash = get_documents_hash(documents)

    # Check whether cached knowledge base exists
    if (
        INDEX_FILE.exists()
        and CHUNKS_FILE.exists()
        and HASH_FILE.exists()
    ):

        saved_hash = HASH_FILE.read_text().strip()

        if saved_hash == current_hash:

            print("Loading cached knowledge base...")

            model = get_embedding_model()
            index = faiss.read_index(
                str(INDEX_FILE)
            )

            chunks = json.loads(
                CHUNKS_FILE.read_text(
                    encoding="utf-8"
                )
            )

            print(
                f"Loaded cached knowledge base: "
                f"{len(chunks)} chunks"
            )

            return model, index, chunks

    # -----------------------------
    # Build new knowledge base
    # -----------------------------

    print("Building new knowledge base...")

    chunks = []

    for document in documents:

        document_chunks = chunk_text(
            document["text"]
        )

        for chunk in document_chunks:

            chunks.append({
                "filename": document["filename"],
                "text": chunk
            })

    print(
        f"Creating embeddings for "
        f"{len(chunks)} chunks..."
    )

    model = get_embedding_model()

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=True
    )

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatL2(
        dimension
    )

    index.add(
        embeddings.astype("float32")
    )

    # -----------------------------
    # Save cache
    # -----------------------------

    faiss.write_index(
        index,
        str(INDEX_FILE)
    )

    CHUNKS_FILE.write_text(
        json.dumps(
            chunks,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    HASH_FILE.write_text(
        current_hash,
        encoding="utf-8"
    )

    print("Knowledge base cached successfully.")

    return model, index, chunks


# -----------------------------
# Search knowledge base
# -----------------------------

def search_documents(
    question,
    model,
    index,
    chunks,
    top_k=3
):

    question_embedding = model.encode(
        [question],
        convert_to_numpy=True
    )

    distances, indices = index.search(
        question_embedding.astype("float32"),
        top_k
    )

    context_parts = []
    sources = []

    for index_number in indices[0]:

        if index_number < 0:
            continue

        result = chunks[index_number]

        context_parts.append(
            result["text"]
        )

        if result["filename"] not in sources:

            sources.append(
                result["filename"]
            )

    context = "\n\n".join(
        context_parts
    )

    return context, sources