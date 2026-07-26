import { Inbox } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router";
import { api } from "../api.js";
import StaffLayout from "../StaffLayout.jsx";
import { RunStatus } from "../ui.jsx";

const SAFETY = {
  EMERGENCY: "Emergency",
  CLINICAL_ADVICE: "Clinical question",
  ADMIN: "Ordinary",
  UNCHECKED: "Not checked",
};

const VISIT = { NEW: "new visit", FOLLOW_UP: "follow-up" };

// What the patient wants, as the coordinator understood it.
const INTENT = {
  BOOK: "Book",
  RESCHEDULE: "Reschedule",
  CANCEL: "Cancel",
  DOCUMENTS_ONLY: "Documents",
  STATUS: "Status",
};

const sentAt = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

const percent = (confidence) => `${Math.round(confidence * 100)}%`;

const short = (text) => (text.length > 80 ? `${text.slice(0, 80)}…` : text);

// What the safety step found, and whether a word rule or the LLM decided it.
function safetyText(run) {
  if (!run.safety) return "—";
  const label = SAFETY[run.safety] ?? run.safety;
  if (!run.safety_source) return label;
  return `${label} · ${run.safety_source === "llm" ? "LLM" : "rules"}`;
}

// What the routing step decided. Routing always uses the LLM.
function routingText(run) {
  const { routing } = run;
  if (!routing) return run.department ?? "—";
  if (routing.result === "ROUTED") {
    const visit = routing.changed_to_new ? "new visit (asked for follow-up)" : VISIT[routing.visit_type];
    return `${routing.department_name} · ${visit} · ${percent(routing.confidence)}`;
  }
  if (routing.result === "LOW_CONFIDENCE") {
    return `Not sure, sent to staff · guessed ${routing.department} ${percent(routing.confidence)}`;
  }
  return "LLM failed, sent to staff";
}

// Every request, newest first, with how the agents decided it. Each WR opens its timeline.
export default function StaffRequests() {
  const [runs, setRuns] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/staff/runs").then(setRuns, (e) => setError(e.message));
  }, []);

  return (
    <StaffLayout
      title="Requests"
      subtitle="Every patient request, newest first. Intent is what the coordinator understood the patient wants. Safety shows whether a word rule or the LLM decided; routing is always the LLM."
    >
      <title>Requests - AgentCare</title>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {runs?.length === 0 && (
        <div className="card empty">
          <Inbox aria-hidden="true" />
          No requests yet.
        </div>
      )}
      {runs?.length > 0 && (
        <>
          <div className="table-card">
            <table>
              <thead>
                <tr>
                  <th>Request</th>
                  <th>Patient</th>
                  <th>Sent</th>
                  <th>Status</th>
                  <th>Intent</th>
                  <th>Safety</th>
                  <th>Routing</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id}>
                    <td className="request-cell">
                      <Link className="mono" to={`/staff/runs/${run.id}`}>
                        WR-{run.id}
                      </Link>
                      <div>{short(run.request_text)}</div>
                    </td>
                    <td className="nowrap">{run.patient}</td>
                    <td className="mono nowrap">{sentAt.format(new Date(run.created_at))}</td>
                    <td>
                      <RunStatus status={run.status} />
                    </td>
                    <td>{run.intent ? (INTENT[run.intent] ?? run.intent) : "—"}</td>
                    <td className="nowrap">{safetyText(run)}</td>
                    <td>{routingText(run)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted">Showing the newest {runs.length} requests.</p>
        </>
      )}
    </StaffLayout>
  );
}
