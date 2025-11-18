import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";

interface MonitorStats {
  clips_captured: number;
  segments_analyzed: number;
  last_clip_time: string | null;
  total_size_mb: number;
}

export function useMonitorStats(channelName: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ["monitor-stats", channelName],
    queryFn: async () => {
      try {
        const stats = await apiClient.getMonitorStats(channelName);
        return stats as MonitorStats;
      } catch (error: any) {
        // Return default stats if monitor doesn't exist (404)
        if (error.message?.includes('Not Found') || error.message?.includes('404')) {
          return {
            clips_captured: 0,
            segments_analyzed: 0,
            last_clip_time: null,
            total_size_mb: 0
          } as MonitorStats;
        }
        throw error;
      }
    },
    enabled: enabled && !!channelName,
    refetchInterval: 15000, // Refresh every 15 seconds
    staleTime: 10000,
    retry: false, // Don't retry on 404 errors
  });
}

