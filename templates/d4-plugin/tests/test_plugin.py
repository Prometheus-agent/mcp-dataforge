import pytest
from d4_plugin_<name>.server import execute, my_tool

def test_execute():
    result = execute("example task", {"param": "hello"})
    assert result["status"] == "success"

def test_mcp_tool():
    result = my_tool("world")
    assert result["result"] == "processed world"
