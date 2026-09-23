import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models import FindRequest, FindResponse
from app.data import load_contractors
from app.filters import filter_candidates
from app.ranking import Ranker


def create_app(dataset_path=None, encoder=None):
    @asynccontextmanager
    async def lifespan(app):
        path = Path(dataset_path or os.environ.get("CONTRACTORS_PATH") or
                    Path(__file__).resolve().parents[1] / "data/contractors.csv")
        app.state.contractors = load_contractors(path)
        app.state.ranker = Ranker(app.state.contractors, model=encoder)
        yield

    app = FastAPI(title="Contractor Finder", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/health")
    def health():
        return {"status": "ok", "contractors": len(app.state.contractors),
                "synthetic_count": sum(c["synthetic"] for c in app.state.contractors)}

    @app.post("/api/find", response_model=FindResponse)
    def find(req: FindRequest):
        candidates, status, count, reasons = filter_candidates(app.state.contractors, req)
        ranked = app.state.ranker.rank_and_explain(candidates, req) if candidates else []
        ranked = [{**c, "category": req.category} for c in ranked]
        return FindResponse(status=status, candidates=ranked,
                            excluded_count=count, excluded_reasons=reasons)

    return app


app = create_app()
