from pathlib import Path

DOCUMENTS_DIR = Path("documents")


def load_documents():
    documents = []

    for file_path in DOCUMENTS_DIR.glob("*.md"):
        text = file_path.read_text(encoding="utf-8")

        documents.append({
            "filename": file_path.name,
            "text": text
        })

    return documents


if __name__ == "__main__":
    documents = load_documents()

    for document in documents:
        print(f"\nLoaded: {document['filename']}")
        print(f"Characters: {len(document['text'])}")