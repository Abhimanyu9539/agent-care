import { CalendarX } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api.js";
import StaffLayout from "../StaffLayout.jsx";
import { Pill } from "../ui.jsx";

const dateTime = new Intl.DateTimeFormat("en-GB", {
  weekday: "short",
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

// `starts_at` is already the hospital's wall-clock time with no offset, such as "2026-11-15T09:00:00".
// Read as local time and printed back, it shows that same time: "Sun 15 Nov 2026, 09:00".
function formatStart(startsAt) {
  return dateTime.format(new Date(startsAt.slice(0, 19))).replace(",", "");
}

const SLOT_STATUS = {
  AVAILABLE: ["done", "Available"],
  HELD: ["approval", "Held"],
  BOOKED: ["info", "Booked"],
  BLOCKED: ["neutral", "Blocked"],
};

// Upcoming appointment slots for every doctor.
export default function StaffSlots() {
  const [slots, setSlots] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/staff/slots").then(setSlots, (e) => setError(e.message));
  }, []);

  return (
    <StaffLayout title="Doctors and slots" subtitle="Upcoming appointment slots for every doctor, soonest first.">
      <title>Slots - AgentCare</title>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {slots?.length === 0 && (
        <div className="card empty">
          <CalendarX aria-hidden="true" />
          No upcoming slots.
        </div>
      )}
      {slots?.length > 0 && (
        <>
          <div className="table-card">
            <table>
              <thead>
                <tr>
                  <th>Slot</th>
                  <th>Starts</th>
                  <th>Doctor</th>
                  <th>Department</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {slots.map((slot) => {
                  const [tone, label] = SLOT_STATUS[slot.status] ?? ["neutral", slot.status];
                  return (
                    <tr key={slot.id}>
                      <td className="mono">S-{slot.id}</td>
                      <td className="mono nowrap">{formatStart(slot.starts_at)}</td>
                      <td>{slot.doctor}</td>
                      <td>{slot.department}</td>
                      <td>
                        <Pill tone={tone}>{label}</Pill>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="muted">Showing the next {slots.length} slots.</p>
        </>
      )}
    </StaffLayout>
  );
}
