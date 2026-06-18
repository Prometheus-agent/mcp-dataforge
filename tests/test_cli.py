import pytest
from click.testing import CliRunner
from d4.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestCli:
    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0

    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_mcp_command(self, runner):
        result = runner.invoke(cli, ["mcp"])
        assert result.exit_code == 0
        assert "mcpServers" in result.output

    def test_agent_list_no_config(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["agent", "list"])
            assert result.exit_code != 0

    def test_init_creates_config(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0
            assert "Created config" in result.output
