from embed_store import client, search
from company_questions import company_list_reply

FALLBACK = "Sorry, bot is unable to answer your question"

SYSTEM_PROMPT = f"""You are a study assistant for software engineering interview prep:
core CS (operating systems, networking, concurrency, DBMS & SQL, Python), data structures
& algorithms, system design, and general interview strategy.

Answer the question directly, using ONLY the context provided.
- Give only the answer: no introduction, no closing remarks, no offers of more help.
- Never mention the context, notes, sources, sections or documents.
- Keep it short: 2-5 sentences, or a few short points when the question asks for steps, types or differences.
- Plain text only: no markdown, no bold, no headings.
- If the context covers the question only partly, answer that part without commenting on the gaps.
- If the answer is not in the context, reply with exactly this sentence and nothing else: "{FALLBACK}"
- This also applies to anything outside the context: general knowledge, greetings, small talk, opinions, current events, or topics not covered. Never use outside knowledge."""


def ask(question, top_k=5):
    # Company-wise question lists come straight from the CSV files (no LLM needed)
    reply = company_list_reply(question)
    if reply is not None:
        return reply

    # 1. Retrieve the most relevant chunks
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
    return response.choices[0].message.content


if __name__ == "__main__":
    print("Study Chatbot (type 'exit' to quit)")
    while True:
        question = input("\nYou: ").strip()
        if question.lower() == "exit":
            break
        if not question:
            continue
        print(f"\nBot: {ask(question)}")
