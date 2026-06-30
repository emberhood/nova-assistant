import { create } from "zustand";
import { fetchBudgetSummary, fetchCalendarMonth } from "./api";
import type { BudgetSummary, CalendarMonth, NovaState, UserId } from "./types";

interface UserCache {
  budget?: BudgetSummary | null;
  cal?: CalendarMonth | null;
}

interface NovaStore {
  activeUser: UserId;
  novaState: NovaState;
  lastHeard: string | null;
  lastResponse: string | null;
  budgetData: BudgetSummary | null;
  calData: CalendarMonth | null;
  cache: Partial<Record<UserId, UserCache>>;

  setActiveUser: (user: UserId) => void;
  refreshUserData: (user?: UserId) => void;
  setNovaState: (state: NovaState) => void;
  setLastHeard: (text: string) => void;
  setLastResponse: (text: string) => void;
  setBudgetData: (data: BudgetSummary | null, user?: UserId) => void;
  setCalData: (data: CalendarMonth | null, user?: UserId) => void;
  invalidateCalCache: (user: UserId) => void;
}

export const useNovaStore = create<NovaStore>((set, get) => ({
  activeUser: "owner",
  novaState: "idle",
  lastHeard: null,
  lastResponse: null,
  budgetData: null,
  calData: null,
  cache: {},

  // Apply theme + show cached data instantly, then refresh in the background
  setActiveUser: (user) => {
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("data-user", user);
    }
    const cached = get().cache[user];
    set({
      activeUser: user,
      budgetData: cached?.budget ?? null,
      calData: cached?.cal ?? null,
    });
    get().refreshUserData(user);
  },

  refreshUserData: (user) => {
    const u = user ?? get().activeUser;

    // shared has no budget
    if (u !== "shared") {
      fetchBudgetSummary(u)
        .then((d) => get().setBudgetData(d, u))
        .catch(() => {});
    } else {
      get().setBudgetData(null, u);
    }

    const today = new Date();
    fetchCalendarMonth(today.getFullYear(), today.getMonth() + 1, u)
      .then((d) => get().setCalData(d, u))
      .catch(() => {});
  },

  setNovaState: (novaState) => set({ novaState }),
  setLastHeard: (lastHeard) => set({ lastHeard }),
  setLastResponse: (lastResponse) => set({ lastResponse }),

  setBudgetData: (data, user) => {
    const u = user ?? get().activeUser;
    set((s) => ({
      ...(u === s.activeUser ? { budgetData: data } : {}),
      cache: { ...s.cache, [u]: { ...s.cache[u], budget: data } },
    }));
  },

  setCalData: (data, user) => {
    const u = user ?? get().activeUser;
    set((s) => ({
      ...(u === s.activeUser ? { calData: data } : {}),
      cache: { ...s.cache, [u]: { ...s.cache[u], cal: data } },
    }));
  },

  invalidateCalCache: (user) => {
    set((s) => ({
      cache: { ...s.cache, [user]: { ...s.cache[user], cal: undefined } },
    }));
  },
}));
