import { ShieldCheck, TriangleAlert, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { api } from "../api.js";
import StaffLayout from "../StaffLayout.jsx";
import { Pill } from "../ui.jsx";

const TYPE_LABELS = {
  EMERGENCY: "Emergency",
  CLINICAL_ADVICE: "Clinical question",
  POLICY_APPROVAL: "Needs approval",
  DOCUMENT_MISMATCH: "Document mismatch",
  LOW_CONFIDENCE: "Low confidence",
  SYSTEM_FAILURE: "System failure",
};

function formatWaiting(minutes) {
  return minutes < 60 ? `${minutes} min` : `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}

// Urgent cases are red; every other case is waiting on a person, in the approval amber.
function CasePill({ c }) {
  if (c.priority === "URGENT") {
    return (
      <Pill tone="urgent" icon={<TriangleAlert />}>
        Urgent
      </Pill>
    );
  }
  return (
    <Pill tone="approval" icon={<User />}>
      {TYPE_LABELS[c.type] ?? c.type}
    </Pill>
  );
}

const caseId = (c) => `ESC-${String(c.id).padStart(4, "0")}`;
const runId = (c) => (c.workflow_run_id ? `WR-${c.workflow_run_id}` : "no run");

// Open cases handed to staff, most urgent first: the list beside the case that is open. The staff start page.
export default function StaffEscalations() {
  const [cases, setCases] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [resolving, setResolving] = useState(false);
  const detail = useRef(null);

  function load() {
    api("/api/staff/escalations").then(setCases, (e) => setError(e.message));
  }

  useEffect(load, []);

  function select(id) {
    setSelectedId(id);
    // On narrow screens the case sits below the list; bring it into view. No-op when already visible.
    detail.current?.scrollIntoView({ block: "nearest" });
  }

  async function resolve(c) {
    setError("");
    setNotice("");
    setResolving(true);
    try {
      await api(`/api/staff/escalations/${c.id}/resolve`, { method: "POST" });
      setNotice(`${caseId(c)} resolved.`);
    } catch (e) {
      setError(e.message);
    }
    setResolving(false);
    load(); // Reload either way: if someone else resolved it first, it drops off the list too.
  }

  // The case the person picked, or the most urgent one. A resolved case falls back to the next.
  const open = cases?.find((c) => c.id === selectedId) ?? cases?.[0];

  return (
    <StaffLayout title="Escalations" subtitle="Cases the agents stopped and handed to a person.">
      <title>Escalations - AgentCare</title>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div role="status" className="live">
        {notice && <p className="notice">{notice}</p>}
      </div>
      {cases?.length === 0 && (
        <div className="card empty">
          <ShieldCheck aria-hidden="true" />
          No open cases. New escalations show up here.
        </div>
      )}
      {open && (
        <div className="cases">
          <div className="case-list">
            {cases.map((c) => (
              <button
                key={c.id}
                type="button"
                className={c.id === open.id ? "case selected" : "case"}
                aria-pressed={c.id === open.id}
                onClick={() => select(c.id)}
              >
                <span className="case-top">
                  <CasePill c={c} />
                  <span className="mono muted">{caseId(c)}</span>
                </span>
                <span className="case-title">{c.reason}</span>
                <span className="case-sub">
                  {c.patient} · {runId(c)} · waiting {formatWaiting(c.waiting_minutes)}
                </span>
              </button>
            ))}
          </div>
          <section ref={detail} className="card case-detail" aria-label={`Case ${caseId(open)}`}>
            <div className="case-meta">
              <CasePill c={open} />
              <span className="mono muted">
                {caseId(open)} · {runId(open)} · waiting {formatWaiting(open.waiting_minutes)}
              </span>
            </div>
            <h2>{open.reason}</h2>
            <dl className="facts">
              <div>
                <dt>Patient</dt>
                <dd>{open.patient}</dd>
              </div>
              <div>
                <dt>Type</dt>
                <dd>{TYPE_LABELS[open.type] ?? open.type}</dd>
              </div>
              <div>
                <dt>Priority</dt>
                <dd>{open.priority.charAt(0) + open.priority.slice(1).toLowerCase()}</dd>
              </div>
              <div>
                <dt>Workflow run</dt>
                <dd className="mono">
                  {open.workflow_run_id ? (
                    <Link to={`/staff/runs/${open.workflow_run_id}`}>{runId(open)}</Link>
                  ) : (
                    runId(open)
                  )}
                </dd>
              </div>
            </dl>
            <div className="decision">
              <button type="button" className="btn btn-primary" disabled={resolving} onClick={() => resolve(open)}>
                {resolving ? "Resolving…" : "Resolve"}
              </button>
            </div>
          </section>
        </div>
      )}
    </StaffLayout>
  );
}
