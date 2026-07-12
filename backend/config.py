import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()


def _env_bool(name, default=False):
    return os.getenv(name, str(default).lower()).strip().lower() in ('1', 'true', 'yes', 'on')


def validate_runtime_config(config):
    """Fail closed when production secrets or database settings are missing/weak."""
    if not config.get('IS_PRODUCTION'):
        return

    required = ('SECRET_KEY', 'JWT_SECRET_KEY', 'DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME')
    missing = [name for name in required if not str(config.get(name) or '').strip()]
    weak_values = {'dev-secret-key', 'jwt-dev-secret', 'change-me', '123456', 'password'}
    weak = [
        name for name in ('SECRET_KEY', 'JWT_SECRET_KEY', 'DB_PASSWORD')
        if str(config.get(name) or '').strip().lower() in weak_values
    ]
    if missing or weak:
        problems = []
        if missing:
            problems.append('missing: ' + ', '.join(missing))
        if weak:
            problems.append('weak/default: ' + ', '.join(weak))
        raise RuntimeError('Unsafe production configuration (' + '; '.join(problems) + ')')


class Config:
    # Flask
    FLASK_ENV = os.getenv('FLASK_ENV', 'development').strip().lower()
    IS_PRODUCTION = FLASK_ENV == 'production'
    SECRET_KEY = os.getenv('SECRET_KEY', '' if IS_PRODUCTION else 'dev-only-secret-change-before-deploy')
    DEBUG = FLASK_ENV == 'development'

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', '' if IS_PRODUCTION else 'dev-only-jwt-change-before-deploy')
    JWT_EXPIRE_HOURS = int(os.getenv('JWT_EXPIRE_HOURS', 2))

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
    AI_MOCK_ENABLED = _env_bool('AI_MOCK_ENABLED', True)
    AI_SAVE_PROMPT = _env_bool('AI_SAVE_PROMPT', False)
    AI_SAFETY_ENABLED = _env_bool('AI_SAFETY_ENABLED', True)
    AI_FALLBACK_ENABLED = _env_bool('AI_FALLBACK_ENABLED', True)
    AI_TIMEOUT_SECONDS = int(os.getenv('AI_TIMEOUT_SECONDS', 90))
    AI_MAX_RETRIES = min(max(int(os.getenv('AI_MAX_RETRIES', 2)), 0), 2)

    # DeepSeek V4 Pro uses the Chat Completions endpoint only.
    DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    DEEPSEEK_CHAT_ENDPOINT = os.getenv('DEEPSEEK_CHAT_ENDPOINT', '/chat/completions')
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-v4-pro')
    DEEPSEEK_THINKING_ENABLED = _env_bool('DEEPSEEK_THINKING_ENABLED', True)
    DEEPSEEK_REASONING_EFFORT = os.getenv('DEEPSEEK_REASONING_EFFORT', 'max')

    # AI 视觉模型配置（本版本默认仅 mock 演示，不主动调用外部 API）
    AI_VISION_PROVIDER = os.getenv('AI_VISION_PROVIDER', 'openai_compatible_vision')
    AI_VISION_API_BASE_URL = os.getenv('AI_VISION_API_BASE_URL', '')
    AI_VISION_API_KEY = os.getenv('AI_VISION_API_KEY', '')
    AI_VISION_MODEL = os.getenv('AI_VISION_MODEL', '')
    AI_VISION_TIMEOUT = int(os.getenv('AI_VISION_TIMEOUT', 60))
    AI_VISION_MAX_IMAGE_MB = int(os.getenv('AI_VISION_MAX_IMAGE_MB', 10))

    # OCR is optional; core backend starts even when RapidOCR is not installed.
    OCR_PROVIDER = os.getenv('OCR_PROVIDER', 'mock')
    OCR_FALLBACK_ENABLED = _env_bool('OCR_FALLBACK_ENABLED', True)
    OCR_MAX_PIXELS = int(os.getenv('OCR_MAX_PIXELS', 24_000_000))
    OCR_MAX_DIMENSION = int(os.getenv('OCR_MAX_DIMENSION', 10_000))
    OCR_NORMALIZE_MAX_SIDE = int(os.getenv('OCR_NORMALIZE_MAX_SIDE', 3000))
    OCR_PREVIEW_DIR = os.getenv('OCR_PREVIEW_DIR', '').strip()
    SCORE_IMPORT_PREVIEW_DIR = os.getenv('SCORE_IMPORT_PREVIEW_DIR', '').strip()
    USER_IMPORT_PREVIEW_DIR = os.getenv('USER_IMPORT_PREVIEW_DIR', '').strip()
    IMPORT_PREVIEW_TTL_SECONDS = int(os.getenv('IMPORT_PREVIEW_TTL_SECONDS', 1800))

    CLOUD_UPLOAD_ALLOWED_HOST_SUFFIXES = tuple(
        item.strip().lower()
        for item in os.getenv(
            'CLOUD_UPLOAD_ALLOWED_HOST_SUFFIXES',
            '.tcb.qcloud.la,.tcloudbaseapp.com,.myqcloud.com,.cloudbase.net',
        ).split(',')
        if item.strip()
    )


class TestConfig(Config):
    TESTING = True
    IS_PRODUCTION = False
    SECRET_KEY = 'test-secret-not-for-production'
    JWT_SECRET_KEY = 'test-jwt-not-for-production'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {}
