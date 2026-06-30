"use client";

import { motion } from "framer-motion";
import { useNovaStore } from "@/lib/store";
import NavBar from "./nav-bar";
import NovaOverlay from "./nova-overlay";
import PageTransition from "./page-transition";
import SharedCalendar from "./shared-calendar";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const isShared = useNovaStore((s) => s.activeUser === "shared");

  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden">
      <div className="pointer-events-none absolute inset-0 z-0">
        <div className="grid-overlay" />
        <div className="radial-glow glow-tl" />
        <div className="radial-glow glow-br" />
      </div>

      {!isShared && <NovaOverlay />}

      <NavBar />

      <main className="relative z-[1] flex-1 overflow-hidden">
        {isShared ? (
          <motion.div
            key="shared"
            className="flex h-full w-full overflow-hidden"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <SharedCalendar />
          </motion.div>
        ) : (
          <PageTransition>{children}</PageTransition>
        )}
      </main>
    </div>
  );
}
