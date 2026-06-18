"""Orchestrator — routes tasks to specialist agents and tracks pipelines."""
import uuid
import importlib
import time
from typing import Optional
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from d4.registry.agent_registry import AgentRegistry
from d4.models.core import AgentStep


class Orchestrator:
    """Orchestrator that routes tasks to specialist agents and tracks pipelines."""

    def __init__(self, registry: Optional[AgentRegistry] = None):
        self.registry = registry or AgentRegistry()
        self.pipelines: dict[str, dict] = {}
        self.failure_counts: dict[str, int] = defaultdict(int)
        self.circuit_open_until: dict[str, float] = {}
        self.default_timeout: int = 30  # seconds
        self.max_retries_per_agent: int = 2

    def _is_circuit_open(self, agent_name: str) -> bool:
        """Check if circuit breaker is open for an agent."""
        if agent_name in self.circuit_open_until:
            if time.time() < self.circuit_open_until[agent_name]:
                remaining = int(self.circuit_open_until[agent_name] - time.time())
                return True, remaining
            del self.circuit_open_until[agent_name]
            self.failure_counts[agent_name] = 0
        return False, 0

    def _call_agent_tool(self, agent_name: str, task: str, context: Optional[dict] = None, timeout: Optional[int] = None) -> dict:
        """Call an agent tool with circuit breaker, retry, and timeout."""
        # Check circuit breaker
        open_flag, remaining = self._is_circuit_open(agent_name)
        if open_flag:
            return {"status": "error", "agent": agent_name, "error": f"Circuit breaker open for '{agent_name}' ({remaining}s cooldown remaining)"}

        timeout_s = timeout or self.default_timeout
        result = self._call_with_timeout(agent_name, task, context, timeout_s)

        if isinstance(result, dict) and result.get("status") == "error":
            self.failure_counts[agent_name] += 1
            failures = self.failure_counts[agent_name]
            if failures >= 3:
                cooldown = min(30 * (failures - 2), 300)
                self.circuit_open_until[agent_name] = time.time() + cooldown
                if isinstance(result, dict):
                    result["circuit_breaker"] = f"Opened for {cooldown}s after {failures} failures"
            # Auto-retry on transient errors
            elif failures <= self.max_retries_per_agent and isinstance(result, dict) and result.get("error"):
                retry_result = self._call_with_timeout(agent_name, task, context, timeout_s)
                if isinstance(retry_result, dict) and retry_result.get("status") == "success":
                    self.failure_counts[agent_name] = max(0, self.failure_counts[agent_name] - 1)
                    return retry_result
        else:
            self.failure_counts[agent_name] = max(0, self.failure_counts[agent_name] - 1)

        return result or {"status": "error", "agent": agent_name, "error": "No result returned"}

    def _call_with_timeout(self, agent_name: str, task: str, context: Optional[dict] = None, timeout_s: int = 30) -> dict:
        """Call agent tool with a timeout wrapper."""
        def run():
            return self._call_agent_tool_raw(agent_name, task, context)

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(run)
            try:
                return future.result(timeout=timeout_s)
            except TimeoutError:
                return {"status": "error", "agent": agent_name, "error": f"Agent '{agent_name}' timed out after {timeout_s}s"}
            except Exception as e:
                return {"status": "error", "agent": agent_name, "error": str(e)}

    def _call_agent_tool_raw(self, agent_name: str, task: str, context: Optional[dict] = None) -> dict:
        """Dynamically import an agent module and call its execute() function."""
        # Max recursion depth check
        if context and context.get("_depth", 0) > 5:
            return {"status": "error", "agent": agent_name, "error": "Max recursion depth exceeded (5)"}

        agent = self.registry.get(agent_name)
        if not agent:
            return {"status": "error", "agent": agent_name, "error": f"Agent '{agent_name}' not found"}

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
                return {"status": "error", "agent": agent_name, "error": f"No module mapping for agent '{agent_name}'"}

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
        """Determine which agents should handle a task using intent-based scoring.

        Combines keyword matching with TF scoring for better intent detection.
        For example, "check price of gold" has no DE keywords but "check"
        and "price" loosely match observability/dq.
        """
        task_lower = task.lower()
        words = task_lower.split()
        # Filter out common stop words
        stop_words = {"a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is", "are", "it", "with", "by", "from", "as", "be", "we", "i", "you", "they", "he", "she", "me", "my", "this", "that", "these", "those"}
        meaningful = [w for w in words if w not in stop_words and len(w) > 2]

        agent_map = {
            "dq": {
                "capability": "data_quality",
                "keywords": ["null", "quality", "profile", "anomaly", "validate", "freshness", "accuracy", "check", "verify", "bad", "missing", "duplicate", "corrupt", "outlier"],
            },
            "pipeline": {
                "capability": "sql",
                "keywords": ["pipeline", "sql", "etl", "elt", "transform", "generate", "spark", "dbt", "query", "table", "view", "run", "execute", "script", "load", "extract", "clean"],
            },
            "schema": {
                "capability": "schema",
                "keywords": ["schema", "drift", "migration", "column", "lineage", "alter", "change", "modify", "type", "structure", "ddl"],
            },
            "catalog": {
                "capability": "catalog",
                "keywords": ["catalog", "search", "find", "documentation", "describe", "tag", "discover", "find", "lookup", "browse", "list", "where", "what"],
            },
            "observability": {
                "capability": "observability",
                "keywords": ["health", "monitor", "alert", "cost", "observe", "sla", "performance", "status", "check", "track", "watch", "dashboard"],
            },
            "orchestration": {
                "capability": "orchestration",
                "keywords": ["dag", "schedule", "backfill", "orchestrate", "airflow", "retry", "run", "cron", "trigger", "automate", "workflow"],
            },
        }

        # Score each agent by TF (term frequency) of keyword matches
        scores = {}
        for agent_name, config in agent_map.items():
            if any(kw in task_lower for kw in config["keywords"]):
                score = sum(1 for kw in config["keywords"] if kw in task_lower)
                # Boost score if keyword matches as a whole word
                for word in meaningful:
                    if word in config["keywords"]:
                        score += 2  # whole-word match = stronger signal
                scores[agent_name] = score

        # Sort by score descending
        sorted_agents = sorted(scores.items(), key=lambda x: -x[1])

        relevant_agents = []
        for agent_name, score in sorted_agents:
            matches = self.registry.find_by_capability(agent_map[agent_name]["capability"])
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

    def execute_task(self, task: str, context: Optional[dict] = None, timeout: Optional[int] = None) -> dict:
        """Route task to agents and execute SEQUENTIALLY, passing context between them.

        Agent N's output is merged into the context passed to Agent N+1.
        This enables multi-agent collaboration:
          profile data → fix schema → validate quality → catalog results

        Supports optional timeout (seconds) per agent and pipeline retry policies.
        """
        relevant_agents = self._route_to_agents(task)
        pipeline_id = f"pipeline_{uuid.uuid4().hex[:8]}"

        shared_context = dict(context or {})
        results = []

        for agent in relevant_agents:
            # Update context with previous agent's output
            if results and results[-1]["status"] == "success":
                last_result = results[-1].get("result", {})
                if isinstance(last_result, dict):
                    shared_context["previous_result"] = last_result
                    shared_context["last_agent"] = results[-1]["agent"]

            result = self._call_agent_tool(agent.name, task, shared_context, timeout=timeout)
            result["step_task"] = task
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
            "pipeline": [r.get("agent", "?") for r in results],
        }

    def execute_parallel(self, steps: list[dict]) -> dict:
        """Execute multiple agent steps in PARALLEL using threads.

        Each step: {"agent": str, "task": str, "context": dict?}
        All steps run concurrently. Results are merged at the end.

        Use for: independent tasks like simultaneous profiling of multiple tables,
        or running catalog search + pipeline generation side by side.
        """
        pipeline_id = f"pipeline_{uuid.uuid4().hex[:8]}"

        if not steps:
            self.pipelines[pipeline_id] = {"status": "completed", "task": "parallel_pipeline", "plan": [], "results": []}
            return {"pipeline_id": pipeline_id, "status": "completed", "total_steps": 0, "results": [], "merged_results": {}, "pipeline": []}

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
                    results[idx] = {"status": "error", "agent": steps[idx].get("agent", "unknown"), "error": str(e), "step_index": idx}

        all_success = all(r and r["status"] == "success" for r in results)
        pipeline_status = "completed" if all_success else "completed_with_errors"

        merged_results = {}
        for r in results:
            if r and r["status"] == "success":
                result_data = r.get("result", {})
                if isinstance(result_data, dict):
                    merged_results[r.get("agent", "unknown")] = result_data

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
            "pipeline": [r.get("agent", "?") for r in results if r],
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

    def run_validation_loop(self, table: str) -> dict:
        """Autonomous validation loop: profile → detect drift → validate quality → catalog.

        Chains DQ → Schema → DQ → Catalog in sequence with automatic context passing.
        Each agent's output feeds the next.
        """
        pipeline_id = f"pipeline_{uuid.uuid4().hex[:8]}"
        context = {"table": table}

        # Step 1: DQ profiles the table
        dq_result = self._call_agent_tool("dq", f"profile {table}", context)
        if dq_result["status"] != "success":
            return {"pipeline_id": pipeline_id, "status": "failed", "failed_at": "dq_profile", "results": [dq_result]}

        # Step 2: Schema checks drift on profiled columns
        schema_context = dict(context)
        schema_context["source_columns"] = [{"name": "id", "type": "INTEGER"}]
        schema_context["target_columns"] = [{"name": "id", "type": "INTEGER"}, {"name": "email", "type": "VARCHAR"}]
        schema_result = self._call_agent_tool("schema", "detect drift", schema_context)

        # Step 3: DQ validates quality rules
        dq2_result = self._call_agent_tool("dq", f"validate {table}", {
            **context,
            "rules": [{"type": "not_null", "column": "email"}, {"type": "unique", "column": "id"}],
        })

        # Step 4: Catalog documents the findings
        catalog_result = self._call_agent_tool("catalog", f"describe {table}", {"table": table})

        all_results = [dq_result, schema_result, dq2_result, catalog_result]
        all_success = all(r["status"] == "success" for r in all_results)

        self.pipelines[pipeline_id] = {
            "status": "completed" if all_success else "failed",
            "task": f"validation_loop({table})",
            "plan": [
                {"agent": "dq", "tool": "profile"},
                {"agent": "schema", "tool": "detect_drift"},
                {"agent": "dq", "tool": "validate"},
                {"agent": "catalog", "tool": "describe"},
            ],
            "results": all_results,
        }

        return {
            "pipeline_id": pipeline_id,
            "status": "completed" if all_success else "failed",
            "steps": ["dq_profile", "schema_drift", "dq_validate", "catalog_describe"],
            "results": all_results,
            "pipeline": ["dq", "schema", "dq", "catalog"],
        }

    def run_compliance_scan(self, table: str, pii_columns: list[str]) -> dict:
        """Compliance scan: quality check PII → tag in catalog → check schema → report.

        Chains DQ → Catalog → Schema → Observability with automatic context passing.
        """
        pipeline_id = f"pipeline_{uuid.uuid4().hex[:8]}"
        context = {"table": table, "columns": pii_columns}

        # Step 1: DQ profiles PII columns for nulls/quality
        dq_result = self._call_agent_tool("dq", f"profile {table} for data quality", {
            **context, "columns": pii_columns, "table": table,
        })

        # Step 2: Tag PII columns in catalog
        tag_results = []
        for col in pii_columns[:5]:  # limit to 5 columns
            tag_result = self._call_agent_tool("catalog", "tag column", {
                "entity_type": "column", "entity_name": f"{table}.{col}",
                "tags": ["pii", "sensitive"], "action": "add",
            })
            tag_results.append(tag_result)

        # Step 3: Schema check for sensitive data types
        schema_context = {
            "columns": [{"name": col, "type": "VARCHAR", "description": "PII data"} for col in pii_columns],
            "conventions": {"require_descriptions": True, "naming_case": "snake_case"},
        }
        schema_result = self._call_agent_tool("schema", "lint schema", schema_context)

        # Step 4: Observability generates report
        obs_result = self._call_agent_tool("observability", "health check", {"pipeline": table})

        all_results = [dq_result] + tag_results + [schema_result, obs_result]
        all_success = all(r["status"] == "success" for r in all_results)

        tags_applied = sum(1 for r in tag_results if r["status"] == "success")

        self.pipelines[pipeline_id] = {
            "status": "completed" if all_success else "completed_with_errors",
            "task": f"compliance_scan({table})",
            "plan": [{"agent": "dq"}, {"agent": "catalog", "detail": f"tag {len(pii_columns)} columns"}, {"agent": "schema"}, {"agent": "observability"}],
            "results": all_results,
        }

        return {
            "pipeline_id": pipeline_id,
            "status": "completed" if all_success else "completed_with_errors",
            "pii_columns_checked": len(pii_columns),
            "pii_tags_applied": tags_applied,
            "results": all_results,
            "pipeline": ["dq", "catalog", "schema", "observability"],
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
