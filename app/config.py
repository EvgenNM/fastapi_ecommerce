import os
from dotenv import load_dotenv


load_dotenv()


SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

TOKEN_URL = 'users/token'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
NAME_TOKEN_HEAD = 'Bearer'
