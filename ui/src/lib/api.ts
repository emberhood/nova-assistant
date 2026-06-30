import type {
  BudgetSummary,
  CalendarMonth,
  EnrollStatus,
  UserId,
  UsersResponse,
} from "./types";

export async function fetchBudgetSummary(user: UserId): Promise<BudgetSummary> {
  const res = await fetch(`/api/budget/summary?user=${user}`);
  return res.json();
}

export async function fetchCalendarMonth(
  year: number,
  month: number,
  user: UserId,
): Promise<CalendarMonth> {
  const res = await fetch(`/api/calendar/month?year=${year}&month=${month}&user=${user}`);
  return res.json();
}

export async function fetchEnrollStatus(): Promise<EnrollStatus> {
  const res = await fetch("/api/voice/enroll/status");
  return res.json();
}

export async function fetchUsers(): Promise<UsersResponse> {
  const res = await fetch("/api/users");
  return res.json();
}

export async function triggerVoice(): Promise<void> {
  await fetch("/api/voice/trigger", { method: "POST" });
}

export async function startEnroll(): Promise<{ status: string; message: string }> {
  const res = await fetch("/api/voice/enroll", { method: "POST" });
  return res.json();
}
