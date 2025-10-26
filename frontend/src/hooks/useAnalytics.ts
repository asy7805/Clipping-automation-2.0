import { useQuery } from "@tanstack/react-query";
import { useClips } from "./useClips";

interface AnalyticsData {
  totalClips: number;
  avgScore: number;
  highScoreClips: number;
  storageUsedGB: number;
  topChannels: Array<{
    name: string;
    clips: number;
    avgScore: number;
  }>;
  clips: Array<{
    created_at: string;
    confidence_score: number;
    channel_name: string;
    file_size: number;
  }>;
}

export function useAnalytics() {
  const { data: clipsData, isLoading } = useClips({ limit: 1000 }); // Get as many clips as possible

  return useQuery({
    queryKey: ["analytics", clipsData?.clips?.length],
    queryFn: async () => {
      // Extract clips array from paginated response
      const clips = clipsData?.clips || [];
      
      if (!clips || clips.length === 0) {
        return {
          totalClips: 0,
          avgScore: 0,
          highScoreClips: 0,
          storageUsedGB: 0,
          topChannels: [],
          clips: []
        };
      }

      // Calculate real metrics
      const totalSize = clips.reduce((sum, c) => sum + (c.file_size || 0), 0);
      const storageUsedGB = totalSize / (1024 ** 3);
      
      // Calculate average score and high score clips
      const scoresOnly = clips.map(c => c.confidence_score || 0).filter(s => s > 0);
      const avgScore = scoresOnly.length > 0 
        ? scoresOnly.reduce((sum, score) => sum + score, 0) / scoresOnly.length 
        : 0;
      const highScoreClips = clips.filter(c => (c.confidence_score || 0) >= 0.7).length;

      // Group by channel
      const channelStats: Record<string, { count: number; totalScore: number; scoreCount: number }> = {};
      clips.forEach(clip => {
        if (!channelStats[clip.channel_name]) {
          channelStats[clip.channel_name] = { count: 0, totalScore: 0, scoreCount: 0 };
        }
        channelStats[clip.channel_name].count++;
        if (clip.confidence_score && clip.confidence_score > 0) {
          channelStats[clip.channel_name].totalScore += clip.confidence_score;
          channelStats[clip.channel_name].scoreCount++;
        }
      });

      // Calculate top channels by clip count
      const topChannels = Object.entries(channelStats)
        .map(([name, stats]) => ({
          name,
          clips: stats.count,
          avgScore: stats.scoreCount > 0 ? stats.totalScore / stats.scoreCount : 0
        }))
        .sort((a, b) => b.clips - a.clips)
        .slice(0, 5);

      return {
        totalClips: clips.length,
        avgScore,
        highScoreClips,
        storageUsedGB: Math.round(storageUsedGB * 100) / 100,
        topChannels,
        clips: clips.map(c => ({
          created_at: c.created_at,
          confidence_score: c.confidence_score || 0,
          channel_name: c.channel_name,
          file_size: c.file_size || 0
        }))
      } as AnalyticsData;
    },
    enabled: !isLoading && !!clipsData?.clips,
    staleTime: 30000,
  });
}

