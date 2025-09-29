from typing import Optional 

from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings


class Authentication(BaseModel):
    username: str
    password: str

# Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class MessageRequest(BaseModel):
    conversationId: str
    content: str
    agentId: str

class AppConfig(BaseSettings):
    # Required variables (no default)
    API_KEY: str = Field(..., min_length=1, env="API_KEY")
    BASE_URL: str = Field(..., min_length=1, env="BASE_URL")
    FOLDER: str = Field(..., min_length=1, env="FOLDER")
    MODEL_NAME: str = Field(..., min_length=1, env="MODEL_NAME")
    MCP_CONFIG: str = Field(..., min_length=1, env="MCP_CONFIG")

    LDAP_SERVER: str = Field(..., min_length=1, env="LDAP_SERVER")
    LDAP_PORT: int = Field(..., allow_inf_nan=False, env="LDAP_PORT")
    
    # Optional variables with defaults
    LOG_LEVEL: str = Field('INFO', env="DEBUG")
    POSTGRESQL_URL: str = Field(None, env="POSTGRESQL_URL")

    class Config:
        # Extra configuration
        env_file = ".env"  # Optional: load from .env file
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra environment variables


