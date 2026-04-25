// D-23-G sentiment helper tests · 2026-04-24
// No framework (el frontend no tiene vitest/jest) · ejecutable con Node:
//   cd frontend && node src/lib/politica/__tests__/sentiment.test.mjs
// Sale con exit 0 si pasa todo, exit 1 si falla.
//
// Reimplementa la lógica para testearla aislada del bundle TS. Si la fuente
// en `sentiment.ts` cambia, actualizar también este test.

import assert from "node:assert/strict";

// Replica mínima de rol.ts · alinear con frontend/src/lib/politica/rol.ts
const PARTIDO_A_ROL = {
  MORENA: "oficialismo",
  PT: "oficialismo",
  PVEM: "oficialismo",
  PAN: "oposicion",
  PRI: "oposicion",
  PRD: "oposicion",
  MC: "oposicion",
  INDEPENDIENTE: "independiente",
  SIN_PARTIDO: "independiente",
};
const rolFromPartido = (p) => {
  if (!p) return "independiente";
  return PARTIDO_A_ROL[p.trim().toUpperCase()] ?? "independiente";
};

// Replica de sentiment.ts
const adjustSentimentScoreForRole = (score, partido) => {
  if (score == null) return null;
  return rolFromPartido(partido) === "oposicion" ? -score : score;
};
const adjustSentimentLabelForRole = (label, partido) => {
  if (!label) return null;
  if (rolFromPartido(partido) !== "oposicion") return label;
  const k = label.toLowerCase();
  if (k === "positive") return "negative";
  if (k === "negative") return "positive";
  return label;
};
const adjustSentimentDistributionForRole = (dist, partido) => {
  if (rolFromPartido(partido) !== "oposicion") return dist;
  return { ...dist, positive: dist.negative, negative: dist.positive };
};
const deriveSentimentLabelFromScore = (score) => {
  if (score == null) return null;
  if (score > 0.2) return "positive";
  if (score < -0.2) return "negative";
  return "neutral";
};

// ─── Tests ─────────────────────────────────────────────────
let passed = 0;
let failed = 0;
const run = (name, fn) => {
  try {
    fn();
    console.log(`  ✓ ${name}`);
    passed++;
  } catch (e) {
    console.error(`  ✗ ${name}\n    ${e.message}`);
    failed++;
  }
};

console.log("adjustSentimentScoreForRole");
run("MC (oposición) flipa score positivo a negativo", () => {
  assert.equal(adjustSentimentScoreForRole(0.67, "MC"), -0.67);
});
run("MC (oposición) flipa score negativo a positivo", () => {
  assert.equal(adjustSentimentScoreForRole(-0.59, "MC"), 0.59);
});
run("MORENA (oficialismo) mantiene score crudo", () => {
  assert.equal(adjustSentimentScoreForRole(-0.67, "MORENA"), -0.67);
});
run("null partido → independiente → mantiene crudo", () => {
  assert.equal(adjustSentimentScoreForRole(0.5, null), 0.5);
});
run("partido unknown → independiente → mantiene crudo", () => {
  assert.equal(adjustSentimentScoreForRole(0.3, "UNKNOWN_PARTY"), 0.3);
});
run("score null → null (no fabricar)", () => {
  assert.equal(adjustSentimentScoreForRole(null, "MC"), null);
});
run("score 0 flipado sigue 0", () => {
  assert.equal(adjustSentimentScoreForRole(0, "MC"), -0);
});
run("partido lowercase MC mayúsculas normalizan", () => {
  assert.equal(adjustSentimentScoreForRole(0.5, "mc"), -0.5);
});

console.log("\nadjustSentimentLabelForRole");
run("oposición swap positive → negative", () => {
  assert.equal(adjustSentimentLabelForRole("positive", "MC"), "negative");
});
run("oposición swap negative → positive", () => {
  assert.equal(adjustSentimentLabelForRole("negative", "PAN"), "positive");
});
run("oposición mantiene neutral", () => {
  assert.equal(adjustSentimentLabelForRole("neutral", "MC"), "neutral");
});
run("oficialismo mantiene positive", () => {
  assert.equal(adjustSentimentLabelForRole("positive", "MORENA"), "positive");
});
run("label null → null", () => {
  assert.equal(adjustSentimentLabelForRole(null, "MC"), null);
});
run("label Uppercase Positive → negative (lowercase compare)", () => {
  assert.equal(adjustSentimentLabelForRole("Positive", "MC"), "negative");
});

console.log("\nadjustSentimentDistributionForRole");
run("oposición swap positive/negative counts", () => {
  const dist = { positive: 10, negative: 20, neutral: 5, total: 35 };
  const r = adjustSentimentDistributionForRole(dist, "MC");
  assert.equal(r.positive, 20);
  assert.equal(r.negative, 10);
  assert.equal(r.neutral, 5);
  assert.equal(r.total, 35);
});
run("oficialismo mantiene distribución", () => {
  const dist = { positive: 10, negative: 20, neutral: 5 };
  const r = adjustSentimentDistributionForRole(dist, "MORENA");
  assert.deepEqual(r, dist);
});

console.log("\nderiveSentimentLabelFromScore");
run("0.59 > 0.2 → positive", () => {
  assert.equal(deriveSentimentLabelFromScore(0.59), "positive");
});
run("-0.59 < -0.2 → negative", () => {
  assert.equal(deriveSentimentLabelFromScore(-0.59), "negative");
});
run("0.2 exacto (no mayor) → neutral", () => {
  assert.equal(deriveSentimentLabelFromScore(0.2), "neutral");
});
run("-0.2 exacto (no menor) → neutral", () => {
  assert.equal(deriveSentimentLabelFromScore(-0.2), "neutral");
});
run("0 → neutral", () => {
  assert.equal(deriveSentimentLabelFromScore(0), "neutral");
});
run("-0.5 (Piña flipado) → negative (resuelve bug Neutral -50%)", () => {
  assert.equal(deriveSentimentLabelFromScore(-0.5), "negative");
});
run("null → null", () => {
  assert.equal(deriveSentimentLabelFromScore(null), null);
});
run("undefined → null", () => {
  assert.equal(deriveSentimentLabelFromScore(undefined), null);
});

console.log(`\n${passed} passed · ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
