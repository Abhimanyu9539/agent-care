import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { api } from "../api.js";
import AuthLayout from "../AuthLayout.jsx";

export default function Register({ setUser }) {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    const body = Object.fromEntries(new FormData(event.currentTarget));
    setBusy(true);
    try {
      setUser(await api("/api/auth/register", { method: "POST", body }));
      navigate("/");
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  }

  return (
    <AuthLayout>
      <title>Register - AgentCare</title>
      <form className="card form" onSubmit={submit}>
        <div className="auth-intro">
          <h1>Register as a patient</h1>
          <p>Staff accounts are set up by the hospital.</p>
        </div>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <label>
          Full name
          <input name="full_name" autoComplete="name" required autoFocus />
        </label>
        <label>
          Email
          <input type="email" name="email" autoComplete="email" required />
        </label>
        <label>
          Password (at least 8 characters)
          <input type="password" name="password" autoComplete="new-password" minLength={8} required />
        </label>
        <label>
          Date of birth
          <input type="date" name="date_of_birth" autoComplete="bday" required />
        </label>
        <label>
          Phone
          <input type="tel" name="phone" autoComplete="tel" required />
        </label>
        <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
          {busy ? "Registering…" : "Register"}
        </button>
        <p className="center muted">
          Already registered? <Link to="/login">Log in</Link>
        </p>
      </form>
    </AuthLayout>
  );
}
