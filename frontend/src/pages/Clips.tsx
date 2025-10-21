import { useState, useEffect, useRef, useCallback } from "react";
import { Search, Grid3x3, List, SlidersHorizontal, X, Loader2, ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { NetflixClipCard } from "@/components/clips/NetflixClipCard";
import { useIsMobile } from "@/hooks/use-mobile";
import { useClips } from "@/hooks/useClips";
import { useSearchParams } from "react-router-dom";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { getChannelAvatarProps } from "@/lib/avatarUtils";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
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
  
  const [view, setView] = useState<"grid" | "list">("grid");
  const [channelFilter, setChannelFilter] = useState<string | undefined>(urlChannel || undefined);
  const [timeFilter, setTimeFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<string>("newest");
  const [searchQuery, setSearchQuery] = useState("");
  const [isPulling, setIsPulling] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [expandedChannels, setExpandedChannels] = useState<string[]>([]);
  const isMobile = useIsMobile();
  const touchStartY = useRef(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Count active filters
  const activeFilterCount = [channelFilter, timeFilter !== "all"].filter(Boolean).length;

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

  // Auto-expand first channel and filtered channel
  useEffect(() => {
    if (filteredClips.length > 0) {
      const channels = Object.keys(filteredClips.reduce((acc, clip) => {
        acc[clip.channel_name] = true;
        return acc;
      }, {} as Record<string, boolean>));
      
      if (channelFilter && !expandedChannels.includes(channelFilter)) {
        setExpandedChannels([channelFilter]);
      } else if (expandedChannels.length === 0 && channels.length > 0) {
        // Auto-expand first channel by default
        setExpandedChannels([channels[0]]);
      }
    }
  }, [filteredClips, channelFilter]);

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
      className="min-h-screen"
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Page Title */}
      <div className="px-6 md:px-8 pt-6 pb-4">
        <h1 className="text-3xl md:text-4xl font-bold mb-2">My Clips</h1>
        <p className="text-muted-foreground">
          {filteredClips.length} clip{filteredClips.length !== 1 ? 's' : ''} 
          {channelFilter && ` from ${channelFilter}`}
        </p>
      </div>

      <div className="px-6 md:px-8 pb-8 space-y-6">
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
      {/* Netflix-style Clean Filter Bar */}
      <div className="sticky top-0 z-30 bg-background/98 backdrop-blur-md py-4 border-b border-border/50">
        <div className="flex items-center gap-3">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <Input 
              placeholder="Search clips..."
              className="pl-10 h-12 bg-muted/50 border-0 focus-visible:ring-1 focus-visible:ring-primary text-base"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* Filters Popover */}
          {!isMobile && (
            <Popover open={filtersOpen} onOpenChange={setFiltersOpen}>
              <PopoverTrigger asChild>
                <Button variant="outline" className="h-12 gap-2">
                  <SlidersHorizontal className="w-4 h-4" />
                  Filters
                  {activeFilterCount > 0 && (
                    <Badge variant="secondary" className="ml-1 px-1.5 min-w-5 h-5">
                      {activeFilterCount}
                    </Badge>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-80 p-6" align="end">
                <div className="space-y-6">
                  <div>
                    <h4 className="font-semibold mb-3">Time Period</h4>
                    <Select value={timeFilter} onValueChange={setTimeFilter}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="24h">Last 24 hours</SelectItem>
                        <SelectItem value="7d">Last 7 days</SelectItem>
                        <SelectItem value="30d">Last 30 days</SelectItem>
                        <SelectItem value="all">All time</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <h4 className="font-semibold mb-3">Sort By</h4>
                    <Select value={sortBy} onValueChange={setSortBy}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="newest">Newest First</SelectItem>
                        <SelectItem value="highest">Highest Score</SelectItem>
                        <SelectItem value="oldest">Oldest First</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {activeFilterCount > 0 && (
                    <Button 
                      variant="outline" 
                      className="w-full"
                      onClick={() => {
                        setChannelFilter(undefined);
                        setTimeFilter("all");
                        setSortBy("newest");
                      }}
                    >
                      Clear Filters
                    </Button>
                  )}
                </div>
              </PopoverContent>
            </Popover>
          )}

          {/* View Toggle */}
          {!isMobile && (
            <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-1">
              <Button
                variant={view === "grid" ? "secondary" : "ghost"}
                size="sm"
                className="h-10"
                onClick={() => setView("grid")}
              >
                <Grid3x3 className="w-4 h-4" />
              </Button>
              <Button
                variant={view === "list" ? "secondary" : "ghost"}
                size="sm"
                className="h-10"
                onClick={() => setView("list")}
              >
                <List className="w-4 h-4" />
              </Button>
            </div>
          )}
        </div>

        {/* Active Filters Display */}
        {activeFilterCount > 0 && (
          <div className="flex items-center gap-2 mt-3 flex-wrap">
            {channelFilter && (
              <Badge variant="secondary" className="gap-2 px-3 py-1">
                Channel: {channelFilter}
                <X 
                  className="w-3 h-3 cursor-pointer hover:text-destructive" 
                  onClick={() => setChannelFilter(undefined)}
                />
              </Badge>
            )}
            {timeFilter !== "all" && (
              <Badge variant="secondary" className="gap-2 px-3 py-1">
                {timeFilter === "24h" ? "Last 24 hours" : timeFilter === "7d" ? "Last 7 days" : "Last 30 days"}
                <X 
                  className="w-3 h-3 cursor-pointer hover:text-destructive" 
                  onClick={() => setTimeFilter("all")}
                />
              </Badge>
            )}
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
          {/* Group clips by channel */}
          {channelFilter ? (
            // If filtered by channel, show as grid
            <div className={`grid gap-6 ${
              isMobile 
                ? "grid-cols-1" 
                : view === "grid" 
                  ? "grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5" 
                  : "grid-cols-1 max-w-3xl mx-auto"
            }`}>
              {filteredClips.map((clip, index) => (
                <div
                  key={clip.id}
                  className="animate-in fade-in slide-in-from-bottom-4"
                  style={{ animationDelay: `${(index % 12) * 30}ms` }}
                >
                  <NetflixClipCard clip={clip} view={view} />
                </div>
              ))}
            </div>
          ) : (
            // Collapsible channel sections
            <div className="space-y-4">
              {(() => {
                // Group clips by channel
                const clipsByChannel = filteredClips.reduce((acc, clip) => {
                  if (!acc[clip.channel_name]) {
                    acc[clip.channel_name] = [];
                  }
                  acc[clip.channel_name].push(clip);
                  return acc;
                }, {} as Record<string, typeof filteredClips>);

                // Sort channels by total clips (descending)
                const sortedChannels = Object.entries(clipsByChannel).sort(
                  (a, b) => b[1].length - a[1].length
                );

                return (
                  <Accordion type="multiple" value={expandedChannels} onValueChange={setExpandedChannels}>
                    {sortedChannels.map(([channel, channelClips]) => {
                      const isExpanded = expandedChannels.includes(channel);
                      const highestScore = Math.max(...channelClips.map(c => c.confidence_score));
                      const { gradient, initials } = getChannelAvatarProps(channel);
                      
                      return (
                        <AccordionItem key={channel} value={channel} className="border-0">
                          <AccordionTrigger className="hover:no-underline bg-card/50 hover:bg-card border border-border rounded-lg px-6 py-4 transition-all">
                            <div className="flex items-center justify-between w-full pr-4">
                              <div className="flex items-center gap-4">
                                <div 
                                  className={`w-10 h-10 rounded-full bg-gradient-to-br ${gradient} flex items-center justify-center text-white font-bold text-sm ring-2 ring-primary/20`}
                                >
                                  {initials}
                                </div>
                                <div className="text-left">
                                  <h3 className="text-lg font-bold text-foreground">{channel}</h3>
                                  <p className="text-sm text-muted-foreground">
                                    {channelClips.length} clip{channelClips.length !== 1 ? 's' : ''} • 
                                    Best: {highestScore.toFixed(2)} ⭐
                                  </p>
                                </div>
                              </div>
                              <Badge variant="outline" className="mr-2">
                                {isExpanded ? 'Collapse' : 'Expand'}
                              </Badge>
                            </div>
                          </AccordionTrigger>
                          <AccordionContent className="pt-6 pb-2">
                            <div className={`grid gap-4 ${
                              isMobile 
                                ? "grid-cols-1" 
                                : view === "grid"
                                  ? "grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
                                  : "grid-cols-1 max-w-3xl mx-auto"
                            }`}>
                              {channelClips.map((clip, index) => (
                                <div
                                  key={clip.id}
                                  className="animate-in fade-in slide-in-from-bottom-2"
                                  style={{ animationDelay: `${index * 30}ms` }}
                                >
                                  <NetflixClipCard clip={clip} view={view} />
                                </div>
                              ))}
                            </div>
                          </AccordionContent>
                        </AccordionItem>
                      );
                    })}
                  </Accordion>
                );
              })()}
            </div>
          )}

        </>
      )}
      </div>
    </div>
  );
};

export default Clips;
