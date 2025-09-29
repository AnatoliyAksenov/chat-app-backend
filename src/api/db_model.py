import os
from psycopg import AsyncConnection

async def get_conversations(aconn:AsyncConnection, user_id:str):
    q = """SELECT jsonb_build_object(
                 'id', c.id,
                 'agentId', c.agent_id,
                 'title', c.title,
                 'createdAt', c.created_at,
                 'lastMessageAt', c.last_message_at,
                 'messages', COALESCE((
                     SELECT jsonb_agg(
                         jsonb_build_object(
                             'id', m.id,
                             'content', m.content,
                             'sender', m.sender,
                             'agentId', m.agent_id,
                             'timestamp', m.timestamp,
                             'conversationId', m.conversation_id
                         )
                         ORDER BY m.timestamp
                     )
                     FROM messages m
                     WHERE m.conversation_id = c.id
                 ), '[]'::jsonb)
             ) AS conversation_json
             FROM conversations c
             WHERE c.user_id =  %(user_id)s"""
    cursor = await aconn.execute(q, {"user_id": user_id})
    res = await cursor.fetchall()

    return res

