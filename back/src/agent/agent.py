import dotenv
from langchain_openai import ChatOpenAI

from .abstraction import Thread
from .tools import RetriveTool, execute, get_website_content
from .data_store import SourceStore
from langchain_core.documents import Document
from langchain import hub
from langgraph.graph import MessagesState
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import List
from langchain_core.runnables import RunnableConfig

from langgraph.prebuilt import create_react_agent
from .util import DiskStore

# Define state for application
class State(MessagesState):
    context: List[Document]

class Agent:
    def __init__(self, thread_id: str, sources_store: SourceStore, threads_store: DiskStore[Thread]):
        self.sources_store = sources_store
        self.prompt = hub.pull("rlm/rag-prompt")
        dotenv.load_dotenv()
        
        self.llm = ChatOpenAI(model="gpt-4o-mini")

        self.memory = MemorySaver()
        
        self.agent_executor = create_react_agent(self.llm, 
            [execute, get_website_content, RetriveTool(data_store=self.sources_store)], 
            checkpointer=self.memory                                 
        )

        self.config: RunnableConfig = {
            "configurable": {
                "thread_id": thread_id
            }
        }

    async def handle_human_message(self, message: str):
        async for step in self.agent_executor.astream(
            {"messages": [{"role": "user", "content": message}]},
            stream_mode="messages",
            config=self.config,
        ):
            yield step

    def get_state(self):
        return self.agent_executor.get_state(config=self.config)

    def update_state(self, state):
        self.agent_executor.update_state(config=self.config, values=state)