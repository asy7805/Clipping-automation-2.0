import { Play, Star } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useVideoPlayer } from "@/contexts/VideoPlayerContext";
import { Clip } from "@/hooks/useClips";

interface NetflixClipCardProps {
  clip: Clip;
  view?: "grid" | "list";
}

const getScoreColor = (score: number) => {
  if (score >= 0.7) return "text-yellow-400";
  if (score >= 0.5) return "text-green-400";
  if (score >= 0.3) return "text-blue-400";
  return "text-gray-400";
};

const getScoreBg = (score: number) => {
  if (score >= 0.7) return "bg-yellow-400/10 border-yellow-400/30";
  if (score >= 0.5) return "bg-green-400/10 border-green-400/30";
  if (score >= 0.3) return "bg-blue-400/10 border-blue-400/30";
  return "bg-gray-400/10 border-gray-400/30";
};

const getStarCount = (score: number) => {
  if (score >= 0.7) return 5;
  if (score >= 0.5) return 4;
  if (score >= 0.3) return 3;
  return 2;
};

const getTimeAgo = (dateString: string) => {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
};

export const NetflixClipCard = ({ clip, view = "grid" }: NetflixClipCardProps) => {
  const { openPlayer } = useVideoPlayer();
  const stars = getStarCount(clip.confidence_score);
  
  // Use real thumbnail from video first frame, fallback to placeholder
  const imagePool = [
    'photo-1542751371-adc38448a05e', 'photo-1511512578047-dfb367046420',
    'photo-1538481199705-c710c4e965fc', 'photo-1552820728-8b83bb6b773f',
    'photo-1560419015-7c427e8ae5ba', 'photo-1614294148960-9aa740632a87',
    'photo-1616990781764-c7b5048d6c29', 'photo-1589241062272-c0a000072dfa'
  ];
  const imageIndex = Math.abs(clip.id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)) % imagePool.length;
  const fallbackImage = `https://images.unsplash.com/${imagePool[imageIndex]}?w=400&h=225&fit=crop`;
  
  // Prefer real thumbnail, fallback to placeholder
  const thumbnail = clip.thumbnail_url || clip.thumbnail || fallbackImage;

  return (
    <div 
      className="group cursor-pointer w-full"
      onClick={() => openPlayer(clip)}
    >
      {/* Thumbnail Container */}
      <div className="relative aspect-video bg-muted rounded-md overflow-hidden mb-2">
        <img 
          src={thumbnail} 
          alt={clip.channel_name}
          className="w-full h-full object-cover transition-all duration-300 group-hover:scale-110"
        />
        
        {/* Dark overlay on hover */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all duration-300" />
        
        {/* Simple centered play button on hover */}
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <div className="w-14 h-14 rounded-full bg-white/90 flex items-center justify-center shadow-2xl transform scale-90 group-hover:scale-100 transition-transform">
            <Play className="w-6 h-6 text-black fill-black ml-0.5" />
          </div>
        </div>

        {/* Duration badge (bottom right) */}
        <div className="absolute bottom-2 right-2 px-2 py-0.5 bg-black/80 rounded text-xs font-medium text-white">
          ~30s
        </div>
      </div>

      {/* Info Below Thumbnail (Netflix style) */}
      <div className="space-y-1.5">
        {/* Channel Name */}
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium text-sm text-foreground truncate group-hover:text-primary transition-colors">
            {clip.channel_name}
          </span>
          <Badge className={cn("text-xs font-bold px-1.5 py-0 border shrink-0", getScoreBg(clip.confidence_score), getScoreColor(clip.confidence_score))}>
            {clip.confidence_score.toFixed(2)}
          </Badge>
        </div>

        {/* Stars and Time */}
        <div className="flex items-center justify-between">
          <div className="flex gap-0.5">
            {[...Array(5)].map((_, i) => (
              <Star
                key={i}
                className={cn(
                  "w-2.5 h-2.5",
                  i < stars 
                    ? `fill-current ${getScoreColor(clip.confidence_score)}` 
                    : 'text-muted-foreground/30'
                )}
              />
            ))}
          </div>
          <span className="text-xs text-muted-foreground">
            {getTimeAgo(clip.created_at)}
          </span>
        </div>
      </div>
    </div>
  );
};

