from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.llm_service import generate_answer
from app.services.embedding_service import model
from app.services.chroma_service import search_chunks
from app.services.chroma_service import collection
from app.services.memory_service import (
    add_message,
    get_history,
    clear_history
)

router = APIRouter()


@router.get("/stats")
def stats():

    return {
        "total_chunks": collection.count()
    }

@router.get("/health")
def health():
    return {
        "status": "running",
        "chunks": collection.count()
    }

@router.post("/reset-chat")
def reset_chat():

    clear_history()

    return {
        "message": "Chat history cleared"
    }
class QueryRequest(BaseModel):
    question: str


@router.post("/query")
async def query_notes(request: QueryRequest):
    try:
        history = get_history()
        search_query = request.question

        if len(history) > 0:

            last_user_questions = [
                msg["content"]
                for msg in history
                if msg["role"] == "user"
            ]

            if last_user_questions:
                search_query = (
                    last_user_questions[-1]
                    + " "
                    + request.question
                )

        question_embedding = model.encode(
            search_query
        ).tolist()

        results = search_chunks(question_embedding)

        documents = results.get("documents", [[]])[0] if results else []
        metadatas = results.get("metadatas", [[]])[0] if results else []
        distances = results.get("distances", [[]])[0] if results else []

        if not documents:
            answer = "I could not find that information in the uploaded notes."
            add_message("user", request.question)
            add_message("assistant", answer)

            return {
                "question": request.question,
                "answer": answer,
                "sources": ["N/A"]
            }

        formatted_results = []

        for doc, meta, distance in zip(
            documents,
            metadatas,
            distances
        ):
            formatted_results.append(
                {
                    "source": meta.get("source", "N/A"),
                    "distance": distance,
                    "content": doc
                }
            )
        retrieved_chunks = documents

        history = get_history()

        print("\nQUESTION:")
        print(request.question)

        print("\nRETRIEVED CHUNKS:")
        for chunk in retrieved_chunks:
            print(chunk[:300])
            print("-" * 50)
        
        answer = generate_answer(
            request.question,
            retrieved_chunks,
            history
        )
        
        add_message(
            "user",
            request.question
        )

        add_message(
            "assistant",
            answer
        )

        sources = list(
            set(
                meta.get("source", "N/A")
                for meta in metadatas
            )
        )

        if answer.strip() == "I could not find that information in the uploaded notes.":
            sources = ["N/A"]

        return {
            "question": request.question,
            "answer": answer,
            "sources": sources
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {exc}"
        )
