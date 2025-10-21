import { ArrowRight, Play, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Star } from "lucide-react";
import { useClips } from "@/hooks/useClips";
import { Link } from "react-router-dom";
import { useVideoPlayer } from "@/contexts/VideoPlayerContext";

const getScoreColor = (score: number) => {
  if (score >= 0.7) return "text-score-gold";
  if (score >= 0.5) return "text-score-green";
  if (score >= 0.3) return "text-score-blue";
  return "text-score-gray";
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

export const RecentClips = () => {
  const { data: clips, isLoading, error } = useClips({ limit: 6 });
  const { openPlayer } = useVideoPlayer();
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">📹 Recent Clips</h2>
        <Link to="/dashboard/clips">
          <Button variant="ghost" className="text-primary hover:text-primary/90">
            View All <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </Link>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : error ? (
        <div className="flex items-center justify-center h-40">
          <p className="text-destructive">Failed to load clips. Please try again.</p>
        </div>
      ) : !clips || clips.length === 0 ? (
        <div className="flex items-center justify-center h-40">
          <p className="text-muted-foreground">No clips found. Start monitoring streams to capture clips!</p>
        </div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-thin">
          {clips.map((clip) => {
            const score = clip.confidence_score;
            const stars = getStarCount(score);
            const thumbnail = clip.thumbnail || `https://images.unsplash.com/photo-1542751371-adc38448a05e?w=400&h=225&fit=crop&sig=${clip.id}`;
            const avatar = `https://api.dicebear.com/7.x/avataaars/svg?seed=${clip.channel_name}`;
            
            return (
              <Card 
                key={clip.id} 
                className="min-w-[280px] bg-card border-border hover:shadow-lg hover:scale-105 transition-all cursor-pointer group"
                onClick={() => openPlayer(clip)}
              >
                <div className="relative">
                  <img 
                    src={thumbnail} 
                    alt={clip.channel_name}
                    className="w-full h-[158px] object-cover rounded-t-lg"
                  />
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center rounded-t-lg">
                    <Play className="w-12 h-12 text-white" />
                  </div>
                  <Badge className={`absolute top-2 right-2 ${getScoreColor(score)} bg-card/90 font-bold`}>
                    {score.toFixed(2)}
                  </Badge>
                  <div className="absolute top-2 right-2 mt-6 flex gap-0.5">
                    {[...Array(5)].map((_, i) => (
                      <Star
                        key={i}
                        className={`w-3 h-3 ${
                          i < stars 
                            ? `fill-current ${getScoreColor(score)}` 
                            : 'text-muted'
                        }`}
                      />
                    ))}
                  </div>
                </div>
                <div className="p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Avatar className="w-6 h-6">
                      <AvatarImage src={avatar} alt={clip.channel_name} />
                      <AvatarFallback>{clip.channel_name[0]?.toUpperCase()}</AvatarFallback>
                    </Avatar>
                    <span className="text-sm font-semibold text-foreground">{clip.channel_name}</span>
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-1 mb-2">
                    "{clip.transcript.slice(0, 50)}{clip.transcript.length > 50 ? '...' : ''}"
                  </p>
                  <p className="text-xs text-muted-foreground">{getTimeAgo(clip.created_at)}</p>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};
