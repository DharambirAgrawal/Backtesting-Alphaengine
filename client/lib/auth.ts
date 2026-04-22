const TOKEN_KEY = "token";
const ROLE_KEY = "role";
const EMAIL_KEY = "email";

function isBrowser() {
  return typeof window !== "undefined";
}

function getCookie(name: string): string | null {
  if (!isBrowser()) return null;
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = document.cookie.match(
    new RegExp(`(?:^|; )${escaped}=([^;]*)`)
  );
  return match ? decodeURIComponent(match[1]) : null;
}

function setCookie(name: string, value: string, maxAgeSeconds: number) {
  if (!isBrowser()) return;
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${name}=${encodeURIComponent(value)}; Path=/; Max-Age=${maxAgeSeconds}; SameSite=Lax${secure}`;
}

function clearCookie(name: string) {
  if (!isBrowser()) return;
  document.cookie = `${name}=; Path=/; Max-Age=0; SameSite=Lax`;
}

export function saveToken(token: string, role: string, email: string) {
  if (!isBrowser()) return;

  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(ROLE_KEY, role);
  localStorage.setItem(EMAIL_KEY, email);

  const maxAge = 60 * 60 * 24 * 30;
  setCookie(TOKEN_KEY, token, maxAge);
  setCookie(ROLE_KEY, role, maxAge);
  setCookie(EMAIL_KEY, email, maxAge);
}

export function getToken(): string | null {
  if (!isBrowser()) return null;
  return localStorage.getItem(TOKEN_KEY) ?? getCookie(TOKEN_KEY);
}

export function getRole(): string | null {
  if (!isBrowser()) return null;
  return localStorage.getItem(ROLE_KEY) ?? getCookie(ROLE_KEY);
}

export function getEmail(): string | null {
  if (!isBrowser()) return null;
  return localStorage.getItem(EMAIL_KEY) ?? getCookie(EMAIL_KEY);
}

export function isAuthenticated() {
  return Boolean(getToken());
}

export function logout() {
  if (!isBrowser()) return;

  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
  localStorage.removeItem(EMAIL_KEY);

  clearCookie(TOKEN_KEY);
  clearCookie(ROLE_KEY);
  clearCookie(EMAIL_KEY);

  window.location.href = "/login";
}
