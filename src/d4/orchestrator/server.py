"""Orchestrator — routes tasks to specialist agents and tracks pipelines."""
import uuid
import importlib
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from d4.registry.agent_registry import AgentRegistry
from d4.models.core import AgentStep


class Orchestrator:
    """Orchestrator that routes tasks to specialist agents and tracks pipelines."""

    def __init__(self, registry: Optional[AgentRegistry] = None):
        self.registry = registry or AgentRegistry()
        self.pipelines: dict[str, dict] = {}

    def _call_agent_tool(self, agent_name: str, task: str, context: Optional[dict] = None) -> dict:
        """Dynamically import an agent module and call its execute() function."""
        agent = self.registry.get(agent_name)
        if not agent:
            return {"status": "error", "error": f"Agent '{agent_name}' not found"}

        try:
            module_map = {
                "pipeline": "d4.agents.pipeline",
                "dq": "d4.agents.dq",
                "schema": "d4.agents.schema",
                "catalog": "d4.agents.catalog",
                "observability": "d4.agents.observability",
                "orchestration": "d4.agents.orchestration",
            }
            module_path = module_map.get(agent_name)
            if not module_path:
                return {"status": "error", "error": f"No module mapping for agent '{agent_name}'"}

            module = importlib.import_module(module_path)
            if not hasattr(module, "execute"):
                return {
                    "status": "error",
                    "error": f"Agent '{agent_name}' has no execute() function",
                }

            result = module.execute(task, context or {})
            return {"status": "success", "agent": agent_name, "result": result}

        except Exception as e:
            return {"status": "error", "agent": agent_name, "error": str(e)}

    def _route_to_agents(self, task: str) -> list:
        """Determine which agents should handle a task based on keywords."""
        task_lower = task.lower()
        relevant_agents = []

        keyword_map = [
            ("dq", "data_quality", ["null", "quality", "profile", "anomaly", "validate", "freshness", "accuracy"]),
            ("pipeline", "sql", ["pipeline", "sql", "etl", "elt", "transform", "generate", "spark", "dbt"]),
            ("schema", "schema", ["schema", "drift", "migration", "column", "lineage", "alter"]),
            ("catalog", "catalog", ["catalog", "search", "find", "documentation", "describe", "tag", "discover"]),
            ("observability", "observability", ["health", "monitor", "alert", "cost", "observe", "sla", "performance"]),
            ("orchestration", "orchestration", ["dag", "schedule", "backfill", "orchestrate", "airflow", "retry", "run"]),
        ]

        for agent_name, capability, keywords in keyword_map:
            if any(kw in task_lower for kw in keywords):
                matches = self.registry.find_by_capability(capability)
                if matches:
                    relevant_agents.append(matches[0])

        if not relevant_agents and self.registry.list_agents():
            relevant_agents = [self.registry.list_agents()[0]]

        return relevant_agents

    def route_task(self, task: str, context: Optional[dict] = None) -> dict:
        """Parse a task description and return a multi-agent execution plan."""
        relevant_agents = self._route_to_agents(task)

        pipeline_id = f"pipeline_{uuid.uuid4().hex[:8]}"
        plan = []
        for agent in relevant_agents:
            plan.append(AgentStep(
                agent=agent.name,
                tool="execute",
                params={"task": task, "context": context or {}},
            ).model_dump())

        self.pipelines[pipeline_id] = {
            "status": "planned",
            "task": task,
            "plan": plan,
            "results": [],
        }

        return {
            "pipeline_id": pipeline_id,
            "summary": f"Planned {len(plan)} agent(s) for task: {task[:80]}...",
            "plan": plan,
        }

    def execute_task(self, task: str, context: Optional[dict] = None) -> dict:
        """Route task to agents and execute SEQUENTIALLY, passing context between them.

        Agent N's output is merged into the context passed to Agent N+1.
        This enables multi-agent collaboration:
          profile data → fix schema → validate quality → catalog results
        """
        relevant_agents = self._route_to_agents(task)
        pipeline_id = f"pipeline_{uuid.uuid4().hex[:8]}"

        shared_context = dict(context or {})
        results = []

        for agent in relevant_agents:
            # Update context with previous agent's output
            if results and results[-1]["status"] == "success":
                # Merge last agent's result so next agent can use it
                last_result = results[-1].get("result", {})
                if isinstance(last_result, dict):
                    shared_context["previous_result"] = last_result
                    shared_context["last_agent"] = results[-1]["agent"]

            result = self._call_agent_tool(agent.name, task, shared_context)
            results.append(result)

        all_success = all(r["status"] == "success" for r in results)
        pipeline_status = "completed" if all_success else "completed_with_errors"

        pipeline_entry = {
            "status": pipeline_status,
            "task": task,
            "plan": [AgentStep(agent=agent.name, tool="execute", params={"task": task}).model_dump()
                     for agent in relevant_agents],
            "results": results,
        }
        self.pipelines[pipeline_id] = pipeline_entry

        return {
            "pipeline_id": pipeline_id,
            "status": pipeline_status,
            "summary": f"Executed {len(results)} agent(s) sequentially: {' → '.join(r['agent'] for r in results)}",
            "results": results,
            "pipeline": [r["agent"] for r in results],
        }

    def execute_custom_pipeline(self, pipeline: list[dict], initial_context: Optional[dict] = None) -> dict:
        """Execute a custom multi-agent pipeline defined by the caller.

        Each step: {"agent": str, "task": str, "context": dict?}
        Runs SEQUENTIALLY — each step receives previous step's output via context.

        To run steps in parallel, use execute_parallel_pipeline() instead.
        """
        pipeline_id = f"pipeline_{uuid.uuid4().hex[:8]}"
        shared_context = dict(initial_context or {})
        results = []

        for step in pipeline:
            agent_name = step["agent"]
            step_task = step.get("task", "")
            step_context = {**shared_context, **step.get("context", {})}

            if results and results[-1]["status"] == "success":
                last_result = results[-1].get("result", {})
                if isinstance(last_result, dict):
                    step_context["previous_result"] = last_result
                    step_context["last_agent"] = results[-1]["agent"]

            result = self._call_agent_tool(agent_name, step_task, step_context)
            result["step_task"] = step_task
            results.append(result)

            if result["status"] == "error":
                break

        all_success = all(r["status"] == "success" for r in results)
        pipeline_status = "completed" if all_success else "failed"

        self.pipelines[pipeline_id] = {
            "status": pipeline_status,
            "task": "custom_pipeline",
            "plan": pipeline,
            "results": results,
        }

        return {
            "pipeline_id": pipeline_id,
            "status": pipeline_status,
            "steps": len(results),
            "results": results,
            "pipeline": [r["agent"] for r in results],
        }

    def execute_parallel(self, steps: list[dict]) -> dict:
        """Execute multiple agent steps in PARALLEL using threads.

        Each step: {"agent": str, "task": str, "context": dict?}
        All steps run concurrently. Results are merged at the end.

        Use for: independent tasks like simultaneous profiling of multiple tables,
        or running catalog search + pipeline generation side by side.
        """
        pipeline_id = f"pipeline_{uuid.uuid4().hex[:8]}"

        def run_step(step: dict) -> dict:
            agent_name = step["agent"]
            step_task = step.get("task", "")
            step_context = step.get("context", {})
            result = self._call_agent_tool(agent_name, step_task, step_context)
            result["step_task"] = step_task
            result["step_index"] = step.get("index", 0)
            return result

        # Assign indices for ordering
        for i, step in enumerate(steps):
            step["index"] = i

        results = [None] * len(steps)
        with ThreadPoolExecutor(max_workers=min(len(steps), 6)) as executor:
            futures = {executor.submit(run_step, step): i for i, step in enumerate(steps)}
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    results[idx] = {"status": "error", "agent": steps[idx]["agent"], "error": str(e), "step_index": idx}

        all_success = all(r and r["status"] == "success" for r in results)
        pipeline_status = "completed" if all_success else "completed_with_errors"

        merged_results = {}
        for r in results:
            if r and r["status"] == "success":
                result_data = r.get("result", {})
                if isinstance(result_data, dict):
                    merged_results[r["agent"]] = result_data

        self.pipelines[pipeline_id] = {
            "status": pipeline_status,
            "task": "parallel_pipeline",
            "plan": steps,
            "results": results,
        }

        return {
            "pipeline_id": pipeline_id,
            "status": pipeline_status,
            "total_steps": len(steps),
            "results": results,
            "merged_results": merged_results,
            "pipeline": [r["agent"] for r in results if r],
        }

    def execute_mixed_pipeline(self, stages: list[dict], initial_context: Optional[dict] = None) -> dict:
        """Execute a multi-stage pipeline mixing sequential and parallel phases.

        Each stage is one of:
          {"type": "sequential", "steps": [{"agent": ..., "task": ..., "context": ...}, ...]}
          {"type": "parallel", "steps": [...]}
          {"type": "single", "agent": ..., "task": ..., "context": ...}

        Stages run sequentially. Within a "parallel" stage, all steps run concurrently.
        Context flows between stages (not within parallel sub-steps).
        """
        pipeline_id = f"pipeline_{uuid.uuid4().hex[:8]}"
        shared_context = dict(initial_context or {})
        stage_results = []

        for stage_idx, stage in enumerate(stages):
            stage_type = stage.get("type", "single")

            if stage_type == "single":
                agent_name = stage["agent"]
                step_task = stage.get("task", "")
                step_context = {**shared_context, **stage.get("context", {})}
                if stage_results:
                    last_stage = stage_results[-1]
                    if last_stage.get("status") == "success":
                        all_results = last_stage.get("results", [])
                        if all_results and all_results[-1].get("status") == "success":
                            step_context["previous_result"] = all_results[-1].get("result", {})
                            step_context["last_agent"] = all_results[-1]["agent"]

                result = self._call_agent_tool(agent_name, step_task, step_context)
                result["step_task"] = step_task
                stage_results.append({"stage": stage_idx, "type": "single", "status": result["status"], "results": [result]})

                # Merge successful result into context
                if result["status"] == "success" and isinstance(result.get("result"), dict):
                    shared_context["stage_" + str(stage_idx)] = result["result"]

            elif stage_type == "sequential":
                sub_results = []
                for step in stage["steps"]:
                    agent_name = step["agent"]
                    step_task = step.get("task", "")
                    step_context = {**shared_context, **step.get("context", {})}
                    if sub_results and sub_results[-1]["status"] == "success":
                        step_context["previous_result"] = sub_results[-1].get("result", {})
                        step_context["last_agent"] = sub_results[-1]["agent"]

                    result = self._call_agent_tool(agent_name, step_task, step_context)
                    result["step_task"] = step_task
                    sub_results.append(result)
                    if result["status"] == "error":
                        break

                all_ok = all(r["status"] == "success" for r in sub_results)
                stage_results.append({"stage": stage_idx, "type": "sequential", "status": "completed" if all_ok else "failed", "results": sub_results})
                if sub_results and sub_results[-1].get("result"):
                    shared_context["stage_" + str(stage_idx)] = sub_results[-1]["result"]

            elif stage_type == "parallel":
                def run_parallel_step(step):
                    agent_name = step["agent"]
                    step_task = step.get("task", "")
                    step_context = {**shared_context, **step.get("context", {})}
                    result = self._call_agent_tool(agent_name, step_task, step_context)
                    result["step_task"] = step_task
                    return result

                sub_results = []
                with ThreadPoolExecutor(max_workers=min(len(stage["steps"]), 6)) as executor:
                    futures = [executor.submit(run_parallel_step, step) for step in stage["steps"]]
                    for future in as_completed(futures):
                        try:
                            sub_results.append(future.result())
                        except Exception as e:
                            sub_results.append({"status": "error", "error": str(e)})

                all_ok = all(r["status"] == "success" for r in sub_results)
                stage_results.append({"stage": stage_idx, "type": "parallel", "status": "completed" if all_ok else "failed", "results": sub_results})

                merged = {}
                for r in sub_results:
                    if r["status"] == "success" and isinstance(r.get("result"), dict):
                        merged[r["agent"]] = r["result"]
                shared_context["stage_" + str(stage_idx)] = merged

        all_success = all(s["status"] == "completed" for s in stage_results)
        pipeline_status = "completed" if all_success else "completed_with_errors"

        self.pipelines[pipeline_id] = {
            "status": pipeline_status,
            "task": "mixed_pipeline",
            "plan": stages,
            "results": stage_results,
        }

        return {
            "pipeline_id": pipeline_id,
            "status": pipeline_status,
            "stages": stage_results,
            "pipeline": pipeline_status,
        }

    def list_agents(self) -> list[dict]:
        """List all registered agents."""
        return [a.model_dump() for a in self.registry.list_agents()]

    def get_pipeline_status(self, pipeline_id: str) -> dict:
        """Get the status of a running or completed pipeline."""
        pipeline = self.pipelines.get(pipeline_id)
        if pipeline is None:
            return {"pipeline_id": pipeline_id, "status": "not_found"}
        return {
            "pipeline_id": pipeline_id,
            "status": pipeline["status"],
            "task": pipeline["task"],
            "plan": pipeline["plan"],
            "results": pipeline.get("results", []),
        }


# Backward compatibility
def create_orchestrator(registry: Optional[AgentRegistry] = None) -> Orchestrator:
    return Orchestrator(registry=registry)

def route_task(state: Orchestrator, task: str, context: Optional[dict] = None) -> dict:
    return state.route_task(task, context)

def list_agents(state: Orchestrator) -> list[dict]:
    return state.list_agents()

def get_pipeline_status(state: Orchestrator, pipeline_id: str) -> dict:
    return state.get_pipeline_status(pipeline_id)
