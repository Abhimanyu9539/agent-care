import { Navigate, Outlet } from "react-router";

// Wraps the pages only some roles may open. The pages inside read `user` and `setUser`
// with useOutletContext(). The backend checks the role again on every API call.
export default function RequireRole({ user, setUser, roles }) {
  if (user === null) return <Navigate to="/login" replace />;
  if (!roles.includes(user.role)) {
    return (
      <main>
        <p className="error">You do not have access to this page.</p>
      </main>
    );
  }
  return <Outlet context={{ user, setUser }} />;
}
