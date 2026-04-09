import type { DashboardData, NoticesPayload, StatusPayload, TimetablePayload } from "./dashboard";

let dashboardPromise: Promise<DashboardData> | null = null;

async function fetchJson<T>(url: string) {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status}`);
  }

  return (await response.json()) as T;
}

export function loadDashboardData() {
  if (!dashboardPromise) {
    dashboardPromise = Promise.all([
      fetchJson<StatusPayload>("/api/status.json"),
      fetchJson<TimetablePayload>("/api/timetable.json"),
      fetchJson<NoticesPayload>("/api/notices.json"),
    ]).then(([status, timetable, notices]) => ({
      status,
      timetable,
      notices,
    }));
  }

  return dashboardPromise;
}
