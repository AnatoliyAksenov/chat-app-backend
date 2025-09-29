from fastapi import APIRouter
from fastapi import Depends, FastAPI, HTTPException, status, Request, Response

from src.auth import get_current_user

router = APIRouter()

@router.get("/agent/")
async def read_users(current_user: dict = Depends(get_current_user)):
    ...