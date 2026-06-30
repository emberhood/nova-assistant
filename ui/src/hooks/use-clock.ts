"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

const emptySubscribe = () => () => {};

// True only after hydration — lets the clock render `null` on the server
// and during the first client render, then switch to live time.
function useIsClient() {
  return useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );
}

// Returns null until mounted to avoid SSR/client clock hydration mismatches.
export function useClock() {
  const isClient = useIsClient();
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  if (isClient && now === null) {
    return new Date();
  }
  return now;
}
