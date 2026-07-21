// Every call to the FastAPI backend goes through here. It sends and receives JSON.
// The session cookie goes along by itself, because the API is on the same origin.
export async function api(path, { method = "GET", body } = {}) {
  const response = await fetch(path, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  // 204 and non-JSON errors (such as a proxy error while the backend is down) have no JSON body.
  const data = await response.json().catch(() => null);
  if (response.ok) return data;

  // The session ended (logged out elsewhere, or deactivated): start again at the login page.
  // /api/auth/ is left out, because a 401 there is an ordinary "not signed in" answer.
  if (response.status === 401 && !path.startsWith("/api/auth/")) {
    window.location.assign("/login");
  }
  const error = new Error(typeof data?.detail === "string" ? data.detail : "Something went wrong. Please try again.");
  error.status = response.status;
  throw error;
}
