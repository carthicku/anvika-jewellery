/** Seconds since a form was opened — a cheap anti-bot signal sent with public forms. */
export function secondsSince(openedAtMs: number): number {
  return Math.max(0, Math.round((Date.now() - openedAtMs) / 1000));
}
