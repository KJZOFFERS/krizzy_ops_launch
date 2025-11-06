from __future__ import annotations
from pydantic import BaseSettings, Field
from functools import lru_cache
class Settings(BaseSettings):
    env: str = Field("production", alias="ENV")
    service_name: str = Field("krizzy_ops_web", alias="SERVICE_NAME")
    port: int = Field(8080, alias="PORT")
    discord_webhook_url: str | None = Field(None, alias="DISCORD_WEBHOOK_URL")
    airtable_api_key: str | None = Field(None, alias="AIRTABLE_API_KEY")
    airtable_kpi_base: str | None = Field(None, alias="AIRTABLE_KPI_BASE")
    airtable_kpi_table: str = Field("KPI_Log", alias="AIRTABLE_KPI_TABLE")
    twilio_account_sid: str | None = Field(None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = Field(None, alias="TWILIO_AUTH_TOKEN")
    twilio_from_number: str | None = Field(None, alias="TWILIO_FROM_NUMBER")
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        populate_by_name = True
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
