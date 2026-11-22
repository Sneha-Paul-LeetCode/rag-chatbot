from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from load_docs import load_notes, chunk_document

load_dotenv()
client = OpenAI()

# Chroma saves everything into this folder
db = chromadb.PersistentClient(path="chroma_db")
collection = db.get_or_create_collection("cs_notes")


def embed(texts):
    """Turn a list of texts into a list of embeddings."""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    return [item.embedding for item in response.data]


def build_index(folder="notes", batch_size=100):
    """Load notes, chunk them by section, embed them, store them."""
    global collection

    # Start fresh so old chunks from earlier runs don't linger as duplicates
    try:
        db.delete_collection("cs_notes")
    except Exception:
        pass
    collection = db.get_or_create_collection("cs_notes")

    chunks = []
    for doc in load_notes(folder):
        chunks.extend(chunk_document(doc))

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        collection.upsert(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            embeddings=embed([c["text"] for c in batch]),
            metadatas=[{"source": c["source"], "topic": c["topic"], "section": c["section"]} for c in batch],
        )
        print(f"  embedded {min(start + batch_size, len(chunks))}/{len(chunks)}")
    print(f"Stored {len(chunks)} chunks")


def search(question, top_k=5):
    """Find the chunks closest in meaning to the question."""
    results = collection.query(
        query_embeddings=embed([question]),
        n_results=top_k,
    )
    return list(zip(results["documents"][0], results["metadatas"][0]))


if __name__ == "__main__":
    build_index()

    question = input("Ask something from your notes: ")
    for text, meta in search(question):
        print(f"\n--- {meta['section']} ({meta['topic']}) ---")
        print(text[:300])
