import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useClips } from '../hooks/useClips';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Slider } from '../components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { ArrowLeft, Filter, Calendar, Star } from 'lucide-react';
import { NetflixClipCard } from '../components/clips/NetflixClipCard';

export const StreamerClips = () => {
  const { streamerName: rawStreamerName } = useParams<{ streamerName: string }>();
  const navigate = useNavigate();
  
  // Safely extract streamerName - handle undefined and decode URL
  const streamerName = rawStreamerName 
    ? (typeof rawStreamerName === 'string' ? decodeURIComponent(rawStreamerName) : String(rawStreamerName))
    : null;
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 12; // 12 clips per page
  
  // Filter states
  const [scoreRange, setScoreRange] = useState<[number, number]>([0, 1]);
  const [sortBy, setSortBy] = useState<'newest' | 'oldest' | 'highest' | 'lowest'>('newest');
  const [showFilters, setShowFilters] = useState(false);

  // Redirect if streamerName is missing
  useEffect(() => {
    if (!streamerName) {
      navigate('/dashboard/clips');
    }
  }, [streamerName, navigate]);

  // Fetch clips for this specific streamer with pagination
  const { data: clipsData, isLoading, error } = useClips({
    channel_name: streamerName || undefined,
    min_score: scoreRange[0],
    max_score: scoreRange[1],
    sort_by: sortBy,
    limit: itemsPerPage,
    offset: (currentPage - 1) * itemsPerPage,
  });

  const clips = clipsData?.clips || [];
  const paginationInfo = clipsData?.pagination;

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [scoreRange, sortBy]);

  // Show loading/error if streamerName is missing
  if (!streamerName) {
    return (
      <div className="p-6">
        <div className="text-center py-12">
          <p className="text-muted-foreground">Invalid streamer name</p>
          <Button
            variant="outline"
            onClick={() => navigate('/dashboard/clips')}
            className="mt-4"
          >
            Back to All Streamers
          </Button>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="flex items-center gap-4 mb-6">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/dashboard/clips')}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to All Streamers
          </Button>
        </div>
        <div className="text-center py-12">
          <p className="text-muted-foreground">Error loading clips for {String(streamerName)}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/dashboard/clips')}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to All Streamers
          </Button>
          <div>
            <h1 className="text-2xl font-bold capitalize">{String(streamerName)}</h1>
            <p className="text-muted-foreground">
              {paginationInfo ? `${paginationInfo.total} total clips` : `${clips.length} clips`}
            </p>
          </div>
        </div>
        
        <Button
          variant="outline"
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-2"
        >
          <Filter className="w-4 h-4" />
          Filters
        </Button>
      </div>

      <div className="flex gap-6">
        {/* Filters Sidebar */}
        {showFilters && (
          <div className="w-72 space-y-4">
            <Card className="glass-strong border-white/10">
              <CardContent className="p-6 space-y-6">
                <div>
                  <h3 className="text-lg font-semibold mb-1">Filters</h3>
                  <p className="text-xs text-muted-foreground">Refine your clip selection</p>
                </div>
                
                <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
                
                {/* Score Range Slider */}
                <div className="space-y-3">
                  <label className="text-sm font-medium flex items-center gap-2">
                    <Star className="w-4 h-4 text-yellow-500" />
                    Score Range
                  </label>
                  <div className="px-2 py-3 rounded-lg bg-background/50">
                    <Slider
                      value={scoreRange}
                      onValueChange={setScoreRange}
                      max={1}
                      min={0}
                      step={0.01}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-muted-foreground mt-2">
                      <span className="font-mono">{scoreRange[0].toFixed(2)}</span>
                      <span className="font-mono">{scoreRange[1].toFixed(2)}</span>
                    </div>
                  </div>
                  
                  {/* Quick Filter Buttons */}
                  <div className="grid grid-cols-3 gap-2">
                    <Button
                      variant={scoreRange[0] === 0 && scoreRange[1] === 0.5 ? "default" : "outline"}
                      size="sm"
                      onClick={() => setScoreRange([0, 0.5])}
                      className="text-xs h-auto py-2 px-2"
                    >
                      <div className="flex flex-col items-center gap-1">
                        <span className="font-semibold">Good</span>
                        <span className="text-[10px] opacity-70">0.0-0.5</span>
                      </div>
                    </Button>
                    <Button
                      variant={scoreRange[0] === 0.5 && scoreRange[1] === 0.7 ? "default" : "outline"}
                      size="sm"
                      onClick={() => setScoreRange([0.5, 0.7])}
                      className="text-xs h-auto py-2 px-2"
                    >
                      <div className="flex flex-col items-center gap-1">
                        <span className="font-semibold">Above avg</span>
                        <span className="text-[10px] opacity-70">0.5-0.7</span>
                      </div>
                    </Button>
                    <Button
                      variant={scoreRange[0] === 0.7 && scoreRange[1] === 1.0 ? "default" : "outline"}
                      size="sm"
                      onClick={() => setScoreRange([0.7, 1.0])}
                      className="text-xs h-auto py-2 px-2"
                    >
                      <div className="flex flex-col items-center gap-1">
                        <span className="font-semibold">Top-tier</span>
                        <span className="text-[10px] opacity-70">0.7-1.0</span>
                      </div>
                    </Button>
                  </div>
                </div>

                <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

                {/* Sort By */}
                <div className="space-y-3">
                  <label className="text-sm font-medium flex items-center gap-2">
                    <Filter className="w-4 h-4 text-blue-500" />
                    Sort By
                  </label>
                  <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
                    <SelectTrigger className="bg-background/50">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="newest">
                        <div className="flex items-center gap-2">
                          <Calendar className="w-4 h-4" />
                          Newest First
                        </div>
                      </SelectItem>
                      <SelectItem value="oldest">
                        <div className="flex items-center gap-2">
                          <Calendar className="w-4 h-4" />
                          Oldest First
                        </div>
                      </SelectItem>
                      <SelectItem value="highest">
                        <div className="flex items-center gap-2">
                          <Star className="w-4 h-4" />
                          Highest Score
                        </div>
                      </SelectItem>
                      <SelectItem value="lowest">
                        <div className="flex items-center gap-2">
                          <Star className="w-4 h-4" />
                          Lowest Score
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

                {/* Reset Filters */}
                <Button
                  variant="outline"
                  onClick={() => {
                    setScoreRange([0, 1]);
                    setSortBy('newest');
                  }}
                  className="w-full bg-background/50 hover:bg-background/80"
                >
                  Reset All Filters
                </Button>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Clips Grid */}
        <div className="flex-1">
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="aspect-video animate-pulse bg-muted rounded-lg" />
              ))}
            </div>
          ) : clips.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No clips found for {String(streamerName)}</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {clips.map((clip) => (
                  <NetflixClipCard
                    key={clip.id}
                    clip={clip}
                  />
                ))}
              </div>

              {/* Pagination Controls */}
              {paginationInfo && paginationInfo.total_pages > 1 && (
                <div className="flex items-center justify-center gap-4 mt-8">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={!paginationInfo.has_prev || isLoading}
                  >
                    Previous
                  </Button>
                  
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">
                      Page {paginationInfo.page} of {paginationInfo.total_pages}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      ({paginationInfo.total} total clips)
                    </span>
                  </div>
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(prev => Math.min(paginationInfo.total_pages, prev + 1))}
                    disabled={!paginationInfo.has_next || isLoading}
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default StreamerClips;
