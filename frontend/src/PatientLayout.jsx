import { ChevronLeft } from "lucide-react";
import { Link, useOutletContext } from "react-router";
import LogoutButton from "./LogoutButton.jsx";
import { Avatar, Logo, SafetyNote, useFocusOnOpen } from "./ui.jsx";

// The patient pages: a top bar, one narrow column, and the safety note at the end.
// With a `title`, the top bar shows a back link and that title instead of the logo.
export default function PatientLayout({ title, subtitle, children }) {
  const { user } = useOutletContext();
  const main = useFocusOnOpen();

  return (
    <>
      <header className="topbar">
        {title ? (
          <div className="topbar-inner topbar-sub">
            <Link to="/patient" className="icon-link" aria-label="Back to home">
              <ChevronLeft aria-hidden="true" />
            </Link>
            <div className="topbar-title">
              <h1>{title}</h1>
              {subtitle && <p className="mono muted">{subtitle}</p>}
            </div>
          </div>
        ) : (
          <div className="topbar-inner">
            <Link to="/patient" className="logo-link">
              <Logo />
            </Link>
            <div className="topbar-user">
              <LogoutButton />
              <Avatar name={user.full_name} />
            </div>
          </div>
        )}
      </header>
      <main className="patient-main" ref={main} tabIndex={-1}>
        {children}
        <SafetyNote />
      </main>
    </>
  );
}
