import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Users, Calendar, Star, Play } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { useClips } from '../hooks/useClips';
import { clampScore } from '../lib/utils';
import { useAuth } from '../contexts/AuthContext';

const Clips = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const { isAdmin } = useAuth();

  // Fetch clips to group by streamer
  // Admin accounts fetch more clips to see all streamers
  const { data: clipsData, isLoading, error } = useClips({
    limit: isAdmin ? 1000 : 100, // Admins get 1000 clips to see all streamers
    sort_by: "newest",
  });

  const clips = clipsData?.clips || [];

  // Group clips by streamer and calculate stats
  const streamerStats = useMemo(() => {
    const grouped = clips.reduce((acc, clip) => {
      const channelName = clip.channel_name;
      if (!acc[channelName]) {
        acc[channelName] = {
          name: channelName,
          totalClips: 0,
          latestClip: null,
          avgScore: 0,
          clips: []
        };
      }
      
      acc[channelName].totalClips++;
      acc[channelName].clips.push(clip);
      
      // Track latest clip
      if (!acc[channelName].latestClip || new Date(clip.created_at) > new Date(acc[channelName].latestClip.created_at)) {
        acc[channelName].latestClip = clip;
      }
      
      return acc;
    }, {} as Record<string, any>);

    // Calculate average scores
    Object.values(grouped).forEach((streamer: any) => {
      const totalScore = streamer.clips.reduce((sum: number, clip: any) => sum + clampScore(clip.confidence_score), 0);
      streamer.avgScore = streamer.totalClips > 0 ? clampScore(totalScore / streamer.totalClips) : 0;
    });

    return Object.values(grouped).sort((a: any, b: any) => b.totalClips - a.totalClips);
  }, [clips]);

  // Filter streamers based on search query
  const filteredStreamers = useMemo(() => {
    if (!searchQuery.trim()) return streamerStats;
    
    return streamerStats.filter((streamer: any) =>
      streamer.name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [streamerStats, searchQuery]);

  // Handle streamer card click
  const handleStreamerClick = (streamerName: string) => {
    navigate(`/dashboard/clips/${encodeURIComponent(streamerName)}`);
  };

  // Get score category
  const getScoreCategory = (score: number) => {
    if (score >= 0.7) return { label: 'Top-tier', color: 'bg-green-500' };
    if (score >= 0.5) return { label: 'Above avg', color: 'bg-yellow-500' };
    return { label: 'Good', color: 'bg-blue-500' };
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  if (error) {
    return (
      <div className="p-6">
        <div className="text-center py-12">
          <p className="text-muted-foreground">Error loading clips</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Clips Library</h1>
        <p className="text-muted-foreground">Browse clips by streamer</p>
      </div>

      {/* Search Bar */}
      <div className="mb-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
          <Input
            placeholder="Search streamers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Streamer Cards Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {Array.from({ length: 8 }).map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="space-y-4">
                  <div className="w-16 h-16 bg-muted rounded-full mx-auto" />
                  <div className="space-y-2">
                    <div className="h-4 bg-muted rounded w-3/4 mx-auto" />
                    <div className="h-3 bg-muted rounded w-1/2 mx-auto" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredStreamers.length === 0 ? (
        <div className="text-center py-12">
          <Users className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">
            {searchQuery ? 'No streamers found matching your search' : 'No streamers found'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredStreamers.map((streamer: any) => {
            const scoreCategory = getScoreCategory(streamer.avgScore);
            return (
              <Card
                key={streamer.name}
                className="group cursor-pointer transition-all duration-200 hover:scale-105 hover:shadow-lg"
                onClick={() => handleStreamerClick(streamer.name)}
              >
                <CardContent className="p-6 text-center">
                  {/* Streamer Avatar */}
                  <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full mx-auto mb-4 flex items-center justify-center text-white font-bold text-xl">
                    {streamer.name.charAt(0).toUpperCase()}
                  </div>

                  {/* Streamer Name */}
                  <h3 className="font-semibold text-lg mb-2 capitalize">
                    {streamer.name}
                  </h3>

                  {/* Stats */}
                  <div className="space-y-2 mb-4">
                    <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                      <Play className="w-4 h-4" />
                      <span>{streamer.totalClips} clips</span>
                    </div>
                    
                    <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                      <Star className="w-4 h-4" />
                      <span>Avg: {streamer.avgScore.toFixed(2)}</span>
                    </div>

                    {streamer.latestClip && (
                      <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                        <Calendar className="w-4 h-4" />
                        <span>Latest: {formatDate(streamer.latestClip.created_at)}</span>
                      </div>
                    )}
                  </div>

                  {/* Score Badge */}
                  <Badge className={`${scoreCategory.color} text-white`}>
                    {scoreCategory.label}
                  </Badge>

                  {/* Hover Effect */}
                  <div className="mt-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                    <Button variant="outline" size="sm" className="w-full">
                      View Clips
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Summary Stats */}
      {streamerStats.length > 0 && (
        <div className="mt-8 p-4 bg-muted/50 rounded-lg">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>Total Streamers: {streamerStats.length}</span>
            <span>Total Clips: {clips.length}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default Clips;