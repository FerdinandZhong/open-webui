import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings."""
    
    # OpenAI Configuration
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    use_llm: bool = os.getenv("USE_LLM", "true").lower() == "true"
    
    # SDN Data Configuration
    sdn_file_path: str = os.getenv("SDN_FILE_PATH", "/home/cdsw/data_list/sdn_final.csv")
    
    # API Configuration
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    
    # Search Configuration
    max_search_results: int = int(os.getenv("MAX_SEARCH_RESULTS", "10"))
    name_match_threshold: float = float(os.getenv("NAME_MATCH_THRESHOLD", "0.4"))
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()