"""Agent runtime with tracing and retry logic."""

import asyncio
import uuid
from datetime import datetime
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from shared.config import get_settings
from observability.tracing import get_tracer
from .base import (
    Agent,
    AgentContext,
    AgentResult,
    AgentStatus,
    AgentError,
    AgentTimeoutError,
    AgentValidationError,
)


class AgentRuntime:
    """Runtime for executing agents with observability and retry logic."""

    def __init__(self):
        self.settings = get_settings()
        self.tracer = get_tracer()

    async def run(
        self,
        agent: Agent,
        input_data: dict,
        user_id: str,
        trace_id: Optional[str] = None,
        config: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> AgentResult:
        """Run an agent with full lifecycle management.

        Args:
            agent: Agent instance to run
            input_data: Input data for the agent
            user_id: User ID for context
            trace_id: Optional trace ID for distributed tracing
            config: Optional agent-specific configuration
            timeout: Optional timeout in seconds

        Returns:
            AgentResult with execution outcome

        Raises:
            AgentValidationError: If input validation fails
            AgentTimeoutError: If execution times out
            AgentError: If execution fails
        """
        # Generate IDs
        agent_id = f"{agent.name}_{uuid.uuid4().hex[:8]}"
        trace_id = trace_id or f"trace_{uuid.uuid4().hex}"

        # Create context
        context = AgentContext(
            agent_id=agent_id,
            user_id=user_id,
            trace_id=trace_id,
            input_data=input_data,
            config=config or {},
        )

        # Validate input
        if not agent.validate_input(input_data):
            raise AgentValidationError(
                f"Invalid input for agent {agent.name}"
            )

        # Start tracing
        with self.tracer.start_span(
            f"agent.{agent.name}",
            attributes={
                "agent.id": agent_id,
                "agent.name": agent.name,
                "agent.version": agent.version,
                "trace.id": trace_id,
                "user.id": user_id,
            },
        ):
            start_time = datetime.utcnow()

            try:
                # Run with timeout
                timeout_seconds = (
                    timeout or self.settings.agent_timeout
                )
                result = await asyncio.wait_for(
                    self._execute_with_retry(agent, context),
                    timeout=timeout_seconds,
                )

                return result

            except asyncio.TimeoutError:
                duration = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                return AgentResult(
                    status=AgentStatus.TIMEOUT,
                    error=f"Agent timed out after {timeout_seconds}s",
                    start_time=start_time,
                    end_time=datetime.utcnow(),
                    duration_ms=duration,
                )

            except Exception as e:
                duration = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                return AgentResult(
                    status=AgentStatus.FAILED,
                    error=str(e),
                    start_time=start_time,
                    end_time=datetime.utcnow(),
                    duration_ms=duration,
                )

    async def _execute_with_retry(
        self, agent: Agent, context: AgentContext
    ) -> AgentResult:
        """Execute agent with retry logic."""

        @retry(
            stop=stop_after_attempt(self.settings.agent_max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True,
        )
        async def _execute():
            start = datetime.utcnow()

            try:
                # Pre-execution hook
                await agent.before_execute(context)

                # Main execution
                result = await agent.execute(context)

                # Post-execution hook
                await agent.after_execute(context, result)

                return result

            except Exception as e:
                duration = (
                    datetime.utcnow() - start
                ).total_seconds() * 1000
                return AgentResult(
                    status=AgentStatus.FAILED,
                    error=str(e),
                    start_time=start,
                    end_time=datetime.utcnow(),
                    duration_ms=duration,
                )

        return await _execute()
