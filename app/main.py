from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.upload import router as upload_router
from app.routes.query import router as query_router
from app.routes.documents import router as documents_router

app = FastAPI(title="CampusGPT", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(query_router)
app.include_router(documents_router)


@app.get("/")
def root():
    return {"message": "AI Study Assistant v2.0 Running"}