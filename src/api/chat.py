from uuid import uuid1
from datetime import datetime
from typing import Dict, AsyncGenerator

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse

from psycopg import AsyncConnection

from src.auth import get_current_user
from src.model import MessageRequest
from src.utils import get_agent, get_db_conn
from src.utils import SupervisorAgent

from src.api.db_model import get_conversations

import asyncio
import json

router = APIRouter()

async def stream_response(agent, content: str, conv_id: str, agent_id: str, user_id: str, user_message_id: str, agent_message_id: str):
    """
    Generator that yields:
    - Whitespace every second until response is ready
    - Final JSON data when available
    """
    yield " \n"

    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")

    task = asyncio.create_task(agent.ainvoke(content, idx=conv_id))

    while not task.done():
        yield " \n" 
        await asyncio.sleep(1)

    result = task.result()
    agent_content = result.get('messages')[-1].content

    # Prepare final JSON response (SSE format: data: {json}\n\n)
    data = {
        "userMessage": {
            "id": user_message_id,
            "content": content,
            "sender": "user",
            "timestamp": ts,
            "conversationId": conv_id
        },
        "agentMessage": {
            "id": agent_message_id,
            "content": agent_content,
            "sender": "agent",
            "agentId": agent_id,
            "timestamp": ts,
            "conversationId": conv_id
        }
    }

    # Send final data as SSE event
    yield json.dumps(data, ensure_ascii=False)

@router.post("/api/v1/message")
async def read_users_me(
    item: MessageRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    agent: SupervisorAgent = Depends(get_agent)
):
    
    user_message_id = str(uuid1())
    agent_message_id = str(uuid1())
    conv_id = item.conversationId
    agent_id = item.agentId
    content = item.content
    user_id = current_user.get('username')

    # Return StreamingResponse with generator
    return StreamingResponse(
        stream_response(agent, content, conv_id, agent_id, user_id, user_message_id, agent_message_id),
        media_type="text/event-stream"  
    )


@router.post("/api/v1/system_message")
async def read_users_me(
    item: MessageRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    agent: SupervisorAgent = Depends(get_agent)
):
    
    user_message_id = str(uuid1())
    agent_message_id = str(uuid1())
    conv_id = item.conversationId
    agent_id = item.agentId
    content = item.content
    user_id = current_user.get('username')

    message = 'Это системное сообщение. Пользователь не видит ответ на него. Отвечай, просто, `OK`. Сообщение:\n' + content
    result = await agent.ainvoke(message, idx=conv_id)

    return Response('{"result": "Success."}' if result else '{"result": "Success."}', status_code=200)



@router.get("/api/v1/conversations")
async def conversations(
    current_user: dict = Depends(get_current_user),
    aconn: AsyncConnection = Depends(get_db_conn)
):
    """
    Returns conversation json with all conversatino messages
    """
    # user_id = current_user.get('username')
    # conversatins = await get_conversations(aconn=aconn, user_id=user_id)

    return Response('Under construction', 404)