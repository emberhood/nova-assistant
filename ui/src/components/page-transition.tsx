"use client";

import { AnimatePresence, motion } from "framer-motion";
import { usePathname } from "next/navigation";
import { useState } from "react";

const ROUTE_ORDER = ["/", "/calendar", "/budget"];

const variants = {
  enter: (dir: number) => ({ opacity: 0, x: dir > 0 ? 60 : -60, scale: 0.97 }),
  center: { opacity: 1, x: 0, scale: 1 },
  exit: (dir: number) => ({ opacity: 0, x: dir < 0 ? 60 : -60, scale: 0.97 }),
};

// Slides routes in/out based on their order in the nav (left<->right),
// mirroring the original panel-index direction logic.
export default function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [prevPathname, setPrevPathname] = useState(pathname);
  const [dir, setDir] = useState(1);

  if (pathname !== prevPathname) {
    const prevIndex = ROUTE_ORDER.indexOf(prevPathname);
    const currentIndex = ROUTE_ORDER.indexOf(pathname);
    if (currentIndex !== -1) setDir(currentIndex >= prevIndex ? 1 : -1);
    setPrevPathname(pathname);
  }

  return (
    <AnimatePresence mode="wait" custom={dir}>
      <motion.div
        key={pathname}
        custom={dir}
        variants={variants}
        initial="enter"
        animate="center"
        exit="exit"
        transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
        className="flex h-full w-full overflow-hidden"
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
