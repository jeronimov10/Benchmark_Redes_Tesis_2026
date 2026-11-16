// Semaforo de un puntaje de red o bloque con los cortes de la aplicacion.
export function lightFromScore(score: number): "green" | "yellow" | "red" {
  if (score >= 0.7) return "green";
  if (score >= 0.45) return "yellow";
  return "red";
}
