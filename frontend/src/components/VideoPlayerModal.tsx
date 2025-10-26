import { useEffect, useRef, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { VisuallyHidden } from "@radix-ui/react-visually-hidden";
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
  X,
  AlertCircle
} from "lucide-react";
import { AIScoreDisplay } from "@/components/AIScoreDisplay";
import { cn } from "@/lib/utils";
import { getChannelAvatarProps } from "@/lib/avatarUtils";
import { Clip, ScoreBreakdown } from "@/hooks/useClips";

interface VideoPlayerModalProps {
  clipId: string | null;
  onClose: () => void;
  onNext?: () => void;
  onPrevious?: () => void;
  clipData?: Clip;
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
  const [videoError, setVideoError] = useState(false);

  useEffect(() => {
    if (clipId && videoRef.current) {
      setVideoError(false);
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

  if (!clipId || !clipData) {
    console.log("VideoPlayerModal: No clip data", { clipId, clipData });
    return null;
  }

  console.log("VideoPlayerModal: Rendering with clip", { 
    id: clipData.id, 
    channel: clipData.channel_name,
    hasStorageUrl: !!clipData.storage_url,
    storageUrl: clipData.storage_url 
  });

  const stars = clipData.confidence_score ? getStarCount(clipData.confidence_score) : 0;
  const { gradient, initials } = getChannelAvatarProps(clipData.channel_name);

  return (
    <Dialog open={!!clipId} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-6xl w-[85vw] h-[70vh] p-0 gap-0 bg-background/95 backdrop-blur-xl border-white/10">
        {/* Accessibility: Hidden title and description for screen readers */}
        <VisuallyHidden>
          <DialogTitle>Clip from {clipData?.channel_name}</DialogTitle>
          <DialogDescription>
            Video clip player showing content from {clipData?.channel_name}
          </DialogDescription>
        </VisuallyHidden>
        
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-50 p-2 rounded-full bg-black/50 hover:bg-black/70 text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex h-full">
          {/* Video Player Section */}
          <div className="flex-1 bg-black relative">
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
            {videoError ? (
              <div className="w-full h-full min-h-[40vh] flex flex-col items-center justify-center text-white space-y-4">
                <AlertCircle className="w-16 h-16 text-red-500" />
                <div className="text-center space-y-2">
                  <p className="text-lg font-semibold">Unable to load video</p>
                  <p className="text-sm text-gray-400">The video file may be unavailable or corrupted</p>
                  {clipData.storage_url && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => window.open(clipData.storage_url, '_blank')}
                      className="mt-4"
                    >
                      Try opening in new tab
                    </Button>
                  )}
                </div>
              </div>
            ) : (
              <video
                ref={videoRef}
                src={clipData.storage_url}
                controls
                loop
                className="w-full h-full max-h-[50vh] object-contain"
                onError={(e) => {
                  console.error("Video load error:", e);
                  setVideoError(true);
                }}
              >
                Your browser does not support video playback.
              </video>
            )}

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
          <div className="w-72 p-3 space-y-2 bg-card/50 backdrop-blur overflow-y-auto flex-shrink-0">
            {/* Channel Info */}
            <div>
              <div className="flex items-center gap-2 mb-1">
                <div className={`w-8 h-8 rounded-full bg-gradient-to-br ${gradient} flex items-center justify-center text-white font-bold text-xs ring-2 ring-primary/20`}>
                  {initials}
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-sm leading-tight">{clipData.channel_name}</h3>
                  <p className="text-[10px] text-muted-foreground">
                    {new Date(clipData.created_at).toLocaleString()}
                  </p>
                </div>
              </div>

              {/* Score Display */}
              <div className="flex items-center gap-2 mb-1">
                {clipData.confidence_score && (
                  <Badge className={cn("text-xs font-bold px-2 py-0.5", getScoreColor(clipData.confidence_score))}>
                    {clipData.confidence_score.toFixed(2)}
                  </Badge>
                )}
                <div className="flex gap-0.5">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      className={cn(
                        "w-2.5 h-2.5",
                        i < stars 
                          ? `fill-current ${clipData.confidence_score ? getScoreColor(clipData.confidence_score) : 'text-primary'}` 
                          : 'text-muted'
                      )}
                    />
                  ))}
                </div>
              </div>

              {/* AI Score Breakdown */}
              {clipData.confidence_score && clipData.score_breakdown && (
                <div className="space-y-1.5">
                  <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wide border-b border-border pb-0.5">
                    Score Breakdown
                  </div>
                  <AIScoreDisplay
                    score={clipData.confidence_score}
                    breakdown={{
                      audioEnergy: clipData.score_breakdown.energy,
                      pitchVariance: clipData.score_breakdown.pitch,
                      emotionScore: clipData.score_breakdown.emotion,
                      keywordBoost: clipData.score_breakdown.keyword
                    }}
                    size="sm"
                    showBreakdown={true}
                  />
                  <div className="text-[10px] text-muted-foreground italic p-1.5 bg-muted/30 rounded border border-border">
                    <p className="font-semibold mb-0.5 text-[9px]">Formula:</p>
                    <p className="font-mono text-[9px] leading-tight">
                      (0.35×E) + (0.25×P) + (0.40×Em) + KB
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Transcript */}
            <div>
              <h4 className="text-xs font-semibold mb-0.5 text-muted-foreground">Transcript</h4>
              <div className="bg-muted/50 rounded p-1.5 max-h-20 overflow-y-auto">
                <p className="text-xs leading-snug">
                  {clipData.transcript || "No transcript available"}
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="space-y-1.5 pt-1.5 border-t border-border">
              <Button
                onClick={handleDownload}
                size="sm"
                className="w-full bg-primary hover:bg-primary/90 h-7 text-xs"
              >
                <Download className="w-3 h-3 mr-1.5" />
                Download
              </Button>
              <Button
                onClick={handleShare}
                variant="outline"
                size="sm"
                className="w-full h-7 text-xs"
              >
                <Share2 className="w-3 h-3 mr-1.5" />
                Share
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="w-full text-destructive hover:text-destructive hover:bg-destructive/10 h-7 text-xs"
              >
                <Trash2 className="w-3 h-3 mr-1.5" />
                Delete
              </Button>
            </div>

            {/* Clip Info */}
            <div className="text-[10px] text-muted-foreground space-y-0.5 pt-1.5 border-t border-border">
              <p>ID: <span className="font-mono">{clipData.id.slice(0, 12)}...</span></p>
              <p>Duration: ~30s</p>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

