import asyncio

from fastapi import APIRouter
from fastapi import Response
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.get('/healthcheck')
async def healthcheck():
    return Response("I'm OK", 200)


@router.get('/ping')
async def pong():
    return Response("pong", 200)


@router.get('/get_400')
async def get_400():
    return Response('Test 400', 400)


@router.get('/get_401')
async def get_400():
    return Response('Access denied 401', 401)


@router.get('/get_403')
async def get_400():
    return Response('Permissions denied', 403)


@router.get('/get_404')
async def get_400():
    return Response('Test page not found', 404)


@router.get('/get_streaming')
async def get_400():
    async def fake_streaming():
        for x in range(100):
            yield " "
            await asyncio.timeout(0.1)
        yield '{"test": "result"}'

    return StreamingResponse(fake_streaming(), media_type="application/json")