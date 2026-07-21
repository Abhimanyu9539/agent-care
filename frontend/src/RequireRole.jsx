import { Link, Navigate, Outlet } from "react-router";

// Wraps the pages only some roles may open. The pages inside read `user` and `setUser`
// with useOutletContext(). The backend checks the role again on every API call.
export default function RequireRole({ user, setUser, roles }) {
  if (user === null) return <Navigate to="/login" replace />;
  if (!roles.includes(user.role)) {
    return (
      <main className="auth">
        <div className="card stack">
          <p className="error" role="alert">
            You do not have access to this page.
          </p>
          <Link to="/">Go to your start page</Link>
        </div>
      </main>
    );
  }
  return <Outlet context={{ user, setUser }} />;
}
