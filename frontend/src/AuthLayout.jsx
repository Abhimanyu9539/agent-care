import { ArrowRightFromLine, BellRing, CalendarCheck, FileText, Users } from "lucide-react";
import { Logo, SafetyNote } from "./ui.jsx";

const FEATURES = [
  [CalendarCheck, "Visits booked and moved for you"],
  [FileText, "Documents sorted into your record"],
  [BellRing, "Reminders before every visit"],
];

// The sign-in pages: a teal brand panel beside the form on wide screens, a short header above it on phones.
export default function AuthLayout({ children }) {
  return (
    <div className="auth-page">
      <aside className="auth-panel">
        <Logo subtitle="Patient administration and care coordination" />
        <div className="auth-pitch">
          <p className="auth-headline">Patient care, coordinated.</p>
          <p>
            Tell us what you need in your own words. AgentCare handles the booking and the paperwork, and hands anything
            medical to a person.
          </p>
          <ul className="auth-features">
            {FEATURES.map(([Icon, text]) => (
              <li key={text}>
                <span className="feature-icon" aria-hidden="true">
                  <Icon />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>
        <p className="auth-panel-foot">
          <Users aria-hidden="true" />
          One sign-in for patients and hospital staff.
        </p>
        <ArrowRightFromLine className="auth-watermark" strokeWidth={1.5} aria-hidden="true" />
      </aside>
      <main className="auth-main">
        {children}
        <SafetyNote />
      </main>
    </div>
  );
}
