import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";

interface MonitorHealth {
  process_alive: boolean;
  process_id: number;
  uptime: string;
  uptime_seconds: number;
  is_live: boolean;
  viewer_count: number;
  stream_title: string;
  game_name: string;
  thumbnail_url: string;
  stream_started_at: string;
  cpu_percent: number;
  memory_mb: number;
  healthy: boolean;
  warnings: string[];
}

export function useMonitorHealth(channelName: string, enabled: boolean = true) {
  return useQuery<MonitorHealth, Error>({
    queryKey: ["monitor-health", channelName],
    queryFn: async () => {
      try {
        const health = await apiClient.getMonitorHealth(channelName);
        return health as MonitorHealth;
      } catch (error: any) {
        // Return default health if monitor doesn't exist (404)
        if (error.message?.includes('Not Found') || error.message?.includes('404')) {
          return {
            process_alive: false,
            process_id: 0,
            uptime: '0m',
            uptime_seconds: 0,
            is_live: false,
            viewer_count: 0,
            stream_title: '',
            game_name: '',
            thumbnail_url: '',
            stream_started_at: '',
            cpu_percent: 0,
            memory_mb: 0,
            healthy: false,
            warnings: ['Monitor not found']
          } as MonitorHealth;
        }
        throw error;
      }
    },
    enabled: enabled && !!channelName,
    refetchInterval: 15000, // Refresh every 15 seconds
    staleTime: 10000, // Data considered fresh for 10 seconds
    retry: false, // Don't retry on 404 errors
  });
}



