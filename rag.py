"""
Lightweight retrieval system for Maintain AI.

The current application uses BM25 retrieval instead of a local
embedding model. This keeps the RAG layer suitable for small,
organization-specific maintenance document collections and
low-memory hosting environments such as Render Free.

The retrieval layer is intentionally independent from the LLM.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from document_loader import load_documents


# ============================================================
# CONFIGURATION
# ============================================================

DOCUMENTS_DIR = Path("documents")

CHUNK_SIZE = 700
CHUNK_OVERLAP = 120

DEFAULT_TOP_K = 3

# BM25 parameters.
BM25_K1 = 1.5
BM25_B = 0.75


# ============================================================
# TOKENIZATION
# ============================================================

TOKEN_PATTERN = re.compile(
    r"[A-Za-z0-9]+(?:[-_/][A-Za-z0-9]+)*"
)


def tokenize(text: str) -> list[str]:
    """
    Convert text into normalized search tokens.

    Hyphenated identifiers such as BC-01 are preserved because
    equipment identifiers and item numbers are important in
    maintenance documents.
    """

    return [
        token.lower()
        for token in TOKEN_PATTERN.findall(text)
    ]


# ============================================================
# DOCUMENT CHUNKING
# ============================================================

def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """
    Split a document into overlapping chunks.

    The overlap prevents important information from being split
    completely across two chunks.
    """

    if not text.strip():
        return []

    if overlap >= chunk_size:
        raise ValueError(
            "Chunk overlap must be smaller than chunk size."
        )

    chunks: list[str] = []

    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(
            start + chunk_size,
            text_length
        )

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start += chunk_size - overlap

    return chunks


# ============================================================
# RETRIEVAL DATA
# ============================================================

@dataclass(frozen=True)
class DocumentChunk:
    """
    A searchable section of an organization document.
    """

    filename: str
    text: str
    tokens: tuple[str, ...]


@dataclass
class RetrievalIndex:
    """
    In-memory BM25 retrieval index.

    This is intentionally small and simple. The current Maintain AI
    knowledge base is document-sized rather than enterprise-scale.
    """

    chunks: list[DocumentChunk]
    document_frequencies: Counter[str]
    average_document_length: float
    document_count: int


# ============================================================
# INDEX BUILDING
# ============================================================

def build_retrieval_index() -> RetrievalIndex:
    """
    Load maintenance documents and build the in-memory retrieval index.

    No ML model is loaded.
    No GPU dependencies are required.
    """

    documents = load_documents()

    if not documents:
        raise RuntimeError(
            "No maintenance documents were found in the "
            f"'{DOCUMENTS_DIR}' directory."
        )

    chunks: list[DocumentChunk] = []

    for document in documents:
        filename = document["filename"]
        text = document["text"]

        for chunk in chunk_text(text):
            tokens = tuple(tokenize(chunk))

            if not tokens:
                continue

            chunks.append(
                DocumentChunk(
                    filename=filename,
                    text=chunk,
                    tokens=tokens,
                )
            )

    if not chunks:
        raise RuntimeError(
            "Maintenance documents were found, but no searchable "
            "content could be extracted."
        )

    document_frequencies: Counter[str] = Counter()

    total_length = 0

    for chunk in chunks:
        unique_terms = set(chunk.tokens)

        document_frequencies.update(
            unique_terms
        )

        total_length += len(chunk.tokens)

    average_document_length = (
        total_length / len(chunks)
    )

    index = RetrievalIndex(
        chunks=chunks,
        document_frequencies=document_frequencies,
        average_document_length=average_document_length,
        document_count=len(chunks),
    )

    print(
        "Maintenance retrieval index ready: "
        f"{len(chunks)} chunks from "
        f"{len(documents)} documents."
    )

    return index


# ============================================================
# BM25 SCORING
# ============================================================

def bm25_score(
    query_tokens: list[str],
    chunk: DocumentChunk,
    index: RetrievalIndex,
) -> float:
    """
    Calculate BM25 relevance for one document chunk.
    """

    if not query_tokens:
        return 0.0

    term_frequencies = Counter(
        chunk.tokens
    )

    document_length = len(chunk.tokens)

    score = 0.0

    for term in query_tokens:
        frequency = term_frequencies.get(
            term,
            0
        )

        if frequency == 0:
            continue

        document_frequency = (
            index.document_frequencies.get(
                term,
                0
            )
        )

        if document_frequency == 0:
            continue

        # Standard BM25 inverse-document-frequency component.
        idf = math.log(
            1
            + (
                (
                    index.document_count
                    - document_frequency
                    + 0.5
                )
                / (
                    document_frequency
                    + 0.5
                )
            )
        )

        denominator = (
            frequency
            + BM25_K1
            * (
                1
                - BM25_B
                + BM25_B
                * (
                    document_length
                    / index.average_document_length
                )
            )
        )

        score += (
            idf
            * (
                frequency
                * (BM25_K1 + 1)
            )
            / denominator
        )

    return score


# ============================================================
# SEARCH
# ============================================================

def search_documents(
    question: str,
    index: RetrievalIndex,
    top_k: int = DEFAULT_TOP_K,
) -> tuple[str, list[str]]:
    """
    Retrieve the most relevant maintenance document chunks.

    Returns:

        context:
            Text to provide to the LLM.

        sources:
            Unique source filenames.
    """

    if not question.strip():
        return "", []

    if not index.chunks:
        return "", []

    query_tokens = tokenize(question)

    if not query_tokens:
        return "", []

    scored_chunks: list[tuple[float, DocumentChunk]] = []

    normalized_question = question.lower()

    for chunk in index.chunks:
        score = bm25_score(
            query_tokens,
            chunk,
            index,
        )

        # Small exact-match bonus.
        #
        # This is useful for identifiers such as:
        # BC-01
        # specific item numbers
        # component names
        #
        # Exact matching is especially valuable in maintenance
        # knowledge bases.
        normalized_chunk = chunk.text.lower()

        exact_bonus = 0.0

        for token in query_tokens:
            if len(token) >= 3 and token in normalized_chunk:
                exact_bonus += 0.05

        # If the complete question phrase appears in a chunk,
        # provide a modest additional relevance bonus.
        if (
            len(normalized_question) >= 8
            and normalized_question in normalized_chunk
        ):
            exact_bonus += 0.5

        final_score = score + exact_bonus

        if final_score > 0:
            scored_chunks.append(
                (
                    final_score,
                    chunk
                )
            )

    if not scored_chunks:
        return "", []

    scored_chunks.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    selected = scored_chunks[:max(1, top_k)]

    context_parts: list[str] = []
    sources: list[str] = []

    for _, chunk in selected:
        context_parts.append(
            chunk.text
        )

        if chunk.filename not in sources:
            sources.append(
                chunk.filename
            )

    context = "\n\n".join(
        context_parts
    )

    return context, sources