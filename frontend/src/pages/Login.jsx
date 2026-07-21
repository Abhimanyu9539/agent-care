import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { api } from "../api.js";
import { Logo } from "../ui.jsx";

export default function Login({ setUser }) {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    const body = Object.fromEntries(new FormData(event.currentTarget));
    setBusy(true);
    try {
      setUser(await api("/api/auth/login", { method: "POST", body }));
      navigate("/");
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  }

  return (
    <main className="auth">
      <title>Log in - AgentCare</title>
      <Logo subtitle="Patient administration and care coordination" />
      <form className="card form" onSubmit={submit}>
        <h1>Log in</h1>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <label>
          Email
          <input type="email" name="email" autoComplete="username" required autoFocus />
        </label>
        <label>
          Password
          <input type="password" name="password" autoComplete="current-password" required />
        </label>
        <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
          {busy ? "Logging in…" : "Log in"}
        </button>
        <p className="center muted">
          New patient? <Link to="/register">Register</Link>
        </p>
      </form>
    </main>
  );
}
