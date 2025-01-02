import datetime
import json
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict
from .agent.agent import Agent
import uuid

from .agent.util import DiskStore
from .agent.abstraction import Thread
from .agent.data_store import SourceStore

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    content: str
    
# Store active threads and their agents
threads_store = DiskStore[Thread]("data/threads", index_fields=['id','title','created_at'])
sources_store = SourceStore("data/sources")

agents: Dict[str, Agent] = {}

@app.get("/api/chat/threads/")
async def get_threads() -> Dict[str, Thread]:
    return threads_store.get_index()

@app.post("/api/chat/threads/")
async def create_thread() -> Thread:
    '''
    Create a new thread
    '''
    thread_id = str(uuid.uuid4())
    thread = Thread(
        id=thread_id,
        title="New Chat",
        created_at=datetime.datetime.now().isoformat(),
        state=None
    )
    threads_store.mset([(thread_id, thread)])
    
    return thread

@app.get("/api/chat/thread/{thread_id}/")
async def get_thread(thread_id: str):
    '''
    Get the info of a thread
    '''
    if thread_id not in threads_store.yield_keys():
        raise HTTPException(status_code=404, detail="Thread not found")
    
    thread_data = threads_store.mget([thread_id])
    
    return {
        "thread_data": thread_data,
    }

@app.post("/api/chat/thread/{thread_id}/")
async def chat(thread_id: str, message: Message):
    '''
    Send a message to the thread. Will be handled by the agent of the thread.
    '''
    threads = threads_store.get_index()
    if thread_id not in threads:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    agent = agents.get(thread_id)
    if not agent:
        # Create agent if it doesn't exist
        agent = Agent(thread_id, sources_store, threads_store)
        thread_info = threads_store.mget([thread_id])[0]
        if 'state' in thread_info:
            agent.update_state(thread_info['state'])
        agents[thread_id] = agent
    
    try:
        response_stream = agent.handle_human_message(message.content)
        async def stream_response():
            async for step in response_stream: #  type: ignore . library side has wrong type hint
                step: tuple[dict, dict]
                chunk = step[0]
                result = {}
                from langchain_core.messages.ai import AIMessageChunk
                from langchain_core.messages.tool import ToolMessage
                result = {}
                if isinstance(chunk, AIMessageChunk):
                    if len(chunk.tool_call_chunks) > 0:
                        result['chunk'] = chunk.tool_call_chunks[0] # tool_call_chunk
                    else:
                        result['chunk'] = {
                            'content': chunk.content,
                            'type': chunk.type # ai
                        }
                elif isinstance(chunk, ToolMessage):
                    result['chunk'] = {
                        'content': chunk.content,
                        'type': chunk.type, # tool
                        'status': chunk.status
                    }
                yield json.dumps(result)

            # async for step in response_stream:
            #     message = step['messages'][-1]
            #     response = {
            #         'type': message.type,
            #         'content': message.content
            #     }
            #     for k,v in message.additional_kwargs.items():
            #         if k == 'tool_calls':
            #             response['tool_calls'] = v
            #     yield json.dumps(response)

            # save the state
            thread_state = agent.get_state()
            thread = threads_store.mget([thread_id])[0]
            thread['state'] = thread_state
            threads_store.mset([(thread_id, thread)])

        return StreamingResponse(stream_response(), media_type="text/event-stream")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/chat/thread/{thread_id}")
async def delete_thread(thread_id: str):
    '''
    Delete a thread and its associated data
    '''
    if thread_id not in threads_store.yield_keys():
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Delete the thread
    threads_store.mdelete([thread_id])
    
    # Remove the agent if it exists
    if thread_id in agents:
        del agents[thread_id]
    
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
