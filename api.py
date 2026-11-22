from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag_chat import ask

app = FastAPI(title="Study Chatbot API")

# Lets the React dev server call this API. Add your deployed frontend URL in phase 2.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Question(BaseModel):
    question: str


@app.post("/api/ask")
def ask_endpoint(body: Question):
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Please type a question.")
    if len(question) > 500:
        raise HTTPException(status_code=400, detail="Keep the question under 500 characters.")
    try:
        return {"answer": ask(question)}
    except Exception:
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")
