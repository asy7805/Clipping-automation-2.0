import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Clamp a score value to be between 0 and 1
 * Ensures scores never exceed 1.0
 */
/**
 * Parse score breakdown from transcript string
 * Format: "Score: X.XXX | {'energy': X, 'pitch': X, 'emotion': X, 'keyword': X} (estimated)\nTranscript..."
 */
export function parseScoreBreakdown(transcript: string | null | undefined): {
  breakdown: ScoreBreakdown | null;
  cleanTranscript: string;
} {
  if (!transcript) {
    return { breakdown: null, cleanTranscript: transcript || "" };
  }

  // Check if transcript starts with "Score:"
  if (!transcript.startsWith("Score:")) {
    return { breakdown: null, cleanTranscript: transcript };
  }

  // Extract the score line (first line)
  const lines = transcript.split("\n");
  const scoreLine = lines[0];
  const cleanTranscript = lines.slice(1).join("\n").trim();

  // Parse: "Score: 0.782 | {'energy': 0.2737, 'pitch': 0.1955, 'emotion': 0.3128, 'keyword': 0} (estimated)"
  const scoreMatch = scoreLine.match(/Score:\s*([\d.]+)/);
  const dictMatch = scoreLine.match(/\{'energy':\s*([\d.]+),\s*'pitch':\s*([\d.]+),\s*'emotion':\s*([\d.]+),\s*'keyword':\s*([\d.]+)\}/);

  if (scoreMatch && dictMatch) {
    const breakdown: ScoreBreakdown = {
      energy: parseFloat(dictMatch[1]),
      pitch: parseFloat(dictMatch[2]),
      emotion: parseFloat(dictMatch[3]),
      keyword: parseFloat(dictMatch[4]),
      final_score: parseFloat(scoreMatch[1])
    };
    return { breakdown, cleanTranscript };
  }

  return { breakdown: null, cleanTranscript };
}

export interface ScoreBreakdown {
  energy: number;
  pitch: number;
  emotion: number;
  keyword: number;
  final_score: number;
}

export function clampScore(score: number | null | undefined): number {
  if (score == null || isNaN(score)) return 0;
  return Math.max(0, Math.min(1, score));
}
