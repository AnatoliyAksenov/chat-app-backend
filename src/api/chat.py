import asyncio
import io
import json
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, Optional
from uuid import uuid1

import docx
import fitz
import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from psycopg import AsyncConnection

from src.api.db_model import get_conversations
from src.auth import get_current_user
from src.model import MessageRequest
from src.utils import SupervisorAgent, get_agent, get_db_conn

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


@router.post("/api/v1/upload_document")
async def upload_document(
    conversation_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    agent: SupervisorAgent = Depends(get_agent)
):
    """
    Upload a document and extract text content for the agent
    Supported formats: pdf, doc, docx, xls, xlsx, csv, txt, md, ipynb, json, xml
    """
    
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 100 MB
    file_content = await file.read()
    
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5 MB.")
    
    # Reset file pointer for processing
    file.file.seek(0)
    
    try:
        # Extract text based on file type
        extracted_text = await extract_text_from_file(file, file_content)
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="No text content found in the document")
        
        # Generate message IDs
        user_message_id = str(uuid1())
        agent_message_id = str(uuid1())
        
        # Use the original conversation ID or create a new one
        conv_id = conversation_id or str(uuid1())
        agent_id = "document_processor"  
        user_id = current_user.get('username')
        
        # Create a message with the extracted text
        message = f'Это системное сообщение. Пользователь не видит ответ на него. Отвечай, просто, `OK`. Документ:{file.filename}\nСодержимое:\n{extracted_text}\n'
        print(message)
        # Return StreamingResponse with the extracted text
        return StreamingResponse(
            stream_response(agent, message, conv_id, agent_id, user_id, user_message_id, agent_message_id),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


async def extract_text_from_file(file: UploadFile, file_content: bytes) -> str:
    """Extract text from various document formats"""
    
    filename = file.filename.lower()
    file_extension = filename.split('.')[-1] if '.' in filename else ''
    
    try:
        if file_extension == 'pdf':
            return extract_text_from_pdf(file_content)
        elif file_extension in ['doc', 'docx']:
            return extract_text_from_docx(file_content)
        elif file_extension in ['xls', 'xlsx']:
            return extract_text_from_excel(file_content)
        elif file_extension == 'csv':
            return extract_text_from_csv(file_content)
        elif file_extension in ['txt', 'md', 'ipynb', 'json', 'xml']:
            return extract_text_from_text(file_content)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file format: {file_extension}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text from {file_extension}: {str(e)}")


def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF using PyMuPDF"""
    text_parts = []
    
    # Open PDF from bytes
    pdf_document = fitz.open(stream=file_content, filetype="pdf")
    
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text = page.get_text()
        text_parts.append(text)
    
    pdf_document.close()
    return "\n".join(text_parts)


def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX files"""
    doc = docx.Document(io.BytesIO(file_content))
    text_parts = []
    
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text)
    
    # Extract text from tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    text_parts.append(cell.text)
    
    return "\n".join(text_parts)


def extract_text_from_excel(file_content: bytes) -> str:
    """Extract text from Excel files (XLS, XLSX)"""
    excel_file = io.BytesIO(file_content)
    text_parts = []
    
    # Read all sheets
    xl = pd.ExcelFile(excel_file)
    
    for sheet_name in xl.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        text_parts.append(f"--- Sheet: {sheet_name} ---")
        
        # Convert dataframe to string representation
        if not df.empty:
            # For small datasets, include all data
            if len(df) <= 100:  # Limit to 100 rows to avoid huge outputs
                text_parts.append(df.to_string(index=False))
            else:
                # For large datasets, include sample and column info
                text_parts.append("Dataset too large, showing first 10 rows:")
                text_parts.append(df.head(10).to_string(index=False))
                text_parts.append(f"... and {len(df) - 10} more rows")
        
        text_parts.append("")  # Add empty line between sheets
    
    return "\n".join(text_parts)


def extract_text_from_csv(file_content: bytes) -> str:
    """Extract text from CSV files"""
    csv_file = io.BytesIO(file_content)
    
    try:
        # Try to detect encoding
        df = pd.read_csv(csv_file)
        
        text_parts = []
        if not df.empty:
            # For small datasets, include all data
            if len(df) <= 100:  # Limit to 100 rows
                text_parts.append(df.to_string(index=False))
            else:
                # For large datasets, include sample
                text_parts.append("Dataset too large, showing first 10 rows:")
                text_parts.append(df.head(10).to_string(index=False))
                text_parts.append(f"... and {len(df) - 10} more rows")
        
        return "\n".join(text_parts)
        
    except Exception as e:
        # If pandas fails, try reading as plain text
        try:
            csv_file.seek(0)
            return csv_file.read().decode('utf-8')
        except:
            return f"CSV content (raw): {csv_file.getvalue().decode('utf-8', errors='ignore')}"


def extract_text_from_text(file_content: bytes) -> str:
    """Extract text from plain text files (TXT, MD)"""
    try:
        return file_content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return file_content.decode('latin-1')
        except:
            return file_content.decode('utf-8', errors='ignore')