"use client";

import { useRouter } from "next/navigation";
import { useNovaStore } from "@/lib/store";
import type { UserId } from "@/lib/types";

// Switching to "shared" resets the route back to "/" (matches legacy
// behavior of resetting the panel to "dashboard"); the app shell then
// swaps the whole content area for SharedCalendar regardless of route.
export function useSelectUser() {
  const router = useRouter();
  const setActiveUser = useNovaStore((s) => s.setActiveUser);

  return (user: UserId) => {
    setActiveUser(user);
    if (user === "shared") router.push("/");
  };
}
