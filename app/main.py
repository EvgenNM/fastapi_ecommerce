from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

import app.config as conf
from app.log import log_middleware
from app.middlewares import TimingMiddleware
from app.routers import categories, products, users, reviews

app = FastAPI()


app_v1 = FastAPI(
    title="FastAPI Интернет-магазин",
    version="0.1.0",
)

# Подключаем маршруты категорий
app_v1.include_router(categories.router)
app_v1.include_router(products.router)
app_v1.include_router(users.router)
app_v1.include_router(reviews.router)


app.mount('/api/v1', app_v1)

app.add_middleware(
    GZipMiddleware, minimum_size=conf.MIDDLEWARE_GZIP_MINIMUM_SIZE
)
# app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=conf.MIDDLEWARE_TRUSTED_HOST_ALLOWED_HOSTS
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=conf.MIDDLEWARE_CORS_ALLOW_ORIGINS,
    allow_credentials=conf.MIDDLEWARE_CORS_ALLOW_CREDENTIALS,
    allow_methods=conf.MIDDLEWARE_CORS_ALLOW_METHODS,
    allow_headers=conf.MIDDLEWARE_CORS_ALLOW_HEADERS,
)
app.add_middleware(TimingMiddleware)
app.middleware("http")(log_middleware)

@app.get("/")
async def root():
    """
    Корневой маршрут, подтверждающий, что API работает.
    """
    return {"message": "Добро пожаловать в API интернет-магазина!"}