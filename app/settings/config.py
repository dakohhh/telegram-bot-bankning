import os
import certifi
from pathlib import Path
from dotenv import load_dotenv
from pydantic import Field
from functools import lru_cache
from typing import Literal, Union
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


EnvironmentType = Literal["development", "production"]

# Get current environment from env vars with type checking
PYTHON_ENV: EnvironmentType = os.getenv("PYTHON_ENV", "development")


# Core application paths
BASE_DIR: Path = Path(__file__).resolve().parent.parent
CERTIFICATE: str = os.path.join(os.path.dirname(certifi.__file__), "cacert.pem")
DOTENV: str = os.path.join(BASE_DIR, ".env")



class GlobalConfig(BaseSettings):
    """Base configuration class with shared settings across environments"""

    # Application metadata
    APP_NAME: str = Field("Telegram  Banking", env="APP_NAME")
    APP_VERSION: str = Field("1.0", env="APP_VERSION")
    APPLICATION_CERTIFICATE: str = Field(default=CERTIFICATE)
    BASE_DIR: Path = Field(default=BASE_DIR)

    ENVIRONMENT: EnvironmentType = PYTHON_ENV

    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")

    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # PAYSTACK
    PAYSTACK_BASE_URL: str  = Field(..., env="PAYSTACK_BASE_URL")
    PAYSTACK_SECRET_KEY: str = Field(..., env="PAYSTACK_SECRET_KEY")


class DevelopmentConfig(GlobalConfig):
    """Development environment specific configurations"""

    DEBUG: bool = True
    RABBITMQ_URL: str = Field("amqp://user:pass@localhost:5672", description="Local RabbitMQ instance")

class ProductionConfig(GlobalConfig):
    """Production environment specific configurations with stricter settings"""

    DEBUG: bool = False
    RABBITMQ_URL: str = Field(..., env="RABBITMQ_URL")
    


@lru_cache()
def get_settings() -> DevelopmentConfig | ProductionConfig:
    """
    Factory function to get environment-specific settings
    
    Returns:
        GlobalConfig: Configuration instance based on current environment
    
    Raises:
        ValueError: If PYTHON_ENV is invalid or not set
    """
    configs = {
        "development": DevelopmentConfig,
        "production": ProductionConfig
    }

    if not PYTHON_ENV or PYTHON_ENV not in configs:
        raise ValueError(f"Invalid deployment environment. Must be one of: {configs.keys()}")

    return configs[PYTHON_ENV]()


ConfigType = Union[GlobalConfig, DevelopmentConfig, ProductionConfig]

# Initialize settings instance
settings = get_settings()

# Uncomment the line below to check the settings set
# print(settings)
