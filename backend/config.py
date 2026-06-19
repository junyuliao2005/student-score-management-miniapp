import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    DEBUG = os.getenv('FLASK_ENV', 'development') == 'development'

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-dev-secret')
    JWT_EXPIRE_HOURS = 2

    # MySQL
    DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'student_grade_db')
    DB_USER_SAFE = quote_plus(DB_USER)
    DB_PASSWORD_SAFE = quote_plus(DB_PASSWORD)
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER_SAFE}:{DB_PASSWORD_SAFE}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        f"?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = int(os.getenv('SQLALCHEMY_POOL_SIZE', 5))
    SQLALCHEMY_MAX_OVERFLOW = int(os.getenv('SQLALCHEMY_MAX_OVERFLOW', 15))
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': SQLALCHEMY_POOL_SIZE,
        'max_overflow': SQLALCHEMY_MAX_OVERFLOW,
        'pool_recycle': 3600,
    }

    # AI 模块
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'mock')
    AI_API_BASE_URL = os.getenv('AI_API_BASE_URL', '')
    AI_API_KEY = os.getenv('AI_API_KEY', '')
    AI_MODEL = os.getenv('AI_MODEL', 'qwen-turbo')
    AI_TIMEOUT = int(os.getenv('AI_TIMEOUT', 30))
    AI_MAX_INPUT_CHARS = int(os.getenv('AI_MAX_INPUT_CHARS', 6000))
    AI_MOCK_ENABLED = os.getenv('AI_MOCK_ENABLED', 'true').lower() == 'true'
    AI_SAVE_PROMPT = os.getenv('AI_SAVE_PROMPT', 'false').lower() == 'true'
    AI_SAFETY_ENABLED = os.getenv('AI_SAFETY_ENABLED', 'true').lower() == 'true'

    # AI 视觉模型配置（本版本默认仅 mock 演示，不主动调用外部 API）
    AI_VISION_PROVIDER = os.getenv('AI_VISION_PROVIDER', 'openai_compatible_vision')
    AI_VISION_API_BASE_URL = os.getenv('AI_VISION_API_BASE_URL', '')
    AI_VISION_API_KEY = os.getenv('AI_VISION_API_KEY', '')
    AI_VISION_MODEL = os.getenv('AI_VISION_MODEL', '')
    AI_VISION_TIMEOUT = int(os.getenv('AI_VISION_TIMEOUT', 60))
    AI_VISION_MAX_IMAGE_MB = int(os.getenv('AI_VISION_MAX_IMAGE_MB', 10))


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {}
