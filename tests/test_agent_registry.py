from d4.registry.agent_registry import AgentRegistry
from d4.models.core import AgentInfo
from d4.config.loader import AgentConfig, DataForgeConfig


class TestAgentRegistry:
    def test_register_agent(self):
        registry = AgentRegistry()
        agent = AgentInfo(name="pipeline", command="python -m d4.agents.pipeline")
        registry.register(agent)
        assert registry.get("pipeline") == agent

    def test_get_nonexistent(self):
        registry = AgentRegistry()
        assert registry.get("nonexistent") is None

    def test_list_agents(self):
        registry = AgentRegistry()
        a1 = AgentInfo(name="pipeline", command="cmd1", capabilities=["sql"])
        a2 = AgentInfo(name="dq", command="cmd2", capabilities=["quality"])
        registry.register(a1)
        registry.register(a2)
        agents = registry.list_agents()
        assert len(agents) == 2
        assert {a.name for a in agents} == {"pipeline", "dq"}

    def test_find_by_capability(self):
        registry = AgentRegistry()
        a1 = AgentInfo(name="pipeline", command="cmd1", capabilities=["sql", "spark"])
        a2 = AgentInfo(name="dq", command="cmd2", capabilities=["data_quality"])
        a3 = AgentInfo(name="schema", command="cmd3", capabilities=["sql", "schema"])
        registry.register(a1)
        registry.register(a2)
        registry.register(a3)
        results = registry.find_by_capability("sql")
        assert len(results) == 2
        assert {a.name for a in results} == {"pipeline", "schema"}

    def test_load_from_config(self):
        registry = AgentRegistry()
        config = DataForgeConfig(
            agents={
                "pipeline": AgentConfig(command="cmd1", capabilities=["sql"]),
                "dq": AgentConfig(command="cmd2", capabilities=["quality"]),
            }
        )
        registry.load_from_config(config)
        assert registry.get("pipeline") is not None
        assert registry.get("dq") is not None
        assert registry.get("pipeline").capabilities == ["sql"]

    def test_unregister(self):
        registry = AgentRegistry()
        agent = AgentInfo(name="pipeline", command="cmd1")
        registry.register(agent)
        registry.unregister("pipeline")
        assert registry.get("pipeline") is None
