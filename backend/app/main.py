from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models import FindRequest, FindResponse, Candidate

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # на хакатоне ок, потом сузить
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/find", response_model=FindResponse)
def find(req: FindRequest):
    # TODO: заменить на реальную логику
    return FindResponse(
        status="ok",
        candidates=[
            Candidate(
                id="stub1", name="Тестовый Подрядчик",
                category=req.category, city=req.city,
                price_from_kzt=req.budget_kzt,
                explanation="это заглушка, реальная логика в разработке",
            )
        ],
    )
