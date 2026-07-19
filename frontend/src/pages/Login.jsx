import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { api } from "../api.js";

export default function Login({ setUser }) {
  const navigate = useNavigate();
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    const body = Object.fromEntries(new FormData(event.currentTarget));
    try {
      setUser(await api("/api/auth/login", { method: "POST", body }));
      navigate("/");
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <main>
      <title>Log in - AgentCare</title>
      <h1>Log in</h1>
      {error && <p className="error">{error}</p>}
      <form onSubmit={submit}>
        <label>
          Email <input type="email" name="email" required autoFocus />
        </label>
        <label>
          Password <input type="password" name="password" required />
        </label>
        <button type="submit">Log in</button>
      </form>
      <p>
        New patient? <Link to="/register">Register</Link>
      </p>
    </main>
  );
}
