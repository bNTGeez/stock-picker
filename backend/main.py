from fastapi import FastAPI

from backend.config import get_settings


app = FastAPI(
    title="AI Investment Research Analyst",
    version="0.1.0",
    description="Backend foundation for a controlled investment research memo pipeline.",
)


@app.get("/health")
def health() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "research-backend",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "quote_match_threshold": settings.quote_match_threshold,
        "data_dir": str(settings.data_dir),
        "raw_data_dir": str(settings.raw_data_dir),
        "processed_data_dir": str(settings.processed_data_dir),
    }
