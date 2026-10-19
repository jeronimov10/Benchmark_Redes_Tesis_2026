/** Traffic light of a network or block score, with the app's cut-offs (0.70 / 0.45). */
export function lightFromScore(score: number): "green" | "yellow" | "red" {
  if (score >= 0.7) return "green";
  if (score >= 0.45) return "yellow";
  return "red";
}
