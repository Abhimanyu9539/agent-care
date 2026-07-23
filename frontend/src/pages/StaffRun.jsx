import { Check } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router";
import { api } from "../api.js";
import StaffLayout from "../StaffLayout.jsx";
import { RunStatus } from "../ui.jsx";

// One request and its agent timeline: every step the workflow ran, in order.
export default function StaffRun() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api(`/api/staff/runs/${id}`).then(setData, (e) => setError(e.message));
  }, [id]);

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
              <RunStatus status={data.run.status} />
              <span className="mono muted">
                {data.run.patient} · step: {data.run.current_step}
              </span>
            </div>
            <p className="quote">“{data.run.request_text}”</p>
          </section>
          <section className="card">
            {data.steps.length === 0 && <p className="muted">No steps yet.</p>}
            <ol className="steps">
              {data.steps.map((step) => (
                <li key={step.seq} className="done">
                  <span className="marker">
                    <Check aria-hidden="true" />
                  </span>
                  <div>
                    <h2>
                      {step.seq}. {step.agent} · {step.node}
                    </h2>
                    <p className="mono">
                      {step.outcome} · {step.latency_ms} ms
                    </p>
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
