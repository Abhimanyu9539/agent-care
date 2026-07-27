import { ArrowRightFromLine, Check, Clock, ShieldCheck, TriangleAlert, User, X } from "lucide-react";
import { useEffect, useRef } from "react";

// Small pieces shared by the pages, drawn from the look and feel in docs/AgentCare UI design.pdf.

export function Logo({ subtitle }) {
  return (
    <span className="logo">
      <span className="logo-mark" aria-hidden="true">
        <ArrowRightFromLine strokeWidth={2.5} />
      </span>
      <span>
        AgentCare
        {subtitle && <small>{subtitle}</small>}
      </span>
    </span>
  );
}

export function Avatar({ name, dark = false }) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0].toUpperCase())
    .join("");
  return (
    <span className={dark ? "avatar avatar-dark" : "avatar"} title={name} aria-hidden="true">
      {initials}
    </span>
  );
}

// A coloured status label. `tone` picks the colour: done, neutral, info, approval, urgent or failed.
// The word carries the meaning; the icon only repeats it, so screen readers skip the icon.
export function Pill({ tone, icon, children }) {
  return (
    <span className={`pill pill-${tone}`}>
      {icon && (
        <span className="pill-icon" aria-hidden="true">
          {icon}
        </span>
      )}
      {children}
    </span>
  );
}

// How each workflow status reads to a patient.
const RUN_STATUS = {
  RUNNING: { tone: "neutral", icon: <span className="dot" />, label: "Running" },
  WAITING_PATIENT_INPUT: { tone: "info", icon: <Clock />, label: "Waiting for you" },
  WAITING_APPROVAL: { tone: "approval", icon: <User />, label: "Needs approval" },
  ESCALATED: { tone: "urgent", icon: <TriangleAlert />, label: "Escalated" },
  COMPLETED: { tone: "done", icon: <Check />, label: "Completed" },
  FAILED: { tone: "failed", icon: <X />, label: "Failed" },
  CANCELLED: { tone: "neutral", icon: <X />, label: "Cancelled" },
};

// Staff see a run that has been RUNNING with no progress for 10 minutes as Stuck.
const STUCK = { tone: "failed", icon: <Clock />, label: "Stuck" };

export function RunStatus({ status, stuck = false }) {
  const { tone, icon, label } = stuck ? STUCK : (RUN_STATUS[status] ?? { tone: "neutral", label: status });
  return (
    <Pill tone={tone} icon={icon}>
      {label}
    </Pill>
  );
}

// A ref for a page's <main>: focused when the page opens, so screen readers start at the new content.
export function useFocusOnOpen() {
  const main = useRef(null);
  useEffect(() => main.current?.focus(), []);
  return main;
}

// The safety boundary stays on screen for patients: medicine stays with people.
export function SafetyNote() {
  return (
    <aside className="safety-note">
      <ShieldCheck aria-hidden="true" />
      <p>
        AgentCare books visits and organises documents. It can't diagnose or advise on medicines. Emergency?{" "}
        <a href="tel:112">Call 112</a>
      </p>
    </aside>
  );
}
