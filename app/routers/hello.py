from fastapi import APIRouter
from app.models.greeting import Greeting

router = APIRouter(prefix="/hello", tags=["hello"])

@router.get("/", response_model=Greeting)
async def say_hello(name: str = "World"):
    return Greeting(message=f"Hello, {name}!")
