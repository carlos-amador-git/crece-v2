import type { ReactNode } from "react";

const BOLD_RE = /(\*\*[^*]+\*\*)/g;

export function renderRichText(text: string): ReactNode {
  if (!text) return null;
  const parts = text.split(BOLD_RE);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}
