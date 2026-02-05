"""Agent registry for discovering and instantiating agents."""

from typing import Dict, Type, Optional
from .base import Agent, AgentError


class AgentRegistry:
    """Global registry for agent classes."""

    _agents: Dict[str, Type[Agent]] = {}

    @classmethod
    def register(cls, name: str, agent_class: Type[Agent]) -> None:
        """Register an agent class.

        Args:
            name: Unique name for the agent
            agent_class: Agent class to register

        Raises:
            AgentError: If name already registered
        """
        if name in cls._agents:
            raise AgentError(f"Agent '{name}' already registered")

        if not issubclass(agent_class, Agent):
            raise AgentError(
                f"Agent class must inherit from Agent base class"
            )

        cls._agents[name] = agent_class

    @classmethod
    def get(cls, name: str) -> Type[Agent]:
        """Get agent class by name.

        Args:
            name: Agent name

        Returns:
            Agent class

        Raises:
            AgentError: If agent not found
        """
        if name not in cls._agents:
            raise AgentError(f"Agent '{name}' not found in registry")

        return cls._agents[name]

    @classmethod
    def list_agents(cls) -> Dict[str, Type[Agent]]:
        """List all registered agents."""
        return cls._agents.copy()

    @classmethod
    def create(cls, name: str, **kwargs) -> Agent:
        """Create agent instance by name.

        Args:
            name: Agent name
            **kwargs: Arguments to pass to agent constructor

        Returns:
            Agent instance
        """
        agent_class = cls.get(name)
        return agent_class(**kwargs)


# Convenience functions
def register_agent(name: str):
    """Decorator to register an agent class.

    Usage:
        @register_agent("ocr")
        class OCRAgent(Agent):
            ...
    """

    def decorator(agent_class: Type[Agent]):
        AgentRegistry.register(name, agent_class)
        return agent_class

    return decorator


def get_agent(name: str) -> Type[Agent]:
    """Get agent class by name."""
    return AgentRegistry.get(name)
