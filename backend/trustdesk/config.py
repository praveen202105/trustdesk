from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_schema: str = "public"
    database_url: str = "postgresql+psycopg://trustdesk:local-dev-only@localhost:5438/trustdesk"
    demo_login_token: str = "local-demo-only"
    session_secret: str = "local-session-secret-change-before-hosting"
    app_origin: str = "http://localhost:3000"
    ai_provider: str = "mock"
    ai_model: str = "mock-policy-v1"
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    embedding_provider: str = "mock"
    embedding_model: str = "mock-hash-v1"
    embedding_dimension: int = 64
    mock_action_base_url: str = "http://localhost:8001"
    mock_action_secret: str = "local-actions-only"
    data_dir: str = "../capstone/data"
    secure_cookies: bool = False
    revision: str = "development"


settings = Settings()

if settings.app_origin.startswith("https://"):
    if (
        settings.session_secret == "local-session-secret-change-before-hosting"
        or settings.demo_login_token == "local-demo-only"
        or settings.mock_action_secret == "local-actions-only"
    ):
        raise ValueError("Configure unique hosted secrets before enabling the public workspace")
    if not settings.secure_cookies:
        raise ValueError("HTTPS hosting requires secure cookies")
