export interface AgentInfo {
  name: string;
  command: string;
  transport: string;
  capabilities: string[];
}

export interface PipelineStep {
  agent: string;
  tool: string;
  params: Record<string, unknown>;
  depends_on: string[];
  parallel: boolean;
}

export interface PipelineSummary {
  id: string;
  status: string;
  task: string;
  plan: PipelineStep[];
  result_count: number;
}

export interface PipelineDetail {
  pipeline_id: string;
  status: string;
  task: string;
  plan: PipelineStep[];
  results?: unknown[];
}
