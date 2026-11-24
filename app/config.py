from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    bot_token: str
    admin_ids: str = ""
    database_url: str = "sqlite+aiosqlite:///./kemcases.db"
    min_withdrawal: int = 100
    webapp_url: str = "http://localhost:8000"
    ad_rewards_enabled: bool = False
    ad_callback_secret: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def admins(self) -> set[int]:
        result = set()
        for item in self.admin_ids.split(","):
            item = item.strip()
            if item.isdigit():
                result.add(int(item))
        return result

settings = Settings()
