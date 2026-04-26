export const ACCESS_TOKEN_STORAGE_KEY = "market-mapper-access-token";
export const DEFAULT_ACCESS_TOKEN = "dev-token";

export function resolveAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY) || DEFAULT_ACCESS_TOKEN;
}

export function storeAccessToken(token) {
  if (!token) {
    return;
  }
  localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
}

export function buildAuthHeaders(accessToken, headers = {}) {
  return {
    ...headers,
    Authorization: `Bearer ${accessToken}`,
  };
}

export function withAccessToken(url, accessToken) {
  if (!url) {
    return url;
  }
  const absoluteUrl = new URL(url, window.location.origin);
  absoluteUrl.searchParams.set("access_token", accessToken);
  return absoluteUrl.toString();
}
