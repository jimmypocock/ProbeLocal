"""Custom streaming handler for LangChain with FastAPI integration"""
import asyncio
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
import json
from queue import Queue
from threading import Thread

from langchain.callbacks.base import AsyncCallbackHandler, BaseCallbackHandler
from langchain.schema import LLMResult
from langchain.schema.messages import BaseMessage
from langchain.schema.agent import AgentAction, AgentFinish
from langchain.schema.output import ChatGenerationChunk, GenerationChunk


class StreamingResponseHandler(BaseCallbackHandler):
    """Handler that puts tokens into a queue for streaming"""
    
    def __init__(self):
        self.queue = Queue()
        self.done = False
        
    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Called when a new token is generated"""
        self.queue.put(token)
        
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM finishes generating"""
        self.queue.put(None)  # Signal end of stream
        self.done = True
        
    def on_llm_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """Called when LLM encounters an error"""
        self.queue.put(None)  # Signal end of stream
        self.done = True


class AsyncStreamingResponseHandler(AsyncCallbackHandler):
    """Async handler for streaming responses"""
    
    def __init__(self):
        self.queue = asyncio.Queue()
        self.done = False
        
    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Called when a new token is generated"""
        await self.queue.put(token)
        
    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM finishes generating"""
        await self.queue.put(None)  # Signal end of stream
        self.done = True
        
    async def on_llm_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """Called when LLM encounters an error"""
        await self.queue.put(None)  # Signal end of stream
        self.done = True


def create_streaming_response(handler: StreamingResponseHandler):
    """Create a generator for FastAPI streaming response"""
    while True:
        token = handler.queue.get()
        if token is None:
            break
        # Format as Server-Sent Events (SSE)
        yield f"data: {json.dumps({'token': token})}\n\n"
    yield f"data: {json.dumps({'done': True})}\n\n"


async def create_async_streaming_response(handler: AsyncStreamingResponseHandler):
    """Create an async generator for FastAPI streaming response"""
    while True:
        token = await handler.queue.get()
        if token is None:
            break
        # Format as Server-Sent Events (SSE)
        yield f"data: {json.dumps({'token': token})}\n\n"
    yield f"data: {json.dumps({'done': True})}\n\n"