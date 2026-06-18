from d4.models.core import AgentInfo
from d4.config.loader import DataForgeConfig


class AgentRegistry:
    """Registry that tracks available agents and their capabilities."""

    def __init__(self):
        self._agents: dict[str, AgentInfo] = {}

    def register(self, agent: AgentInfo) -> None:
        """Register an agent."""
        self._agents[agent.name] = agent

    def unregister(self, name: str) -> None:
        """Remove an agent from the registry."""
        self._agents.pop(name, None)

    def get(self, name: str) -> AgentInfo | None:
        """Get agent info by name."""
        return self._agents.get(name)

    def list_agents(self) -> list[AgentInfo]:
        """List all registered agents."""
        return list(self._agents.values())

    def find_by_capability(self, capability: str) -> list[AgentInfo]:
        """Find agents that have a specific capability."""
        return [
            a for a in self._agents.values()
            if capability in a.capabilities
        ]

    def load_from_config(self, config: DataForgeConfig) -> None:
        """Load agents from a configuration object."""
        for name, agent_cfg in config.agents.items():
            self.register(AgentInfo(
                name=name,
                command=agent_cfg.command,
                transport=agent_cfg.transport,
                capabilities=agent_cfg.capabilities,
            ))
