import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { api } from "../api.js";

export default function Register({ setUser }) {
  const navigate = useNavigate();
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    const body = Object.fromEntries(new FormData(event.currentTarget));
    try {
      setUser(await api("/api/auth/register", { method: "POST", body }));
      navigate("/");
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <main>
      <title>Register - AgentCare</title>
      <h1>Register as a patient</h1>
      {error && <p className="error">{error}</p>}
      <form onSubmit={submit}>
        <label>
          Full name <input name="full_name" required autoFocus />
        </label>
        <label>
          Email <input type="email" name="email" required />
        </label>
        <label>
          Password (at least 8 characters) <input type="password" name="password" minLength={8} required />
        </label>
        <label>
          Date of birth <input type="date" name="date_of_birth" required />
        </label>
        <label>
          Phone <input type="tel" name="phone" required />
        </label>
        <button type="submit">Register</button>
      </form>
      <p>
        Already registered? <Link to="/login">Log in</Link>
      </p>
    </main>
  );
}
