import { useEffect, useRef, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { 
  Download, 
  Share2, 
  Trash2, 
  ChevronLeft, 
  ChevronRight,
  Volume2,
  VolumeX,
  Maximize,
  Star,
  X
} from "lucide-react";
import { AIScoreDisplay } from "@/components/AIScoreDisplay";
import { cn } from "@/lib/utils";

interface VideoPlayerModalProps {
  clipId: string | null;
  onClose: () => void;
  onNext?: () => void;
  onPrevious?: () => void;
  clipData?: {
    id: string;
    channel_name: string;
    confidence_score: number;
    transcript: string;
    created_at: string;
    storage_url?: string;
  };
}

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

export function VideoPlayerModal({ 
  clipId, 
  onClose, 
  onNext, 
  onPrevious,
  clipData 
}: VideoPlayerModalProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    if (clipId && videoRef.current) {
      // Auto-play when clip loads
      videoRef.current.play().catch(err => {
        console.log("Autoplay prevented:", err);
      });
    }
  }, [clipId]);

  const handleFullscreen = () => {
    if (videoRef.current) {
      if (!document.fullscreenElement) {
        videoRef.current.requestFullscreen();
        setIsFullscreen(true);
      } else {
        document.exitFullscreen();
        setIsFullscreen(false);
      }
    }
  };

  const handleDownload = () => {
    if (clipData?.storage_url) {
      window.open(clipData.storage_url, '_blank');
    }
  };

  const handleShare = async () => {
    const shareUrl = `${window.location.origin}/clips/${clipId}`;
    
    if (navigator.share) {
      try {
        await navigator.share({
          title: `Clip from ${clipData?.channel_name}`,
          text: clipData?.transcript.slice(0, 100),
          url: shareUrl,
        });
      } catch (err) {
        console.log("Share cancelled");
      }
    } else {
      // Fallback: copy to clipboard
      navigator.clipboard.writeText(shareUrl);
      // TODO: Show toast notification
      console.log("Link copied to clipboard!");
    }
  };

  if (!clipId || !clipData) return null;

  const stars = getStarCount(clipData.confidence_score);
  const avatar = `https://api.dicebear.com/7.x/avataaars/svg?seed=${clipData.channel_name}`;

  return (
    <Dialog open={!!clipId} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-6xl p-0 gap-0 bg-background/95 backdrop-blur-xl border-white/10">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-50 p-2 rounded-full bg-black/50 hover:bg-black/70 text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-0">
          {/* Video Player Section */}
          <div className="lg:col-span-2 bg-black relative">
            {/* Navigation Arrows */}
            {onPrevious && (
              <button
                onClick={onPrevious}
                className="absolute left-4 top-1/2 -translate-y-1/2 z-10 p-3 rounded-full bg-black/50 hover:bg-black/70 text-white transition-all hover:scale-110"
              >
                <ChevronLeft className="w-6 h-6" />
              </button>
            )}
            {onNext && (
              <button
                onClick={onNext}
                className="absolute right-4 top-1/2 -translate-y-1/2 z-10 p-3 rounded-full bg-black/50 hover:bg-black/70 text-white transition-all hover:scale-110"
              >
                <ChevronRight className="w-6 h-6" />
              </button>
            )}

            {/* Video Element */}
            <video
              ref={videoRef}
              src={clipData.storage_url}
              controls
              loop
              className="w-full h-full max-h-[70vh] object-contain"
              onError={(e) => console.error("Video load error:", e)}
            >
              Your browser does not support video playback.
            </video>

            {/* Overlay Controls */}
            <div className="absolute bottom-4 right-4 flex gap-2">
              <Button
                size="sm"
                variant="outline"
                className="bg-black/50 border-white/20 hover:bg-black/70 text-white backdrop-blur"
                onClick={() => {
                  if (videoRef.current) {
                    videoRef.current.muted = !videoRef.current.muted;
                    setIsMuted(!isMuted);
                  }
                }}
              >
                {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="bg-black/50 border-white/20 hover:bg-black/70 text-white backdrop-blur"
                onClick={handleFullscreen}
              >
                <Maximize className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Metadata Sidebar */}
          <div className="p-6 space-y-6 bg-card/50 backdrop-blur">
            {/* Channel Info */}
            <div>
              <div className="flex items-center gap-3 mb-4">
                <Avatar className="w-12 h-12 ring-2 ring-primary/20">
                  <AvatarImage src={avatar} alt={clipData.channel_name} />
                  <AvatarFallback>{clipData.channel_name[0]?.toUpperCase()}</AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <h3 className="font-bold text-lg">{clipData.channel_name}</h3>
                  <p className="text-xs text-muted-foreground">
                    {new Date(clipData.created_at).toLocaleString()}
                  </p>
                </div>
              </div>

              {/* Score Display */}
              <div className="flex items-center gap-2 mb-3">
                <Badge className={cn("text-lg font-bold px-3 py-1", getScoreColor(clipData.confidence_score))}>
                  {clipData.confidence_score.toFixed(2)}
                </Badge>
                <div className="flex gap-0.5">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      className={cn(
                        "w-4 h-4",
                        i < stars 
                          ? `fill-current ${getScoreColor(clipData.confidence_score)}` 
                          : 'text-muted'
                      )}
                    />
                  ))}
                </div>
              </div>

              {/* AI Score Breakdown */}
              <AIScoreDisplay
                score={clipData.confidence_score}
                breakdown={{
                  audioEnergy: 0.75,
                  pitchVariance: 0.60,
                  emotionScore: 0.80,
                  keywordBoost: 0.50
                }}
                size="sm"
                showBreakdown={true}
              />
            </div>

            {/* Transcript */}
            <div>
              <h4 className="text-sm font-semibold mb-2 text-muted-foreground">Transcript</h4>
              <div className="bg-muted/50 rounded-lg p-3 max-h-32 overflow-y-auto">
                <p className="text-sm leading-relaxed">
                  {clipData.transcript || "No transcript available"}
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="space-y-2 pt-4 border-t border-border">
              <Button
                onClick={handleDownload}
                className="w-full bg-primary hover:bg-primary/90"
              >
                <Download className="w-4 h-4 mr-2" />
                Download Clip
              </Button>
              <Button
                onClick={handleShare}
                variant="outline"
                className="w-full"
              >
                <Share2 className="w-4 h-4 mr-2" />
                Share
              </Button>
              <Button
                variant="outline"
                className="w-full text-destructive hover:text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete
              </Button>
            </div>

            {/* Clip Info */}
            <div className="text-xs text-muted-foreground space-y-1 pt-4 border-t border-border">
              <p>Clip ID: <span className="font-mono">{clipData.id.slice(0, 20)}...</span></p>
              <p>Duration: ~30 seconds</p>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

