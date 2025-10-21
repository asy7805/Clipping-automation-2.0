import { Star, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface AIScoreDisplayProps {
  score: number;
  breakdown?: {
    audioEnergy: number;
    pitchVariance: number;
    emotionScore: number;
    keywordBoost: number;
  };
  size?: "sm" | "md" | "lg";
  showBreakdown?: boolean;
}

const getScoreColor = (score: number) => {
  if (score >= 0.7) return "text-score-gold";
  if (score >= 0.5) return "text-score-green";
  if (score >= 0.3) return "text-score-blue";
  return "text-score-gray";
};

const getScoreGradient = (score: number) => {
  if (score >= 0.7) return "from-score-gold via-yellow-400 to-score-gold";
  if (score >= 0.5) return "from-score-green via-emerald-400 to-score-green";
  if (score >= 0.3) return "from-score-blue via-blue-400 to-score-blue";
  return "from-score-gray via-gray-400 to-score-gray";
};

const getStarCount = (score: number) => {
  if (score >= 0.7) return 5;
  if (score >= 0.5) return 4;
  if (score >= 0.3) return 3;
  return 2;
};

export const AIScoreDisplay = ({ 
  score, 
  breakdown,
  size = "md",
  showBreakdown = false 
}: AIScoreDisplayProps) => {
  const [animated, setAnimated] = useState(false);
  const [displayScore, setDisplayScore] = useState(0);
  
  const circumference = 2 * Math.PI * 45; // radius = 45
  const offset = circumference - (displayScore / 1) * circumference;
  
  const stars = getStarCount(score);
  const isHighScore = score >= 0.7;

  const sizeClasses = {
    sm: "w-24 h-24",
    md: "w-32 h-32", 
    lg: "w-40 h-40"
  };

  const textSizes = {
    sm: "text-xl",
    md: "text-3xl",
    lg: "text-4xl"
  };

  useEffect(() => {
    // Trigger animation on mount
    setTimeout(() => setAnimated(true), 100);
    
    // Animate score counting up
    const duration = 1500;
    const steps = 60;
    const increment = score / steps;
    let current = 0;
    
    const timer = setInterval(() => {
      current += increment;
      if (current >= score) {
        setDisplayScore(score);
        clearInterval(timer);
      } else {
        setDisplayScore(current);
      }
    }, duration / steps);

    return () => clearInterval(timer);
  }, [score]);

  return (
    <div className="space-y-6">
      {/* Radial Progress Circle */}
      <div className="relative flex items-center justify-center">
        {/* Sparkle effects for high scores */}
        {isHighScore && (
          <>
            <Sparkles className="absolute -top-2 -right-2 w-6 h-6 text-score-gold animate-pulse" />
            <Sparkles className="absolute -bottom-2 -left-2 w-5 h-5 text-yellow-400 animate-pulse delay-75" />
            <Sparkles className="absolute top-0 left-0 w-4 h-4 text-score-gold animate-pulse delay-150" />
          </>
        )}

        {/* Glow effect for high scores */}
        {isHighScore && (
          <div className="absolute inset-0 rounded-full bg-score-gold/20 blur-2xl animate-pulse" />
        )}

        <div className={cn("relative", sizeClasses[size])}>
          {/* Background circle */}
          <svg className="w-full h-full transform -rotate-90">
            <circle
              cx="50%"
              cy="50%"
              r="45"
              stroke="hsl(var(--muted))"
              strokeWidth="8"
              fill="none"
              opacity="0.2"
            />
            {/* Animated progress circle */}
            <circle
              cx="50%"
              cy="50%"
              r="45"
              stroke="url(#scoreGradient)"
              strokeWidth="8"
              fill="none"
              strokeDasharray={circumference}
              strokeDashoffset={animated ? offset : circumference}
              strokeLinecap="round"
              className="transition-all duration-1500 ease-out"
              style={{
                filter: isHighScore ? 'drop-shadow(0 0 8px hsl(var(--score-gold)))' : 'none'
              }}
            />
            <defs>
              <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" className={cn("transition-colors", getScoreColor(score))} style={{ stopColor: `hsl(var(--${score >= 0.7 ? 'score-gold' : score >= 0.5 ? 'score-green' : score >= 0.3 ? 'score-blue' : 'score-gray'}))` }} />
                <stop offset="100%" className="text-pink-500" style={{ stopColor: 'hsl(330, 81%, 60%)' }} />
              </linearGradient>
            </defs>
          </svg>

          {/* Score value */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={cn(
              "font-bold tabular-nums",
              textSizes[size],
              getScoreColor(score),
              isHighScore && "animate-pulse"
            )}>
              {displayScore.toFixed(2)}
            </span>
            <div className="flex gap-0.5 mt-1">
              {[...Array(5)].map((_, i) => (
                <Star
                  key={i}
                  className={cn(
                    "w-3 h-3 transition-all duration-500",
                    i < stars 
                      ? `fill-current ${getScoreColor(score)} ${isHighScore && 'animate-pulse'}` 
                      : 'text-muted',
                    animated && i < stars && "scale-100",
                    !animated && "scale-0"
                  )}
                  style={{ transitionDelay: `${i * 100}ms` }}
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Score Breakdown */}
      {showBreakdown && breakdown && (
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            Score Breakdown
          </h4>
          
          <div className="space-y-3">
            {/* Audio Energy */}
            <div>
              <div className="flex items-center justify-between mb-1.5 text-sm">
                <span className="text-muted-foreground">🎧 Audio Energy</span>
                <span className="font-bold text-success tabular-nums">
                  {breakdown.audioEnergy.toFixed(2)}
                </span>
              </div>
              <div className="w-full bg-muted/30 rounded-full h-2 overflow-hidden">
                <div 
                  className={cn(
                    "h-full rounded-full bg-gradient-to-r from-success to-emerald-400",
                    "transition-all duration-1000 ease-out",
                    animated ? "w-full" : "w-0"
                  )}
                  style={{ 
                    width: animated ? `${breakdown.audioEnergy * 100}%` : '0%',
                    transitionDelay: '200ms'
                  }}
                />
              </div>
            </div>

            {/* Pitch Variance */}
            <div>
              <div className="flex items-center justify-between mb-1.5 text-sm">
                <span className="text-muted-foreground">📊 Pitch Variance</span>
                <span className="font-bold text-info tabular-nums">
                  {breakdown.pitchVariance.toFixed(2)}
                </span>
              </div>
              <div className="w-full bg-muted/30 rounded-full h-2 overflow-hidden">
                <div 
                  className={cn(
                    "h-full rounded-full bg-gradient-to-r from-info to-blue-400",
                    "transition-all duration-1000 ease-out"
                  )}
                  style={{ 
                    width: animated ? `${breakdown.pitchVariance * 100}%` : '0%',
                    transitionDelay: '400ms'
                  }}
                />
              </div>
            </div>

            {/* Emotion Score */}
            <div>
              <div className="flex items-center justify-between mb-1.5 text-sm">
                <span className="text-muted-foreground">💜 Emotion</span>
                <span className="font-bold text-primary tabular-nums">
                  {breakdown.emotionScore.toFixed(2)}
                </span>
              </div>
              <div className="w-full bg-muted/30 rounded-full h-2 overflow-hidden">
                <div 
                  className={cn(
                    "h-full rounded-full bg-gradient-to-r from-primary to-pink-500",
                    "transition-all duration-1000 ease-out"
                  )}
                  style={{ 
                    width: animated ? `${breakdown.emotionScore * 100}%` : '0%',
                    transitionDelay: '600ms'
                  }}
                />
              </div>
            </div>

            {/* Keyword Boost */}
            <div>
              <div className="flex items-center justify-between mb-1.5 text-sm">
                <span className="text-muted-foreground">🔑 Keywords</span>
                <span className="font-bold text-warning tabular-nums">
                  {breakdown.keywordBoost.toFixed(2)}
                </span>
              </div>
              <div className="w-full bg-muted/30 rounded-full h-2 overflow-hidden">
                <div 
                  className={cn(
                    "h-full rounded-full bg-gradient-to-r from-warning to-yellow-400",
                    "transition-all duration-1000 ease-out"
                  )}
                  style={{ 
                    width: animated ? `${breakdown.keywordBoost * 100}%` : '0%',
                    transitionDelay: '800ms'
                  }}
                />
              </div>
            </div>
          </div>

          {/* Formula display for high scores */}
          {isHighScore && (
            <div className="mt-4 p-3 rounded-lg bg-score-gold/10 border border-score-gold/20">
              <p className="text-xs text-muted-foreground text-center">
                ⭐ Exceptional Score - Highly Viral Potential
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
