"""Core Pydantic data models for the d4 framework."""
from pydantic import BaseModel, Field
from typing import Optional


class AgentStep(BaseModel):
    """A single step in a multi-agent task plan."""
    agent: str
    tool: str
    params: dict = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    parallel: bool = False


class Task(BaseModel):
    """A task to be executed by one or more agents."""
    id: str
    description: str
    context: dict = Field(default_factory=dict)
    session_id: str
    agent_plan: list[AgentStep] = Field(default_factory=list)


class AgentResponse(BaseModel):
    """Response from an agent after executing a tool."""
    status: str  # "success" | "error" | "pending_approval"
    summary: str
    confidence: float = 0.0
    artifacts: dict = Field(default_factory=dict)
    requires_approval: bool = False
    error: Optional[str] = None


class ToolInfo(BaseModel):
    """Metadata about an MCP tool exposed by an agent."""
    name: str
    description: str
    parameters: dict = Field(default_factory=dict)


class Capability(BaseModel):
    """A capability that an agent provides."""
    name: str
    version: str = "1.0"
    tools: list[ToolInfo] = Field(default_factory=list)


class AgentInfo(BaseModel):
    """Information about a registered agent."""
    name: str = Field(min_length=4)
    command: str
    transport: str = "stdio"
    capabilities: list[str] = Field(default_factory=list)
