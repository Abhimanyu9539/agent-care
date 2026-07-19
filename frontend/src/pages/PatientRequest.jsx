import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { api } from "../api.js";

// One request and its status.
export default function PatientRequest() {
  const { id } = useParams();
  const [run, setRun] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api(`/api/patient/requests/${id}`).then(setRun, (e) => setError(e.message));
  }, [id]);

  const another = (
    <p>
      <Link to="/patient">Send another request</Link>
    </p>
  );

  if (error) {
    return (
      <main>
        <p className="error">{error}</p>
        {another}
      </main>
    );
  }
  if (run === null) return null;

  return (
    <main>
      <title>{`Request WR-${run.id} - AgentCare`}</title>
      <h1>Request WR-{run.id}</h1>
      <p className="request-text">{run.request_text}</p>
      <p>
        Status: <strong>{run.status}</strong>
      </p>
      {run.status === "RUNNING" && <p>We're working on your request.</p>}
      {another}
    </main>
  );
}
