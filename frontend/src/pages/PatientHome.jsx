import { useState } from "react";
import { useNavigate, useOutletContext } from "react-router";
import { api } from "../api.js";
import LogoutButton from "../LogoutButton.jsx";

// The form where a patient describes what they need.
export default function PatientHome() {
  const { user } = useOutletContext();
  const navigate = useNavigate();
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    const body = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const { id } = await api("/api/patient/requests", { method: "POST", body });
      navigate(`/patient/requests/${id}`);
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <main>
      <title>AgentCare</title>
      <h1>
        Signed in as {user.full_name} ({user.role})
      </h1>
      {error && <p className="error">{error}</p>}
      <form onSubmit={submit}>
        <label>
          What do you need?
          <textarea
            name="request_text"
            rows={5}
            required
            placeholder="For example: I need a cardiology follow-up next week."
          />
        </label>
        <button type="submit">Send request</button>
      </form>
      <LogoutButton />
    </main>
  );
}
