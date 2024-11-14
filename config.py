import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    telegram_token: str = os.getenv("TELEGRAM_TOKEN")

    openai_api_key: str = os.getenv("OPENAI_API_KEY")

    amplitude_api_key: str = os.getenv("AMPLITUDE_API_KEY")

    db_host: str = os.getenv("DB_HOST")
    db_port: int = os.getenv("DB_PORT")
    db_name: str = os.getenv("DB_NAME")
    db_user: str = os.getenv("DB_USER")
    db_pass: str = os.getenv("DB_PASS")

    assistant_who_is_id: str = os.getenv("ASSISTANT_WHO_IS_ID")
    assistant_who_need_id: str = os.getenv("ASSISTANT_WHO_NEED_ID")
    assistant_what_can_id: str = os.getenv("ASSISTANT_WHAT_CAN_IS_ID")

    @property
    def get_database_url(self):
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()

