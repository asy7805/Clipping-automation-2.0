import { useState, useEffect, useRef, useCallback } from "react";
import { Search, Grid3x3, List, LayoutGrid, Calendar, ChevronDown, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ClipCard } from "@/components/clips/ClipCard";
import { useIsMobile } from "@/hooks/use-mobile";
import { useClips } from "@/hooks/useClips";
import { useSearchParams } from "react-router-dom";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const Clips = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlChannel = searchParams.get('channel');
  
  const [view, setView] = useState<"grid" | "list" | "compact">("grid");
  const [filters, setFilters] = useState<string[]>([]);
  const [channelFilter, setChannelFilter] = useState<string | undefined>(urlChannel || undefined);
  const [clipWorthyFilter, setClipWorthyFilter] = useState<boolean | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState("");
  const [isPulling, setIsPulling] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const isMobile = useIsMobile();
  const touchStartY = useRef(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Update filter when URL param changes
  useEffect(() => {
    if (urlChannel) {
      setChannelFilter(urlChannel);
    }
  }, [urlChannel]);

  // Fetch clips with filters
  const { data: clips, isLoading, error, refetch } = useClips({
    limit: 50,
    channel_name: channelFilter,
    is_clip_worthy: clipWorthyFilter,
  });

  // Filter by search query on client side
  const filteredClips = clips?.filter(clip => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      clip.transcript.toLowerCase().includes(query) ||
      clip.channel_name.toLowerCase().includes(query)
    );
  }) || [];

  // Pull to refresh for mobile
  const handleTouchStart = (e: React.TouchEvent) => {
    if (!isMobile) return;
    const scrollContainer = scrollContainerRef.current?.closest('main');
    if (scrollContainer && scrollContainer.scrollTop === 0) {
      touchStartY.current = e.touches[0].clientY;
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!isMobile || touchStartY.current === 0) return;
    
    const currentY = e.touches[0].clientY;
    const distance = currentY - touchStartY.current;
    
    if (distance > 0 && distance < 100) {
      setPullDistance(distance);
      setIsPulling(true);
    }
  };

  const handleTouchEnd = () => {
    if (!isMobile) return;
    
    if (pullDistance > 60) {
      // Trigger refresh
      refetch();
    }
    
    setIsPulling(false);
    setPullDistance(0);
    touchStartY.current = 0;
  };

  return (
    <div 
      ref={scrollContainerRef}
      className="container mx-auto px-4 md:px-6 py-8"
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Pull to refresh indicator */}
      {isMobile && isPulling && (
        <div 
          className="flex justify-center items-center text-primary transition-all duration-200"
          style={{ 
            height: `${pullDistance}px`,
            opacity: pullDistance / 60 
          }}
        >
          <div className="text-sm font-medium">
            {pullDistance > 60 ? '↻ Release to refresh' : '↓ Pull to refresh'}
          </div>
        </div>
      )}
      {/* Filter Bar */}
      <div className="sticky top-16 z-30 bg-background/95 backdrop-blur-sm pb-4 md:pb-6 space-y-4">
        <div className="flex items-center gap-2 md:gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 md:w-5 h-4 md:h-5 text-muted-foreground" />
            <Input 
              placeholder={isMobile ? "🔍 Search..." : "🔍 Search by transcript or channel..."}
              className="pl-10 md:pl-12 h-10 md:h-12 text-sm md:text-base"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          {!isMobile && (
            <div className="flex items-center gap-2">
              <Button
                variant={view === "grid" ? "default" : "outline"}
                size="icon"
                onClick={() => setView("grid")}
              >
                <Grid3x3 className="w-4 h-4" />
              </Button>
              <Button
                variant={view === "list" ? "default" : "outline"}
                size="icon"
                onClick={() => setView("list")}
              >
                <List className="w-4 h-4" />
              </Button>
              <Button
                variant={view === "compact" ? "default" : "outline"}
                size="icon"
                onClick={() => setView("compact")}
              >
                <LayoutGrid className="w-4 h-4" />
              </Button>
            </div>
          )}
        </div>

        {!isMobile && (
          <div className="flex items-center gap-3 flex-wrap">
            <Select>
              <SelectTrigger className="w-[180px]">
                <Calendar className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Last 7 days" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="24h">Last 24 hours</SelectItem>
                <SelectItem value="7d">Last 7 days</SelectItem>
                <SelectItem value="30d">Last 30 days</SelectItem>
                <SelectItem value="all">All time</SelectItem>
              </SelectContent>
            </Select>

            <Select>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Channels" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Channels</SelectItem>
                <SelectItem value="nater4l">nater4l</SelectItem>
                <SelectItem value="jordanbentley">jordanbentley</SelectItem>
              </SelectContent>
            </Select>

            <Select>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                <SelectItem value="irl">IRL</SelectItem>
                <SelectItem value="gaming">Gaming</SelectItem>
                <SelectItem value="chatting">Just Chatting</SelectItem>
              </SelectContent>
            </Select>

            <Select>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Sort by Newest" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="newest">Newest First</SelectItem>
                <SelectItem value="highest">Highest Score</SelectItem>
                <SelectItem value="longest">Longest Duration</SelectItem>
              </SelectContent>
            </Select>

            {filters.length > 0 && (
              <Button variant="ghost" size="sm" onClick={() => setFilters([])}>
                Clear All
              </Button>
            )}
          </div>
        )}

        {filters.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            {filters.map((filter) => (
              <Badge key={filter} variant="secondary" className="gap-1">
                {filter}
                <X className="w-3 h-3 cursor-pointer" />
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Clips Feed - Mobile vertical feed, Desktop grid */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center h-64 gap-3">
          <Loader2 className="w-12 h-12 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading clips...</p>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center h-64">
          <p className="text-destructive mb-4">Failed to load clips. Please try again.</p>
          <Button onClick={() => refetch()}>Retry</Button>
        </div>
      ) : filteredClips.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64">
          <p className="text-muted-foreground mb-2">No clips found</p>
          <p className="text-sm text-muted-foreground">
            {searchQuery ? "Try adjusting your search or filters" : "Start monitoring streams to capture clips!"}
          </p>
        </div>
      ) : (
        <>
          <div className={`grid gap-4 md:gap-6 ${
            isMobile 
              ? "grid-cols-1" 
              : view === "grid" 
                ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" 
                : view === "list" 
                  ? "grid-cols-1" 
                  : "grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6"
          }`}>
            {filteredClips.map((clip, index) => {
              // Transform clip data to match ClipCard expectations
              const transformedClip = {
                id: clip.id,
                thumbnail: clip.thumbnail || `https://images.unsplash.com/photo-1542751371-adc38448a05e?w=400&h=225&fit=crop&sig=${clip.id}`,
                score: clip.confidence_score,
                channel: clip.channel_name,
                avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${clip.channel_name}`,
                category: "Unknown",
                transcript: clip.transcript,
                audioEnergy: clip.audio_energy || 0,
                emotion: clip.emotion || "neutral",
                emotionScore: clip.emotion_score || 0,
                duration: clip.duration || "30s",
                fileSize: "N/A",
                timestamp: new Date(clip.created_at).toLocaleString()
              };
              
              return (
                <div
                  key={clip.id}
                  className="animate-in fade-in slide-in-from-bottom-4"
                  style={{ animationDelay: `${(index % 8) * 50}ms` }}
                >
                  <ClipCard clip={transformedClip} view={isMobile ? "list" : view} rawClipData={clip} />
                </div>
              );
            })}
          </div>

          {filteredClips.length > 0 && (
            <div className="mt-12 text-center">
              <p className="text-sm text-muted-foreground">
                Showing {filteredClips.length} clip{filteredClips.length !== 1 ? 's' : ''}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Clips;
