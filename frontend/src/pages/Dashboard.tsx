import { StatsGrid } from "@/components/dashboard/StatsGrid";
import { LiveMonitors } from "@/components/dashboard/LiveMonitors";
import { RecentClips } from "@/components/dashboard/RecentClips";
import { ActivityFeed } from "@/components/dashboard/ActivityFeed";
import { Card } from "@/components/ui/card";
import { AIScoreDisplay } from "@/components/AIScoreDisplay";
import { LoadingIndicator } from "@/components/LoadingIndicator";
import { useStreams, useDashboardStats } from "@/hooks/useStreamData";
import { useClips } from "@/hooks/useClips";
import { useVideoPlayer } from "@/contexts/VideoPlayerContext";
import { useIsMobile } from "@/hooks/use-mobile";

const Dashboard = () => {
  const { isFetching: streamsFetching } = useStreams();
  const { isFetching: statsFetching } = useDashboardStats();
  const { data: clips } = useClips({ limit: 50 }); // Fetch all clips to find highest score
  const { openPlayer } = useVideoPlayer();
  const isUpdating = streamsFetching || statsFetching;
  const isMobile = useIsMobile();

  // Find the highest scoring clip
  const featuredClip = clips && clips.length > 0
    ? clips.reduce((highest, current) => 
        current.confidence_score > highest.confidence_score ? current : highest
      )
    : null;

  return (
    <div className="min-h-screen bg-background">
      <LoadingIndicator isLoading={isUpdating} />
      
      <div className="container mx-auto px-4 md:px-6 py-6 md:py-8 space-y-6 md:space-y-8">
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
        
        {/* Featured High Score Clip */}
        {featuredClip && (
          <Card className="p-4 md:p-6 glass-strong border-white/10 card-hover overflow-hidden relative">
            {/* Glow effect */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-primary/10 rounded-full blur-3xl -z-10" />
            
            <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-2">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center shadow-lg animate-pulse-glow">
                  <span className="text-2xl">⭐</span>
                </div>
                <div>
                  <h2 className="text-xl md:text-2xl font-bold">Top Scoring Clip</h2>
                  <p className="text-sm text-muted-foreground">
                    {featuredClip.channel_name} • {new Date(featuredClip.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold gradient-text">{featuredClip.confidence_score.toFixed(2)}</div>
                <div className="text-xs text-muted-foreground">
                  {featuredClip.confidence_score >= 0.7 ? 'Exceptional' : featuredClip.confidence_score >= 0.5 ? 'Great' : 'Good'}
                </div>
              </div>
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8">
              <div className="w-full relative group cursor-pointer" onClick={() => openPlayer(featuredClip)}>
                <div className="absolute inset-0 bg-gradient-to-r from-primary/20 to-accent/20 rounded-xl blur-xl group-hover:blur-2xl transition-all" />
                <img 
                  src={`https://images.unsplash.com/photo-1542751371-adc38448a05e?w=600&h=400&fit=crop&sig=${featuredClip.id}`}
                  alt="Featured clip"
                  className="relative w-full rounded-xl object-cover aspect-video border border-white/10 shadow-2xl"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-background/80 via-transparent to-transparent rounded-xl" />
                <button className="absolute inset-0 flex items-center justify-center group-hover:bg-black/20 transition-all rounded-xl">
                  <div className="w-16 h-16 bg-primary/90 backdrop-blur rounded-full flex items-center justify-center transform group-hover:scale-110 transition-transform shadow-lg shadow-primary/50">
                    <svg className="w-8 h-8 text-white ml-1" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z"/>
                    </svg>
                  </div>
                </button>
              </div>
              <AIScoreDisplay 
                score={featuredClip.confidence_score}
                breakdown={{
                  audioEnergy: 0.88,
                  pitchVariance: 0.72,
                  emotionScore: 0.85,
                  keywordBoost: 0.68
                }}
                size={isMobile ? "md" : "lg"}
                showBreakdown={true}
              />
            </div>
          </Card>
        )}

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
