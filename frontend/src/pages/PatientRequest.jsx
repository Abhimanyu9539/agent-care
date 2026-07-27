import { Check, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { api } from "../api.js";
import PatientLayout from "../PatientLayout.jsx";
import { RunStatus } from "../ui.jsx";

// What the patient is told for each status. Only the saved status is shown, never guessed progress.
const NEXT_STEP = {
  RUNNING: ["Checking your request", "We're working on your request."],
  WAITING_PATIENT_INPUT: ["Waiting for you", "We need an answer from you to go on."],
  WAITING_APPROVAL: ["With the hospital team", "A staff member needs to approve the next step."],
  ESCALATED: ["Handed to the hospital team", "A staff member will contact you."],
  COMPLETED: ["Done", "Your request is complete."],
  FAILED: ["Something went wrong", "Something went wrong on our side. Our team has been told and will try again."],
  CANCELLED: ["Cancelled", "This request was cancelled."],
};

// A clinical question is declined: AgentCare never advises on medicines or diagnoses.
const DECLINED = [
  "We can't answer this here",
  "Questions about medicines, doses or a diagnosis need a doctor. Send a new request to book a visit, and a doctor can help.",
];

const VISIT = { NEW: "a new visit", FOLLOW_UP: "a follow-up visit" };

// The title and text of the step the request is at now.
function nextStep(run) {
  if (run.stuck) return ["Taking longer than usual", "Something held up your request. Our team will look at it."];
  if (run.safety === "CLINICAL_ADVICE") return DECLINED;
  if (run.department && run.changed_to_new) {
    return [
      `Sent to ${run.department}`,
      `You haven't visited ${run.department} with us before, so we'll register this as a new visit.`,
    ];
  }
  if (run.department) {
    return [`Sent to ${run.department}`, `The ${run.department} team has your request for ${VISIT[run.visit_type]}.`];
  }
  return NEXT_STEP[run.status] ?? [run.status, ""];
}

// "10:38" for today, "14 Nov 10:38" for an earlier day, in the browser's time zone.
function savedAt(iso) {
  const date = new Date(iso);
  const time = date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  if (date.toDateString() === new Date().toDateString()) return time;
  return `${date.toLocaleDateString("en-GB", { day: "2-digit", month: "short" })} ${time}`;
}

// One request and its status.
export default function PatientRequest() {
  const { id } = useParams();
  const [run, setRun] = useState(null);
  const [error, setError] = useState("");

  function load() {
    api(`/api/patient/requests/${id}`).then(setRun, (e) => setError(e.message));
  }

  useEffect(load, [id]);

  // The workflow runs in the background: while it does, check again every 2 seconds. A stuck run waits for staff.
  useEffect(() => {
    if (run?.status !== "RUNNING" || run.stuck) return;
    const timer = setTimeout(load, 2000);
    return () => clearTimeout(timer);
  }, [run]);

  const another = (
    <p className="center">
      <Link to="/patient">Send another request</Link>
    </p>
  );

  if (error) {
    return (
      <PatientLayout title="Your request">
        <p className="error" role="alert">
          {error}
        </p>
        {another}
      </PatientLayout>
    );
  }
  if (run === null) return <PatientLayout title="Your request" />;

  const [stepTitle, stepText] = nextStep(run);
  const finished = run.status === "COMPLETED";

  return (
    <PatientLayout title="Your request" subtitle={`WR-${run.id}`}>
      <title>{`Request WR-${run.id} - AgentCare`}</title>
      {run.safety === "EMERGENCY" && (
        <section className="emergency" role="alert">
          <TriangleAlert aria-hidden="true" />
          <div className="stack">
            <h2>Call 112 now</h2>
            <p>
              What you describe may be an emergency. Don't wait for a booking: call 112 or go to the nearest emergency
              department. Our staff have been alerted.
            </p>
            <a className="btn btn-urgent" href="tel:112">
              Call 112
            </a>
          </div>
        </section>
      )}
      <section className="card">
        <div className="request-head">
          <RunStatus status={run.status} />
          <span className="mono muted">sent {savedAt(run.created_at)}</span>
        </div>
        <p className="quote">“{run.request_text}”</p>
      </section>
      <ol className="steps">
        <li className="done">
          <span className="marker">
            <Check aria-hidden="true" />
          </span>
          <div>
            <h2>Request received</h2>
            <p className="mono">
              WR-{run.id} · saved {savedAt(run.created_at)}
            </p>
          </div>
        </li>
        <li className={finished ? "done" : "active"}>
          <span className="marker">{finished && <Check aria-hidden="true" />}</span>
          <div>
            <h2>{stepTitle}</h2>
            <p>{stepText}</p>
          </div>
        </li>
      </ol>
      {another}
    </PatientLayout>
  );
}
