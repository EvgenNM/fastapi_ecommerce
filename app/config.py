import os
import uuid
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()


SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

TOKEN_URL = 'users/token'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
NAME_TOKEN_HEAD = 'Bearer'

MIDDLEWARE_CORS_ALLOW_ORIGINS = [
    "http://localhost:3000",
    "https://example.com",
    "null"
]
MIDDLEWARE_CORS_ALLOW_CREDENTIALS = True
MIDDLEWARE_CORS_ALLOW_METHODS = ['*']
MIDDLEWARE_CORS_ALLOW_HEADERS = ['*']
MIDDLEWARE_TRUSTED_HOST_ALLOWED_HOSTS = [
    "example.com",
    "*.example.com",
    "localhost",
    "127.0.0.1"
]
MIDDLEWARE_GZIP_MINIMUM_SIZE = 500

# По логированию
LOGGER_FILE = 'info.log'
LOGGER_FORMAT = 'Log: [{extra[log_id]}:{time} - {level} - {message}]'
LOGGER_LEVEL = 'INFO'
# новый файл при достижении 10 МБ
LOGGER_ROTATION = '10 MB'
#  хранить логи только 10 дней
LOGGER_RETENTION = '10 days'
LOGGER_COMPRESSION = 'zip'
LOGGER_ENQUEUE = True
LOGGER_WARNING_LIST_STATUS_CODE = [401, 402, 403, 404]
LOGGER_EXCEPTION_STATUS_CODE = 500

# :::МЕДИА:::
DIRECTORY_USER_CONTENT = 'media'
DIRECTORY_IMAGE_PRODUCTS = 'products'
# Абсолютный путь к корню проекта, где Path(__file__) это путь к
# текущему файлу, а .resolve() абсолютный путь
# (без .., без символических ссылок) и .parent.parent поднимаемся
# на 2 уровня вверх, то есть корень проекта
BASE_DIR = Path(__file__).resolve().parent.parent
# MEDIA_ROOT - Физическая папка на диске, куда сохраняются все изображения.
MEDIA_ROOT = BASE_DIR / DIRECTORY_USER_CONTENT / DIRECTORY_IMAGE_PRODUCTS
# И .mkdir(parents=True, exist_ok=True) создаёт папку, если её нет
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
# ALLOWED_IMAGE_TYPES - Белый список MIME-типов.
# Защищает от загрузки файлов с не нужным расширением
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
# MAX_IMAGE_SIZE - Ограничение размера изображения
MAX_IMAGE_SIZE = 2 * 1024 * 1024
