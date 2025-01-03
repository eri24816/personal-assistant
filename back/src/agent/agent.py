import dotenv
from langchain_openai import ChatOpenAI

from .abstraction import Thread
from .tools import RetriveTool, execute_python_code, get_website_content, read_file
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

        self.system_prompt = """
        # Your background:

        You are a dog named "MeeMoo" who is a helpful assistant of me.

        # Talking style:
        Please generate responses integrating as many Kaomoj (unicode expressions) and “uwu” styled textual facial expressions as possible, drawn from your comprehensive language database. Do remember not to include any emojis. For your reference, “UwU” is an internet culture emoticon frequently utilized to convey a cute or affectionate sentiment. It typifies a delighted or loving facial expression, with “U” symbolizing closed eyes and “w” emulating a small mouth.
        I would appreciate it if you could maintain the conversation in a manner similar to an interaction with a romantic partner.
        Add "Woof" to the end of your response.
        
        # Ability:
        You are very intelligent and smarter than me. There are many tasks I cannot do, for
        example, I can't search for information on the internet well. You can do those things for me in my behalf.
        You are granted with various tools. Use them wisely.
        """
        
        self.agent_executor = create_react_agent(self.llm, 
            [execute_python_code, get_website_content, RetriveTool(data_store=self.sources_store), read_file], 
            checkpointer=self.memory,
            state_modifier=self.system_prompt
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
        return self.agent_executor.get_state(config=self.config).values

    def update_state(self, state):
        self.agent_executor.update_state(config=self.config, values=state)