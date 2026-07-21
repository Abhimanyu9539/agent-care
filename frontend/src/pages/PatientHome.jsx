import { ArrowRight, CalendarDays, RefreshCw } from "lucide-react";
import { useRef, useState } from "react";
import { useNavigate, useOutletContext } from "react-router";
import { api } from "../api.js";
import PatientLayout from "../PatientLayout.jsx";

// Quick starts fill in the first words of a common request, for the patient to finish.
const STARTERS = [
  { icon: CalendarDays, label: "Book a visit", text: "I'd like to book a visit for " },
  { icon: RefreshCw, label: "Reschedule", text: "I need to move my appointment on " },
];

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  return hour < 17 ? "Good afternoon" : "Good evening";
}

// The form where a patient describes what they need.
export default function PatientHome() {
  const { user } = useOutletContext();
  const navigate = useNavigate();
  const requestBox = useRef(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // Busy until the page changes, so a double click cannot send the request twice.
  async function submit(event) {
    event.preventDefault();
    const body = Object.fromEntries(new FormData(event.currentTarget));
    setBusy(true);
    try {
      const { id } = await api("/api/patient/requests", { method: "POST", body });
      navigate(`/patient/requests/${id}`);
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  }

  function start(text) {
    const box = requestBox.current;
    box.value = text;
    box.focus();
    box.setSelectionRange(text.length, text.length);
  }

  return (
    <PatientLayout>
      <title>AgentCare</title>
      <div className="greeting">
        <h1>
          {greeting()}, {user.full_name.split(" ")[0]}
        </h1>
        <p>Tell us what you need. We'll handle the booking and the paperwork.</p>
      </div>
      <form className="card form" onSubmit={submit}>
        <label>
          Your request
          <textarea
            ref={requestBox}
            name="request_text"
            rows={5}
            required
            placeholder="For example: I need a cardiology follow-up next week."
          />
        </label>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
          {busy ? (
            "Sending…"
          ) : (
            <>
              Send request
              <ArrowRight aria-hidden="true" />
            </>
          )}
        </button>
      </form>
      <section>
        <h2 className="section-label">Or start with</h2>
        <div className="chips">
          {STARTERS.map(({ icon: Icon, label, text }) => (
            <button key={label} type="button" className="chip" onClick={() => start(text)}>
              <Icon aria-hidden="true" />
              {label}
            </button>
          ))}
        </div>
      </section>
    </PatientLayout>
  );
}
