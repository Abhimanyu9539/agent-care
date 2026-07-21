import { LogOut } from "lucide-react";
import { useOutletContext } from "react-router";
import { api } from "./api.js";

export default function LogoutButton() {
  const { setUser } = useOutletContext();

  async function logOut() {
    await api("/api/auth/logout", { method: "POST" });
    setUser(null); // RequireRole then sends the visitor to /login.
  }

  return (
    <button type="button" className="btn-ghost" onClick={logOut}>
      <LogOut aria-hidden="true" />
      Log out
    </button>
  );
}
