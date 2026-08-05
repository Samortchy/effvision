from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str  # postgresql+asyncpg://...:5432/postgres  (direct connection, not the pooler)
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    # Default off. `debug` drives echo=True on the SQLAlchemy engine, which logs
    # every statement *with its bound parameters* — for /auth/login and
    # /auth/register that means password hashes and email addresses in the logs.
    # An unset DEBUG must therefore fail closed, not open. Set DEBUG=true in
    # your local .env.
    debug: bool = False
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()