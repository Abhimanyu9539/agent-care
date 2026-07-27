import { Check, RotateCcw, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router";
import { api } from "../api.js";
import StaffLayout from "../StaffLayout.jsx";
import { RunStatus } from "../ui.jsx";

// Which model and prompt a step used and how many tokens, or why the LLM call failed. Never the text.
function LlmLine({ meta }) {
  if (meta.error) {
    return (
      <p className="mono">
        llm {meta.model} failed: {meta.error}
      </p>
    );
  }
  return (
    <p className="mono">
      llm {meta.model} · {meta.prompt_version} · {meta.tokens_in} in / {meta.tokens_out} out tokens
    </p>
  );
}

// What went wrong with a failed or stuck run, and the button that runs it again from the start.
function RetryPanel({ run, retrying, onRetry }) {
  const [title, text] = run.stuck
    ? ["This request is stuck", "It has made no progress for 10 minutes, so its background job was probably lost."]
    : ["This request failed", run.error ? `${run.error.code}: ${run.error.message}` : "No error was saved."];
  return (
    <section className="card retry" aria-label="Retry">
      <div>
        <h2>{title}</h2>
        <p className="mono">{text}</p>
      </div>
      <button type="button" className="btn btn-primary" disabled={retrying} onClick={onRetry}>
        <RotateCcw aria-hidden="true" />
        {retrying ? "Retrying…" : "Retry from the start"}
      </button>
    </section>
  );
}

// One request and its agent timeline: every step the workflow ran, in order.
export default function StaffRun() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [retrying, setRetrying] = useState(false);

  function load() {
    api(`/api/staff/runs/${id}`).then(setData, (e) => setError(e.message));
  }

  useEffect(load, [id]);

  // While it runs, check again every 2 seconds, so a retry's steps appear as they happen.
  useEffect(() => {
    if (data?.run.status !== "RUNNING" || data.run.stuck) return;
    const timer = setTimeout(load, 2000);
    return () => clearTimeout(timer);
  }, [data]);

  async function retry() {
    setError("");
    setRetrying(true);
    try {
      await api(`/api/staff/runs/${id}/retry`, { method: "POST" });
    } catch (e) {
      setError(e.message);
    }
    setRetrying(false);
    load();
  }

  const run = data?.run;

  return (
    <StaffLayout title={`WR-${id}`} subtitle="The request and every step the agents ran.">
      <title>{`WR-${id} - AgentCare`}</title>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {data && (
        <>
          <section className="card">
            <div className="request-head">
              <RunStatus status={run.status} stuck={run.stuck} />
              <span className="mono muted">
                {run.patient} · step: {run.current_step}
                {run.attempt > 1 && ` · attempt ${run.attempt}`}
              </span>
            </div>
            <p className="quote">“{run.request_text}”</p>
          </section>
          {(run.status === "FAILED" || run.stuck) && <RetryPanel run={run} retrying={retrying} onRetry={retry} />}
          <section className="card">
            {data.steps.length === 0 && <p className="muted">No steps yet.</p>}
            <ol className="steps">
              {data.steps.map((step) => (
                <li key={step.seq} className={step.outcome === "OK" ? "done" : "failed"}>
                  <span className="marker">
                    {step.outcome === "OK" ? <Check aria-hidden="true" /> : <X aria-hidden="true" />}
                  </span>
                  <div>
                    <h2>
                      {step.seq}. {step.agent} · {step.node}
                    </h2>
                    <p className="mono">
                      {step.outcome} · {step.latency_ms} ms
                      {run.attempt > 1 && step.attempt && ` · attempt ${step.attempt}`}
                    </p>
                    {step.llm_meta && <LlmLine meta={step.llm_meta} />}
                    {step.tool_calls.map((call, i) => (
                      <p key={i} className="mono">
                        tool {call.tool} → {call.result_ref}
                      </p>
                    ))}
                    <pre className="mono step-output">{JSON.stringify(step.output, null, 2)}</pre>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </>
      )}
    </StaffLayout>
  );
}
