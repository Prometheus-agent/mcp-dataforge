from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class AgentConfig(BaseModel):
    """Configuration for a single agent MCP server."""
    command: str
    transport: str = "stdio"
    capabilities: list[str] = Field(default_factory=list)

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str) -> str:
        if v not in ("stdio", "sse"):
            raise ValueError(f"transport must be 'stdio' or 'sse', got '{v}'")
        return v


class DataForgeConfig(BaseModel):
    """Top-level dataforge configuration."""
    version: str = "1.0"
    project: str = "default"
    agents: dict[str, AgentConfig] = Field(default_factory=dict)


def load_config(path: Path | str) -> DataForgeConfig:
    """Load and validate a YAML config file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return DataForgeConfig(**data)


def find_config(start_dir: Optional[Path] = None) -> Optional[Path]:
    """Search for config.yaml in current dir or .dataforge/ subdir."""
    start = start_dir or Path.cwd()
    candidates = [
        start / "config.yaml",
        start / ".dataforge" / "config.yaml",
        start / "dataforge.yaml",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def create_default_config() -> DataForgeConfig:
    """Create the default configuration."""
    return DataForgeConfig(
        version="1.0",
        project="my-data-platform",
        agents={
            "pipeline": AgentConfig(
                command="python -m d4.agents.pipeline.server",
                capabilities=["sql"],
            ),
            "dq": AgentConfig(
                command="python -m d4.agents.dq.server",
                capabilities=["data_quality", "profiling", "validation"],
            ),
            "schema": AgentConfig(
                command="python -m d4.agents.schema.server",
                capabilities=["schema", "drift", "migration", "lineage"],
            ),
            "catalog": AgentConfig(
                command="python -m d4.agents.catalog.server",
                capabilities=["catalog", "discovery", "documentation", "tagging"],
            ),
        },
    )


def write_default_config(path: Path) -> None:
    """Write a default config.yaml to the given path."""
    import yaml
    cfg = create_default_config()
    data = cfg.model_dump()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
