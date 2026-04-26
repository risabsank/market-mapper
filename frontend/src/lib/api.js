import { buildAuthHeaders } from "./auth.js";

export async function getJson(url, accessToken) {
  const response = await fetch(url, {
    headers: buildAuthHeaders(accessToken),
  });
  if (!response.ok) {
    throw await buildRequestError(response);
  }
  return response.json();
}

export async function postJsonRequest(url, payload, accessToken) {
  const response = await fetch(url, {
    method: "POST",
    headers: buildAuthHeaders(accessToken, {
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw await buildRequestError(response);
  }
  return response.json();
}

export async function deleteJsonRequest(url, accessToken) {
  const response = await fetch(url, {
    method: "DELETE",
    headers: buildAuthHeaders(accessToken),
  });
  if (!response.ok) {
    throw await buildRequestError(response);
  }
}

export async function fetchBlob(url, accessToken) {
  const response = await fetch(url, {
    headers: buildAuthHeaders(accessToken),
  });
  if (!response.ok) {
    throw await buildRequestError(response);
  }
  return response.blob();
}

export async function readErrorPayload(response) {
  try {
    const payload = await response.json();
    return payload.detail || payload.message || null;
  } catch (_error) {
    return null;
  }
}

async function buildRequestError(response) {
  const payload = await readErrorPayload(response);
  const error = new Error(payload || `Request failed with status ${response.status}`);
  error.status = response.status;
  return error;
}
