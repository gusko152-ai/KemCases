from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    bot_token: str
    admin_ids: str = ""
    database_url: str = "sqlite+aiosqlite:///./kemcases.db"
    min_withdrawal: int = 100
    webapp_url: str = "http://localhost:8000"
    ad_rewards_enabled: bool = False
    ad_callback_secret: str = ""
    video_daily_limit: int = 10
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    @property
    def admins(self) -> set[int]:
        return {int(x.strip()) for x in self.admin_ids.split(",") if x.strip().isdigit()}
settings = Settings()
