import { withAccessToken } from "./auth.js";

export function openSessionStream({
  sessionId,
  accessToken,
  onWorkspace,
  onRunStatus,
  onRunEvents,
  onApprovedDashboard,
  onError,
}) {
  const streamUrl = withAccessToken(`/api/sessions/${encodeURIComponent(sessionId)}/stream`, accessToken);
  const source = new EventSource(streamUrl);

  bindJsonEvent(source, "workspace", onWorkspace);
  bindJsonEvent(source, "run_status", onRunStatus);
  bindJsonEvent(source, "run_events", onRunEvents);
  bindJsonEvent(source, "approved_dashboard", onApprovedDashboard);
  bindJsonEvent(source, "error", onError);

  source.onerror = () => {
    if (typeof onError === "function") {
      onError({ message: "Session event stream disconnected." });
    }
  };

  return source;
}

function bindJsonEvent(source, eventName, handler) {
  if (typeof handler !== "function") {
    return;
  }
  source.addEventListener(eventName, (event) => {
    try {
      handler(JSON.parse(event.data));
    } catch (_error) {
      handler({ message: `Received malformed ${eventName} payload.` });
    }
  });
}
