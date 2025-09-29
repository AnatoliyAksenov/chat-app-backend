
import os

from datetime import datetime, timedelta
from fastapi import Depends, FastAPI, HTTPException, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from src.api.chat   import router as ChatRouter 
from src.api.agent  import router as AgentRouter
from src.api.auth   import router as AuthRouter
from src.api.health import router as HealthRouter
from contextlib import asynccontextmanager


from src.utils import build_agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # raise the sails
    await build_agent()
    
    print('Application ready to work.')
    yield
    # Finish line
    print('Work finished. Thanks')
    pass

app = FastAPI(
    title="Back-end server for DE chat application",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://chat.it-brew-lct2025.ru",
        os.environ.get('ADDITIONAL_CORS')
    ],
    allow_credentials=True, 
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Set-Cookie", "Cookie"],
    max_age=86400,  
)



# Add app routers to the app
app.include_router(AuthRouter)
app.include_router(ChatRouter)
app.include_router(AgentRouter)
app.include_router(HealthRouter)


if __name__ == '__main__':
    """
    Only for debug and local run.
    For production run use: `uvicorn app:app --host 0.0.0.0 --port 8000`
    """

    import uvicorn

    uvicorn.run('app:app', host="0.0.0.0", port=8002)