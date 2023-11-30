from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from bson import ObjectId

app = FastAPI()

# Функція для отримання підключення до бд
def get_database() -> AsyncIOMotorClient:
    return AsyncIOMotorClient("mongodb://localhost:27017")["mini_blog"]

# Залежність для отримання підключення до бд
async def get_db() -> AsyncIOMotorClient:
    # Отримую коннект до бд
    db = get_database()
    try:
        yield db
    finally:
        # Закриваю коннект після траю
        db.client.close()

# Базова модель
class Base(BaseModel):
    class Config:
        # Вказую FastAPI юзати orm_mode для автоматичного перетворення моделей
        orm_mode = True

# Модель для категорії
class CategoryCreate(Base):
    name: str

class Category(CategoryCreate):
    id: str

# Модель для автора
class AuthorCreate(Base):
    name: str

class Author(AuthorCreate):
    id: str

# Модель для статті
class ArticleCreate(Base):
    title: str
    text: str
    category_id: ObjectId
    author_id: ObjectId
    tags: list[str] = Field(default_factory=list)

class Article(ArticleCreate):
    id: str

# Маршрути
@app.post("/categories/", response_model=Category)
async def create_category(category: CategoryCreate, db: AsyncIOMotorClient = Depends(get_db)):
    category_dict = jsonable_encoder(category)
    result = await db.categories.insert_one(category_dict)
    category.id = str(result.inserted_id)
    return category

@app.post("/authors/", response_model=Author)
async def create_author(author: AuthorCreate, db: AsyncIOMotorClient = Depends(get_db)):
    author_dict = jsonable_encoder(author)
    result = await db.authors.insert_one(author_dict)
    author.id = str(result.inserted_id)
    return author

@app.post("/articles/", response_model=Article)
async def create_article(article: ArticleCreate, db: AsyncIOMotorClient = Depends(get_db)):
    category, author = await db.categories.find_one({"_id": article.category_id}), await db.authors.find_one({"_id": article.author_id})
    if not category or not author:
        raise HTTPException(status_code=404, detail="Категорія або Автор не знайдені")
    article_dict = jsonable_encoder(article)
    result = await db.articles.insert_one(article_dict)
    article.id = str(result.inserted_id)
    return article

@app.get("/articles/{article_id}", response_model=Article)
async def read_article(article_id: str, db: AsyncIOMotorClient = Depends(get_db)):
    article = await db.articles.find_one({"_id": ObjectId(article_id)})
    if article:
        return article
    raise HTTPException(status_code=404, detail="Стаття не знайдена")

@app.put("/articles/{article_id}", response_model=Article)
async def update_article(article_id: str, article: ArticleCreate, db: AsyncIOMotorClient = Depends(get_db)):
    category, author = await db.categories.find_one({"_id": article.category_id}), await db.authors.find_one({"_id": article.author_id})
    if not category or not author:
        raise HTTPException(status_code=404, detail="Категорія або Автор не знайдені")
    article_dict = jsonable_encoder(article)
    await db.articles.update_one({"_id": ObjectId(article_id)}, {"$set": article_dict})
    article.id = article_id
    return article

@app.delete("/articles/{article_id}", response_model=dict)
async def delete_article(article_id: str, db: AsyncIOMotorClient = Depends(get_db)):
    # Видаляю статтю та повертаю отвєтку про успішне видалення
    result = await db.articles.delete_one({"_id": ObjectId(article_id)})
    if result.deleted_count == 1:
        return {"status": "success", "message": "Стаття видалена"}
    raise HTTPException(status_code=404, detail="Стаття не знайдена")
