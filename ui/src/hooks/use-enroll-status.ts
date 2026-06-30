"use client";

import { useEffect, useState } from "react";
import { fetchEnrollStatus } from "@/lib/api";
import type { EnrollStatus } from "@/lib/types";

export function useEnrollStatus() {
  const [status, setStatus] = useState<EnrollStatus | null>(null);

  useEffect(() => {
    fetchEnrollStatus().then(setStatus).catch(() => {});
  }, []);

  return status;
}
