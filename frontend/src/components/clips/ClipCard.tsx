import { Play, Download, Share2, Trash2, Star } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn, clampScore } from "@/lib/utils";
import { AIScoreDisplay } from "@/components/AIScoreDisplay";
import { useVideoPlayer } from "@/contexts/VideoPlayerContext";
import { Clip } from "@/hooks/useClips";

interface ClipCardProps {
  clip: {
    id: string;
    thumbnail: string;
    score: number;
    channel: string;
    avatar: string;
    category: string;
    transcript: string;
    audioEnergy: number;
    emotion: string;
    emotionScore: number;
    duration: string;
    fileSize: string;
    timestamp: string;
  };
  view?: "grid" | "list" | "compact";
  rawClipData?: Clip; // Pass the full API clip data for video player
}

const getScoreColor = (score: number) => {
  if (score >= 0.7) return "text-score-green";
  if (score >= 0.5) return "text-yellow-500";
  if (score >= 0.3) return "text-score-blue";
  return "text-score-gray";
};

const getScoreBg = (score: number) => {
  if (score >= 0.7) return "bg-score-green/10";
  if (score >= 0.5) return "bg-yellow-500/10";
  if (score >= 0.3) return "bg-score-blue/10";
  return "bg-score-gray/10";
};

const getStarCount = (score: number) => {
  if (score >= 0.7) return 5;
  if (score >= 0.5) return 4;
  if (score >= 0.3) return 3;
  return 2;
};

const emotionEmojis: Record<string, string> = {
  joy: "😊",
  surprise: "😮",
  excitement: "🔥",
  neutral: "😐"
};

export const ClipCard = ({ clip, view = "grid", rawClipData }: ClipCardProps) => {
  const clampedScore = clampScore(clip.score);
  const stars = getStarCount(clampedScore);
  const { openPlayer } = useVideoPlayer();

  const handlePlayClick = () => {
    if (rawClipData) {
      openPlayer(rawClipData);
    } else {
      console.warn("No raw clip data available for playback");
    }
  };

  return (
    <Card className={cn(
      "group bg-card border-border overflow-hidden transition-all duration-300",
      "hover:shadow-2xl hover:shadow-primary/30 hover:border-primary/50",
      "hover:scale-[1.02]",
      view === "list" && "flex gap-4"
    )}>
      {/* Thumbnail */}
      <div className={cn(
        "relative overflow-hidden",
        view === "compact" ? "aspect-video" : "aspect-video"
      )}>
        {/* Gradient Placeholder */}
        <div className="w-full h-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center transition-all duration-500 group-hover:scale-110">
          <div className="text-center text-white">
            <div className="text-2xl font-bold">{clip.channel.slice(0, 2).toUpperCase()}</div>
            <div className="text-sm opacity-75">{clip.channel}</div>
          </div>
        </div>
        
        {/* Gradient Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent transition-opacity duration-300 group-hover:from-black/60" />
        
        {/* Play Button Overlay with scale animation */}
        <button
          onClick={handlePlayClick}
          className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300 bg-black/40"
        >
          <div className="w-16 h-16 rounded-full bg-primary flex items-center justify-center transform scale-75 group-hover:scale-100 transition-transform duration-300 shadow-lg shadow-primary/50">
            <Play className="w-8 h-8 text-white fill-white ml-1" />
          </div>
        </button>

        {/* Channel Avatar */}
        <Avatar className="absolute bottom-3 left-3 w-8 h-8 border-2 border-background group-hover:scale-110 transition-transform duration-300">
          <AvatarImage src={clip.avatar} alt={clip.channel} />
          <AvatarFallback>{clip.channel[0]}</AvatarFallback>
        </Avatar>

        {/* Score Badge with glow */}
        <div className="absolute top-3 right-3">
          <Badge className={cn(
            "font-bold text-base px-3 py-1 shadow-lg transition-all duration-300",
            getScoreColor(clampedScore),
            getScoreBg(clampedScore),
            clampedScore >= 0.7 && "group-hover:shadow-score-green/50",
            clampedScore >= 0.5 && clampedScore < 0.7 && "group-hover:shadow-yellow-500/50",
            clampedScore >= 0.3 && clampedScore < 0.5 && "group-hover:shadow-score-blue/50"
          )}>
            {clampedScore.toFixed(2)}
          </Badge>
          <div className="flex gap-0.5 mt-1 justify-end">
            {[...Array(5)].map((_, i) => (
              <Star
                key={i}
                className={cn(
                  "w-3 h-3 transition-all duration-300",
                  i < stars 
                    ? `fill-current ${getScoreColor(clampedScore)} group-hover:scale-110` 
                    : 'text-muted'
                )}
              />
            ))}
          </div>
        </div>

        {/* Action Buttons - Slide up from bottom */}
        <div className="absolute bottom-0 left-0 right-0 p-4 flex items-center justify-center gap-2 transform translate-y-full group-hover:translate-y-0 transition-transform duration-300 bg-gradient-to-t from-black/90 to-transparent">
          <Button 
            size="sm" 
            className="bg-primary/90 hover:bg-primary backdrop-blur-sm shadow-lg"
            onClick={handlePlayClick}
          >
            <Play className="w-4 h-4 mr-1" />
            Play
          </Button>
          <Button 
            size="sm" 
            variant="outline"
            className="border-white/20 hover:bg-white/10 backdrop-blur-sm"
          >
            <Download className="w-4 h-4" />
          </Button>
          <Button 
            size="sm" 
            variant="outline"
            className="border-white/20 hover:bg-white/10 backdrop-blur-sm"
          >
            <Share2 className="w-4 h-4" />
          </Button>
          <Button 
            size="sm" 
            variant="outline"
            className="border-white/20 hover:bg-destructive/20 hover:text-destructive backdrop-blur-sm"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className={cn("p-4 space-y-3", view === "list" && "flex-1")}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-bold text-foreground">{clip.channel}</span>
            <Badge variant="outline" className="text-xs text-info border-info/20">
              {clip.category}
            </Badge>
          </div>
        </div>

        <p className="text-sm text-muted-foreground line-clamp-3 leading-relaxed">
          "{clip.transcript}"
        </p>

        {/* Metadata */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">🎧 Audio:</span>
            <div className="flex-1 bg-muted rounded-full h-1.5">
              <div 
                className="h-full bg-success rounded-full transition-all duration-300 group-hover:bg-gradient-to-r group-hover:from-success group-hover:to-emerald-400"
                style={{ width: `${clip.audioEnergy * 100}%` }}
              />
            </div>
          </div>
          <div className="text-muted-foreground">
            {emotionEmojis[clip.emotion]} {clip.emotion} ({clip.emotionScore.toFixed(2)})
          </div>
          <div className="text-muted-foreground">⏱️ {clip.duration}</div>
          <div className="text-muted-foreground">💾 {clip.fileSize}</div>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-border">
          <span className="text-xs text-muted-foreground">{clip.timestamp}</span>
        </div>
      </div>
    </Card>
  );
};

