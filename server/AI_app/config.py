# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # ───────────────────────────
    # ▶ 기본 서비스 파라미터
    # ───────────────────────────
    http_host: str = "0.0.0.0"
    http_port: int = 8002
    ws_port:   int = 8765

    # ───────────────────────────
    # ▶ CORS / 보안
    # ───────────────────────────
    allow_origins: list[str] = ["*"]
    jwt_secret:    str = "CHANGEME"     # 배포 시 ENV로만 주입

    # ───────────────────────────
    # ▶ 로깅
    # ───────────────────────────
    log_level: str = "info"

    # ───────────────────────────
    # ▶ 메타
    # ───────────────────────────
    env: str = "development"            # dev / staging / prod …

    # Pydantic-Settings 메타설정
    model_config = SettingsConfigDict(
        env_file=".env",                # 여러 개면 .env.dev 같은 이름 지정
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",                 # 알 수 없는 변수는 무시
    )

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
