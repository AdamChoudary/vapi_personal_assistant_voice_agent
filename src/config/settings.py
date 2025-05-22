from pydantic_settings import BaseSettings

class VapiSettings(BaseSettings):
    vapi_api_key: str | None = None
    vapi_api_url: str = "https://api.vapi.ai"

    class Config:
        env_file = ".env"