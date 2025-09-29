from fastapi import APIRouter, Response, HTTPException, Depends, status

from src.model import Authentication

from src.auth import authenticate_user, create_access_token, get_current_user
from src.auth import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()


@router.post("/api/v1/auth")
async def login(response: Response, item: Authentication):

    user = await authenticate_user(item.username, item.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    
    access_token = create_access_token(data={"sub": user['username'], "groups": user['groups']})
    
    # Set HTTP-only cookie (key parameters explained below)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,  # Most important for security
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        # secure=True,  # Enable for production (HTTPS only)
        # samesite="Lax",  # Adjust based on your frontend setup
        path="/",  # Make cookie available for all routes
    )
    return {"id": user.get('username'), "message": "Login successful"}


@router.post("/logout")
async def logout(response: Response):
    """Clear the authentication cookie"""
    response.delete_cookie(
        key="access_token",
        httponly=True,
        path="/",
        # secure=True,
        # samesite="Lax"
    )
    return {"message": "Logged out"}


@router.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return {
        "username": current_user["username"],
        "email": current_user["email"],
        "full_name": current_user["full_name"]
    }