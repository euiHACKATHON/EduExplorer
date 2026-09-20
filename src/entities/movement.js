// Exponential smoothing feels the same at different frame rates.
export function smoothVelocity(current, target, delta, braking = false) {
  const blend =
    1 - Math.exp((-(braking ? 24 : 14) * Math.min(delta, 50)) / 1000);
  const next = current + (target - current) * blend;
  return Math.abs(next) < 0.5 ? 0 : next;
}
