import { useEffect, useState } from "react";
import { useOutletContext } from "react-router";
import { api } from "../api.js";
import LogoutButton from "../LogoutButton.jsx";

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

// Upcoming appointment slots for every doctor.
export default function StaffSlots() {
  const { user } = useOutletContext();
  const [slots, setSlots] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/staff/slots").then(setSlots, (e) => setError(e.message));
  }, []);

  return (
    <main className="wide">
      <title>Slots - AgentCare</title>
      <h1>Upcoming slots</h1>
      <p>
        Signed in as {user.full_name} ({user.role})
      </p>
      {error && <p className="error">{error}</p>}
      {slots?.length === 0 && <p>No upcoming slots.</p>}
      {slots?.length > 0 && (
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
            {slots.map((slot) => (
              <tr key={slot.id}>
                <td>S-{slot.id}</td>
                <td>{formatStart(slot.starts_at)}</td>
                <td>{slot.doctor}</td>
                <td>{slot.department}</td>
                <td>{slot.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <LogoutButton />
    </main>
  );
}
