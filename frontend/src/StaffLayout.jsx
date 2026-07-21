import { Stethoscope, TriangleAlert } from "lucide-react";
import { NavLink, useOutletContext } from "react-router";
import LogoutButton from "./LogoutButton.jsx";
import { Avatar, Logo, useFocusOnOpen } from "./ui.jsx";

// The staff console: a sidebar with the signed-in person and the staff pages, and the page beside it.
export default function StaffLayout({ title, subtitle, children }) {
  const { user } = useOutletContext();
  const main = useFocusOnOpen();

  return (
    <div className="staff">
      <aside className="sidebar">
        <Logo subtitle="Staff console" />
        <div className="user-card">
          <Avatar name={user.full_name} dark />
          <div>
            <div className="user-name">{user.full_name}</div>
            <div className="role">role: {user.role.toLowerCase()}</div>
          </div>
        </div>
        <nav className="side-nav" aria-label="Staff pages">
          <NavLink to="/staff/escalations">
            <TriangleAlert aria-hidden="true" />
            Escalations
          </NavLink>
          <NavLink to="/staff/slots">
            <Stethoscope aria-hidden="true" />
            Doctors and slots
          </NavLink>
        </nav>
        <div className="sidebar-foot">
          <LogoutButton />
        </div>
      </aside>
      <main className="staff-main" ref={main} tabIndex={-1}>
        <header className="page-head">
          <h1>{title}</h1>
          {subtitle && <p>{subtitle}</p>}
        </header>
        {children}
      </main>
    </div>
  );
}
