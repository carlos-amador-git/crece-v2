"use client";

import { type ReactNode } from "react";
import { motion, MotionConfig } from "motion/react";

interface FadeUpProps {
  children: ReactNode;
  index?: number;
  className?: string;
}

/**
 * Fade-up stagger animation wrapper.
 * Uses index % 6 to cap stagger delay on long grids (Gemini G6).
 * Delay: 0.05s per item, duration: 0.3s (Gemini G3).
 */
export function FadeUp({ children, index = 0, className }: FadeUpProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{
        delay: (index % 6) * 0.05,
        duration: 0.3,
        ease: "easeOut",
      }}
      style={{ willChange: "transform, opacity" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/**
 * Wrap at layout level to automatically respect prefers-reduced-motion.
 * Usage: <MotionProvider>{children}</MotionProvider>
 */
export function MotionProvider({ children }: { children: ReactNode }) {
  return (
    <MotionConfig reducedMotion="user">
      {children}
    </MotionConfig>
  );
}
