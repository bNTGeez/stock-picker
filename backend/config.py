from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as error:
        raise ValueError(f"{name} must be a float") from error


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    llm_api_key: str | None
    llm_model: str
    quote_match_threshold: float
    data_dir: Path
    raw_data_dir: Path
    processed_data_dir: Path


@lru_cache
def get_settings() -> Settings:
    data_dir = Path(os.getenv("RESEARCH_DATA_DIR", "backend/data"))
    return Settings(
        llm_provider=os.getenv("RESEARCH_LLM_PROVIDER", "manual"),
        llm_api_key=os.getenv("RESEARCH_LLM_API_KEY"),
        llm_model=os.getenv("RESEARCH_LLM_MODEL", "gpt-5"),
        quote_match_threshold=_float_env("RESEARCH_QUOTE_MATCH_THRESHOLD", 0.95),
        data_dir=data_dir,
        raw_data_dir=Path(os.getenv("RESEARCH_RAW_DATA_DIR", str(data_dir / "raw"))),
        processed_data_dir=Path(
            os.getenv("RESEARCH_PROCESSED_DATA_DIR", str(data_dir / "processed"))
        ),
    )
