import asyncio
import json

from pydantic import ValidationError

from langchain_core.prompts import PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.model import AppConfig
from src.prompts import main as main_prompt

# from langfuse import Langfuse
# from langfuse.langchain import CallbackHandler

# langfuse = Langfuse(
#     public_key="pk-lf-b250746b-10e2-49f6-aca0-af44c4a161b9",
#     secret_key="sk-lf-067b3500-1e8e-4b0a-81c8-a1ffeb49964b",
#     host="https://langfuse.it-brew-lct2025.ru"
# )

# langfuse_handler = CallbackHandler()

_config: dict = None

def get_config():
    global _config
    if _config:
        return _config
    
    try:
        # This will automatically read from environment variables
        # or .env file
        config = AppConfig()
        return config
    
    except ValidationError as e:
        print("Configuration error:")
        print(e.errors())
        # Exit or handle error appropriately
        raise


class SupervisorAgent():

    def __init__(self, api_key: str, base_url: str, folder: str, model: str, tools: list, checkpointer: BaseCheckpointSaver): 
        self.api_key = api_key
        self.base_url = base_url
        self.folder =  folder
        self.model = model
        self.tools = tools
        self.checkpointer = checkpointer
        
        self.llm = ChatOpenAI(api_key=self.api_key, base_url=self.base_url, model=self.model)
        self.agent = create_react_agent(self.llm, tools=self.tools, prompt=main_prompt, checkpointer=checkpointer)

    @classmethod
    async def create(cls, api_key: str, base_url: str, folder: str, model: str, mcp_configs: dict, pg_conf: str): 
        
        client = MultiServerMCPClient(mcp_configs)
        tools = await client.get_tools() 

        if pg_conf:
            aconn = await AsyncConnection.connect(pg_conf, autocommit=True, row_factory=dict_row)
            
            checkpointer = AsyncPostgresSaver(aconn)
            await checkpointer.setup()
            
            return cls(api_key=api_key, base_url=base_url, folder=folder, model=model, tools=tools, checkpointer=checkpointer)
        else:
            checkpointer = InMemorySaver()
            return cls(api_key=api_key, base_url=base_url, folder=folder, model=model, tools=tools, checkpointer=checkpointer)

    
    async def ainvoke(self, message, idx: int):
        config = {
            "configurable": {"thread_id": str(idx)}, 
            "recursion_limit": 50, 
            #"callbacks": [langfuse_handler]
            }
        message_input = {"messages": [{"role": "user", "content": message}]}

        return await self.agent.ainvoke(message_input,config=config)

    
    
_agent = None    

async def build_agent():
    global _agent
    conf = get_config()
    _agent = await SupervisorAgent.create(
        api_key=conf.API_KEY, 
        base_url=conf.BASE_URL, 
        folder=conf.FOLDER, 
        model=conf.MODEL_NAME,
        mcp_configs=json.load(open(conf.MCP_CONFIG,"r")),
        pg_conf=conf.POSTGRESQL_URL
        )


def get_agent():
    return _agent

_db:AsyncConnection = None

async def get_db_conn() -> AsyncConnection:
    global _db
    if _db:
        return _db
    else:
        conf = get_config()
        aconn = await AsyncConnection.connect(conf.POSTGRESQL_URL)
        _db = aconn
        return _db
