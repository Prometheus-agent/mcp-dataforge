"""Example DataForge agent plugin template."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("<Name> Agent", description="Description of what this agent does")


def execute(task: str, context: dict) -> dict:
    """Main entry point — called by orchestrator.

    This is the function DataForge imports dynamically.
    """
    task_lower = task.lower()
    # Route to tools based on task keywords
    if "example" in task_lower:
        return example_tool(context.get("param", "default"))
    return {"status": "success", "message": f"Processed: {task}"}


def example_tool(param: str) -> dict:
    """Example tool implementation."""
    return {"param": param, "result": f"processed {param}"}


@mcp.tool()
def my_tool(param: str = "default") -> dict:
    """An MCP tool exposed by this plugin."""
    return example_tool(param)
