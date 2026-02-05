"""Base agent interface and contracts."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AgentContext(BaseModel):
    """Context passed to agent during execution."""

    agent_id: str
    user_id: str
    trace_id: str
    input_data: Dict[str, Any]
    config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Result returned by agent."""

    status: AgentStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Execution metrics
    start_time: datetime
    end_time: datetime
    duration_ms: float

    # Tool calls made by agent
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class Agent(ABC):
    """Base class for all agents.

    Agents are autonomous units that:
    1. Accept structured input (via AgentContext)
    2. Execute a specific task (using tools)
    3. Return structured output (via AgentResult)
    4. Are traceable and observable
    """

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.description = self.__doc__ or "No description"

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute the agent's main logic.

        Args:
            context: Agent execution context with input data

        Returns:
            AgentResult with status and output

        Raises:
            AgentError: If execution fails
        """
        pass

    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data before execution.

        Args:
            input_data: Input data to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    async def before_execute(self, context: AgentContext) -> None:
        """Hook called before execute().

        Override to add pre-execution logic (e.g., setup, validation).
        """
        pass

    async def after_execute(
        self, context: AgentContext, result: AgentResult
    ) -> None:
        """Hook called after execute().

        Override to add post-execution logic (e.g., cleanup, logging).
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Get agent metadata."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
        }


class AgentError(Exception):
    """Base exception for agent errors."""

    pass


class AgentTimeoutError(AgentError):
    """Raised when agent execution times out."""

    pass


class AgentValidationError(AgentError):
    """Raised when agent input validation fails."""

    pass
