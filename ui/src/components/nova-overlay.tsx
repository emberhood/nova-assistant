"use client";

import { AnimatePresence, motion } from "framer-motion";
import { usePathname } from "next/navigation";
import { useNovaStore } from "@/lib/store";
import NovaOrb from "./nova-orb-3d";
import type { NovaState } from "@/lib/types";

const STATE_LABEL: Partial<Record<NovaState, string>> = {
  listening: "Ακούω...",
  processing: "Επεξεργάζομαι...",
  speaking: "Μιλάω...",
};

// Floating status badge shown on non-dashboard routes while Nova is active.
export default function NovaOverlay() {
  const pathname = usePathname();
  const novaState = useNovaStore((s) => s.novaState);
  const lastHeard = useNovaStore((s) => s.lastHeard);
  const lastResponse = useNovaStore((s) => s.lastResponse);

  const active = pathname !== "/" && novaState !== "idle";

  return (
    <AnimatePresence>
      {active && (
        <motion.div
          className="glass-strong pointer-events-none fixed bottom-6 right-6 z-[9999] flex max-w-[300px] items-center gap-3 rounded-full py-2 pl-2 pr-4 shadow-[0_4px_24px_rgba(0,0,0,0.4),0_0_0_1px_rgba(255,255,255,0.03)]"
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 40 }}
          transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
        >
          <div className="relative h-12 w-12 flex-shrink-0 overflow-visible">
            <NovaOrb state={novaState} size={48} />
          </div>

          <div className="flex min-w-0 flex-col gap-0.5">
            <span className="font-heading text-[11px] font-semibold uppercase tracking-[0.12em] text-nova-cyan">
              {STATE_LABEL[novaState]}
            </span>
            <AnimatePresence mode="wait">
              {novaState === "speaking" && lastResponse && (
                <motion.span
                  key="resp"
                  className="block max-w-[200px] truncate text-[11px] text-white/45"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  {lastResponse}
                </motion.span>
              )}
              {novaState === "processing" && lastHeard && (
                <motion.span
                  key="heard"
                  className="block max-w-[200px] truncate text-[11px] text-white/45"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  &quot;{lastHeard}&quot;
                </motion.span>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
