from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuracion de la aplicacion VitalSync.
    Carga automaticamente desde .env usando pydantic-settings.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Database
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "vitalsync"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"

    # Application
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key-change-in-production"

    # JWT
    JWT_SECRET: str = "jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @property
    def DATABASE_URL(self) -> str:
        """URL de conexion async para PostgreSQL"""
        return f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """URL de conexion sync para PostgreSQL (Alembic)"""
        return f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"


# Singleton de configuracion
settings = Settings()
