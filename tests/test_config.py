import pytest
import yaml
from d4.config.loader import (
    DataForgeConfig,
    AgentConfig,
    load_config,
    find_config,
    create_default_config,
)


class TestAgentConfig:
    def test_minimal(self):
        cfg = AgentConfig(command="python -m d4.agents.pipeline")
        assert cfg.transport == "stdio"
        assert cfg.capabilities == []

    def test_invalid_transport(self):
        with pytest.raises(ValueError, match="transport"):
            AgentConfig(command="echo", transport="invalid")


class TestDataForgeConfig:
    def test_minimal(self):
        cfg = DataForgeConfig()
        assert cfg.version == "1.0"
        assert cfg.agents == {}

    def test_with_agents(self):
        agent = AgentConfig(command="python -m d4.agents.pipeline")
        cfg = DataForgeConfig(agents={"pipeline": agent})
        assert cfg.agents["pipeline"].command == "python -m d4.agents.pipeline"


class TestLoadConfig:
    def test_load_from_dict(self, tmp_path):
        config_data = {
            "version": "1.0",
            "project": "test-project",
            "agents": {
                "pipeline": {
                    "command": "python -m d4.agents.pipeline",
                    "transport": "stdio",
                    "capabilities": ["sql"],
                }
            },
        }
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)
        cfg = load_config(config_file)
        assert cfg.project == "test-project"
        assert "pipeline" in cfg.agents
        assert cfg.agents["pipeline"].capabilities == ["sql"]

    def test_load_empty_config(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: '1.0'\n")
        cfg = load_config(config_file)
        assert cfg.version == "1.0"
        assert cfg.agents == {}

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.yaml")


class TestFindConfig:
    def test_find_in_current_dir(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: '1.0'\n")
        monkeypatch.chdir(tmp_path)
        result = find_config()
        assert result == config_file

    def test_find_in_dataforge_dir(self, tmp_path, monkeypatch):
        dataforge_dir = tmp_path / ".dataforge"
        dataforge_dir.mkdir()
        config_file = dataforge_dir / "config.yaml"
        config_file.write_text("version: '1.0'\n")
        monkeypatch.chdir(tmp_path)
        result = find_config()
        assert result == config_file


class TestCreateDefaultConfig:
    def test_default_has_pipeline_agent(self):
        cfg = create_default_config()
        assert "pipeline" in cfg.agents
        assert cfg.agents["pipeline"].command == "python -m d4.agents.pipeline.server"

    def test_default_has_dq_agent(self):
        cfg = create_default_config()
        assert "dq" in cfg.agents
        assert "data_quality" in cfg.agents["dq"].capabilities

    def test_default_has_schema_agent(self):
        cfg = create_default_config()
        assert "schema" in cfg.agents
        assert "drift" in cfg.agents["schema"].capabilities

    def test_default_has_catalog_agent(self):
        cfg = create_default_config()
        assert "catalog" in cfg.agents
        assert "discovery" in cfg.agents["catalog"].capabilities
