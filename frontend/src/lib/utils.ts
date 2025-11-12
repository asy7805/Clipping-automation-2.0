import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Clamp a score value to be between 0 and 1
 * Ensures scores never exceed 1.0
 */
export function clampScore(score: number | null | undefined): number {
  if (score == null || isNaN(score)) return 0;
  return Math.max(0, Math.min(1, score));
}
