import { StatsGrid } from "@/components/dashboard/StatsGrid";
import { LiveMonitors } from "@/components/dashboard/LiveMonitors";
import { RecentClips } from "@/components/dashboard/RecentClips";
import { ActivityFeed } from "@/components/dashboard/ActivityFeed";
import { Card } from "@/components/ui/card";
import { LoadingIndicator } from "@/components/LoadingIndicator";
import { useStreams, useDashboardStats } from "@/hooks/useStreamData";
import { useClips } from "@/hooks/useClips";
import { useVideoPlayer } from "@/contexts/VideoPlayerContext";
import { useIsMobile } from "@/hooks/use-mobile";
import { clampScore } from "@/lib/utils";

const Dashboard = () => {
  const { isFetching: streamsFetching } = useStreams();
  const { isFetching: statsFetching } = useDashboardStats();
  const { data: clipsData } = useClips({ limit: 50 }); // Fetch all clips to find highest score
  const { openPlayer } = useVideoPlayer();
  const isUpdating = streamsFetching || statsFetching;
  const isMobile = useIsMobile();

  // Extract clips array from paginated response
  const clips = clipsData?.clips || [];

  // Find the highest scoring clip
  const featuredClip = clips.length > 0
    ? clips.reduce((highest, current) => 
        clampScore(current.confidence_score) > clampScore(highest.confidence_score) ? current : highest
      )
    : null;

  return (
    <div className="min-h-screen bg-background">
      <LoadingIndicator isLoading={isUpdating} />
      
      <div className="container mx-auto px-4 md:px-6 py-6 md:py-8 space-y-8 md:space-y-12">
        {/* Page Header */}
        <div className="animate-fade-in">
          <h1 className="text-3xl md:text-4xl font-bold mb-2 gradient-text">
            🎬 Live Monitoring Dashboard
          </h1>
          <p className="text-muted-foreground">
            AI is watching your streams and auto-saving the best moments
          </p>
        </div>

        <StatsGrid />
        
        <LiveMonitors />
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 md:gap-8">
          <div className="lg:col-span-2">
            <RecentClips />
          </div>
          <div>
            <ActivityFeed />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
