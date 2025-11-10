import { useEffect, useRef, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { VisuallyHidden } from "@radix-ui/react-visually-hidden";
import { motion, AnimatePresence } from "framer-motion";
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
import { cn, clampScore } from "@/lib/utils";
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

  const clampedScore = clampScore(clipData?.confidence_score);
  const stars = clampedScore > 0 ? getStarCount(clampedScore) : 0;
  const { gradient, initials } = clipData ? getChannelAvatarProps(clipData.channel_name) : { gradient: 'from-purple-500 to-blue-500', initials: 'NA' };

  return (
    <AnimatePresence>
      <Dialog open={!!clipId && !!clipData} onOpenChange={(open) => !open && onClose()}>
        {clipData && (
          <DialogContent 
            className="max-w-[95vw] w-[1400px] h-[100vh] p-0 gap-0 bg-background border-primary/20 shadow-2xl shadow-black/50 overflow-hidden rounded-xl"
            style={{
              position: 'fixed',
              left: '50%',
              top: '50%',
              transform: 'translate(-50%, -50%)',
              zIndex: 50
            }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 20 }}
              transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
              className="flex h-full gap-6"
            >
              {/* Accessibility: Hidden title and description for screen readers */}
              <VisuallyHidden>
                <DialogTitle>Clip from {clipData.channel_name}</DialogTitle>
                <DialogDescription>
                  Video clip player showing content from {clipData.channel_name}
                </DialogDescription>
              </VisuallyHidden>
          {/* Video Player Section - Better sizing */}
          <div className="flex-1 bg-black relative flex items-center justify-center min-w-0">
            {/* Navigation Arrows */}
            {onPrevious && (
              <button
                onClick={onPrevious}
                className="absolute left-6 top-1/2 -translate-y-1/2 z-10 p-4 rounded-full bg-black/60 hover:bg-black/80 text-white transition-all hover:scale-110 shadow-lg"
              >
                <ChevronLeft className="w-6 h-6" />
              </button>
            )}
            {onNext && (
              <button
                onClick={onNext}
                className="absolute right-6 top-1/2 -translate-y-1/2 z-10 p-4 rounded-full bg-black/60 hover:bg-black/80 text-white transition-all hover:scale-110 shadow-lg"
              >
                <ChevronRight className="w-6 h-6" />
              </button>
            )}

            {/* Video Element - Better sizing */}
            {videoError ? (
              <div className="w-full h-full flex flex-col items-center justify-center text-white space-y-4">
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
                className="w-full h-full object-cover"
                onError={(e) => {
                  console.error("Video load error:", e);
                  setVideoError(true);
                }}
              >
                Your browser does not support video playback.
              </video>
            )}

            {/* Overlay Controls */}
            <div className="absolute bottom-6 right-6 flex gap-2">
              <Button
                size="sm"
                variant="outline"
                className="bg-black/60 border-white/20 hover:bg-black/80 text-white backdrop-blur"
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
                className="bg-black/60 border-white/20 hover:bg-black/80 text-white backdrop-blur"
                onClick={handleFullscreen}
              >
                <Maximize className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Metadata Sidebar - Better sizing */}
          <div className="w-[380px] p-6 space-y-4 bg-card/95 backdrop-blur-xl overflow-y-auto flex-shrink-0 border-l border-border/50 h-full">
            {/* Channel Info */}
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${gradient} flex items-center justify-center text-white font-bold text-sm ring-2 ring-primary/20`}>
                  {initials}
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-base leading-tight">{clipData.channel_name}</h3>
                  <p className="text-xs text-muted-foreground">
                    {new Date(clipData.created_at).toLocaleString()}
                  </p>
                </div>
              </div>

              {/* Score Display */}
              <div className="flex items-center gap-2 mb-2">
                {clampedScore > 0 && (
                  <Badge className={cn("text-sm font-bold px-3 py-1", getScoreColor(clampedScore))}>
                    {clampedScore.toFixed(2)}
                  </Badge>
                )}
                <div className="flex gap-0.5">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      className={cn(
                        "w-3 h-3",
                        i < stars 
                          ? `fill-current ${clampedScore > 0 ? getScoreColor(clampedScore) : 'text-primary'}` 
                          : 'text-muted'
                      )}
                    />
                  ))}
                </div>
              </div>

              {/* AI Score Breakdown */}
              {clampedScore > 0 && clipData.score_breakdown && (
                <div className="space-y-2">
                  <div className="text-xs font-bold text-muted-foreground uppercase tracking-wide border-b border-border pb-1">
                    Score Breakdown
                  </div>
                  <AIScoreDisplay
                    score={clampedScore}
                    breakdown={{
                      audioEnergy: clipData.score_breakdown.energy,
                      pitchVariance: clipData.score_breakdown.pitch,
                      emotionScore: clipData.score_breakdown.emotion,
                      keywordBoost: clipData.score_breakdown.keyword
                    }}
                    size="sm"
                    showBreakdown={true}
                  />
                </div>
              )}
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
            <div className="space-y-2 pt-2 border-t border-border">
              <Button
                onClick={handleDownload}
                size="sm"
                className="w-full bg-primary hover:bg-primary/90 h-9"
              >
                <Download className="w-4 h-4 mr-2" />
                Download
              </Button>
              <Button
                onClick={handleShare}
                variant="outline"
                size="sm"
                className="w-full h-9"
              >
                <Share2 className="w-4 h-4 mr-2" />
                Share
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="w-full text-destructive hover:text-destructive hover:bg-destructive/10 h-9"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete
              </Button>
            </div>

            {/* Clip Info */}
            <div className="text-xs text-muted-foreground space-y-1 pt-2 border-t border-border">
              <p>ID: <span className="font-mono">{clipData.id.slice(0, 12)}...</span></p>
              <p>Duration: ~30s</p>
            </div>
          </div>
            </motion.div>
          </DialogContent>
        )}
      </Dialog>
    </AnimatePresence>
  );
}

