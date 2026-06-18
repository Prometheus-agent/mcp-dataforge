"""DataForge Web UI — FastAPI server for monitoring and controlling the orchestrator."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from d4.config.loader import find_config, load_config
from d4.registry.agent_registry import AgentRegistry
from d4.orchestrator.server import Orchestrator

app = FastAPI(title="DataForge", version="0.1.0")

# Initialize orchestrator from config
_config_path = find_config()
if _config_path:
    _config = load_config(_config_path)
    _registry = AgentRegistry()
    _registry.load_from_config(_config)
else:
    _registry = AgentRegistry()
orch = Orchestrator(registry=_registry)


@app.get("/api/agents")
def api_list_agents():
    return JSONResponse(content=orch.list_agents())


@app.get("/api/pipelines")
def api_list_pipelines():
    pipelines = []
    for pid, data in orch.pipelines.items():
        pipelines.append({
            "id": pid,
            "status": data.get("status", "unknown"),
            "task": data.get("task", "")[:80],
            "plan": data.get("plan", []),
            "result_count": len(data.get("results", [])),
        })
    return JSONResponse(content={"pipelines": pipelines, "total": len(pipelines)})


@app.get("/api/pipelines/{pipeline_id}")
def api_get_pipeline(pipeline_id: str):
    return JSONResponse(content=orch.get_pipeline_status(pipeline_id))


@app.post("/api/execute")
async def api_execute(body: dict):
    result = orch.execute_task(body.get("task", ""), body.get("context"))
    return JSONResponse(content=result)


@app.post("/api/pipeline/custom")
async def api_custom_pipeline(body: dict):
    result = orch.execute_custom_pipeline(body.get("pipeline", []), body.get("initial_context"))
    return JSONResponse(content=result)


@app.post("/api/pipeline/parallel")
async def api_parallel(body: dict):
    result = orch.execute_parallel(body.get("steps", []))
    return JSONResponse(content=result)


@app.post("/api/pipeline/mixed")
async def api_mixed(body: dict):
    result = orch.execute_mixed_pipeline(body.get("stages", []), body.get("initial_context"))
    return JSONResponse(content=result)


# Serve frontend
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
def index():
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse(content={"status": "DataForge API running", "agents": len(orch.list_agents())})


def run(host: str = "0.0.0.0", port: int = 8080):
    import uvicorn
    uvicorn.run(app, host=host, port=port)
