from fastapi import FastAPI

from app.routers import categories, products, users, reviews

app = FastAPI()

# Создаём приложение FastAPI
app_v1 = FastAPI(
    title="FastAPI Интернет-магазин",
    version="0.1.0",
)

# Подключаем маршруты категорий
app_v1.include_router(categories.router)
app_v1.include_router(products.router)
app_v1.include_router(users.router)
app_v1.include_router(reviews.router)


app.mount('/v1', app_v1)


# Корневой эндпоинт для проверки
@app.get("/")
async def root():
    """
    Корневой маршрут, подтверждающий, что API работает.
    """
    return {"message": "Добро пожаловать в API интернет-магазина!"}