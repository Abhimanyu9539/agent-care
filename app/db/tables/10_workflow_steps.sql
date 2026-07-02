-- One row per agent step in a run: the agent timeline on the staff screen.

CREATE TABLE workflow_steps (
  id            bigserial PRIMARY KEY,
  run_id        bigint NOT NULL REFERENCES workflow_runs(id),
  seq           int NOT NULL,
  agent         text NOT NULL,                 -- safety, coordinator, routing, ...
  node          text NOT NULL,
  outcome       text NOT NULL CHECK (outcome IN ('OK', 'RETRIED', 'FAILED', 'INTERRUPTED')),
  input_summary jsonb NOT NULL,                -- ids and counts, no free text
  output        jsonb,                         -- the validated output schema
  tool_calls    jsonb NOT NULL DEFAULT '[]',   -- [{tool, args, ok, ms, result_ref}]
  llm_meta      jsonb,                         -- {model, prompt_version, tokens_in, tokens_out, attempts}
  latency_ms    int NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (run_id, seq)
);
