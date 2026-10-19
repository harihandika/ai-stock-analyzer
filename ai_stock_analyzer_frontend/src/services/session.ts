import Cookies from "js-cookie";
export function storeSession(access: string, refresh?: string) {
  const secure =
    typeof window !== "undefined" && window.location.protocol === "https:";
  Cookies.set("access_token", access, {
    secure,
    sameSite: "strict",
    path: "/",
    expires: 1,
  });
  if (refresh)
    Cookies.set("refresh_token", refresh, {
      secure,
      sameSite: "strict",
      path: "/",
      expires: 7,
    });
}
export function clearSession() {
  Cookies.remove("access_token", { path: "/" });
  Cookies.remove("refresh_token", { path: "/" });
  if (typeof window !== "undefined")
    window.dispatchEvent(new Event("auth-expired"));
}
