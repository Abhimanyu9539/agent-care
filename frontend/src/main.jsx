import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router";
import { api } from "./api.js";
import RequireRole from "./RequireRole.jsx";
import Login from "./pages/Login.jsx";
import PatientHome from "./pages/PatientHome.jsx";
import PatientRequest from "./pages/PatientRequest.jsx";
import Register from "./pages/Register.jsx";
import StaffSlots from "./pages/StaffSlots.jsx";
import "./styles.css";

// The start page for each visitor.
function startPage(user) {
  if (user === null) return "/login";
  return user.role === "PATIENT" ? "/patient" : "/staff/slots";
}

function App() {
  // undefined while we ask the backend who is signed in, null when nobody is.
  const [user, setUser] = useState(undefined);

  useEffect(() => {
    api("/api/auth/me").then(setUser, () => setUser(null));
  }, []);

  if (user === undefined) return null;

  return (
    <Routes>
      <Route path="/" element={<Navigate to={startPage(user)} replace />} />
      <Route path="/login" element={<Login setUser={setUser} />} />
      <Route path="/register" element={<Register setUser={setUser} />} />
      <Route element={<RequireRole user={user} setUser={setUser} roles={["PATIENT"]} />}>
        <Route path="/patient" element={<PatientHome />} />
        <Route path="/patient/requests/:id" element={<PatientRequest />} />
      </Route>
      <Route element={<RequireRole user={user} setUser={setUser} roles={["STAFF", "ADMIN"]} />}>
        <Route path="/staff/slots" element={<StaffSlots />} />
      </Route>
      <Route
        path="*"
        element={
          <main>
            <h1>Page not found</h1>
            <p>
              <Link to="/">Go to the start page</Link>
            </p>
          </main>
        }
      />
    </Routes>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
