from fastapi import FastAPI
from contextlib import asynccontextmanager

from api import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    yield
    print("Shutting down...")


app = FastAPI(lifespan=lifespan)

app.include_router(router)
