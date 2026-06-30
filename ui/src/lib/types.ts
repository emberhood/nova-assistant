export type UserId = "owner" | "andriana" | "shared";

export type NovaState = "idle" | "listening" | "processing" | "speaking";

export type PanelId = "dashboard" | "calendar" | "budget";

export type WsMessage =
  | { type: "nova_state"; payload: NovaState; text?: string; heard?: string }
  | { type: "navigate"; tab: PanelId }
  | { type: "set_user"; user: UserId }
  | { type: "refresh_calendar" };

export interface CalendarEvent {
  title: string;
  time: string; // "HH:MM" or "all day"
}

export interface CalendarDay {
  date: string; // ISO date (YYYY-MM-DD)
  day: number;
  month: number;
  year: number;
  isCurrentMonth: boolean;
  isToday: boolean;
  isWeekend: boolean;
  events: CalendarEvent[];
}

export type CalendarWeek = CalendarDay[];

export interface CalendarMonth {
  year: number;
  month: number;
  monthName: string;
  today: string;
  weeks: CalendarWeek[];
  user: string;
}

export interface BudgetAccount {
  name: string;
  balance: number;
}

export interface BudgetExpense {
  notes: string | null;
  amount: number;
  date: string;
  category: string | null;
}

export interface BudgetSummaryAvailable {
  available: true;
  totalBalance: number;
  monthIncome: number;
  monthExpenses: number;
  accounts: BudgetAccount[];
  recentExpenses: BudgetExpense[];
}

export interface BudgetSummaryUnavailable {
  available: false;
  error?: string;
}

export type BudgetSummary = BudgetSummaryAvailable | BudgetSummaryUnavailable;

export interface EnrollStatus {
  enrolled: boolean;
  available: boolean;
  threshold: number;
}

export interface UserProfile {
  id: string;
  name: string;
  short: string;
  theme: string;
}

export interface UsersResponse {
  users: UserProfile[];
  shared_calendar: string;
}
