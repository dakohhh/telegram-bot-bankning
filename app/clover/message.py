from pydantic import BaseModel, Field
from typing import Union, Literal, Optional

class BaseMessage(BaseModel):
    role: str

class SystemMessage(BaseMessage):
    role: Literal["system"] = Field(default="system")
    content: str

class HumanMessage(BaseMessage):
    role: Literal["human"] = Field(default="human")
    content: str

class AssistantMessage(BaseMessage):
    role: Literal["assistant"] = Field(default="assistant")
    content: Optional[str] = None
    tool_call: Optional[dict] = None 

Message = Union[SystemMessage, HumanMessage, AssistantMessage]