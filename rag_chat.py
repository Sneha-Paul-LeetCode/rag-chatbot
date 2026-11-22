from embed_store import client, search

SYSTEM_PROMPT = """You are a study assistant for software engineering interview prep:
core CS (operating systems, networking, concurrency, DBMS & SQL, Python), data structures
& algorithms, system design, and general interview strategy.

Answer using ONLY the context provided, which comes from the user's notes.
- Start with a direct answer, then add key points as short bullets if helpful.
- For "difference between" questions, give a compact side-by-side comparison.
- If the context covers the question only partly, answer that part and say what is missing.
- If the answer is not in the context, reply exactly: "I couldn't find that in your notes."
- Never use outside knowledge, even if you know the answer."""


def ask(question, top_k=5):
    # 1. Retrieve the most relevant chunks (each already starts with its section heading)
    results = search(question, top_k=top_k)

    # 2. Build the context
    context = "\n\n---\n\n".join(text for text, _ in results)

    # 3. Ask GPT with the context + question
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
    )
    answer = response.choices[0].message.content

    # Unique section names, in the order they were retrieved
    sections = list(dict.fromkeys(meta["section"] for _, meta in results))
    return answer, sections


if __name__ == "__main__":
    print("Core CS Study Chatbot (type 'exit' to quit)")
    while True:
        question = input("\nYou: ").strip()
        if question.lower() == "exit":
            break
        if not question:
            continue

        answer, _ = ask(question)
        print(f"\nBot: {answer}")
