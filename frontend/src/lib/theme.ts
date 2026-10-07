/** Theme handling: `dark` class on <html>, persisted in localStorage. Dark by default. */

export type ThemeMode = "dark" | "light";

const KEY = "sentinel-theme";

export function getTheme(): ThemeMode {
  if (typeof localStorage === "undefined") return "dark";
  return localStorage.getItem(KEY) === "light" ? "light" : "dark";
}

export function applyTheme(mode: ThemeMode): void {
  const root = document.documentElement;
  root.classList.toggle("dark", mode === "dark");
  localStorage.setItem(KEY, mode);
}
