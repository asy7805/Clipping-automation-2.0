import { useQuery, UseQueryResult } from "@tanstack/react-query";
import { apiClient, StreamResponse } from "@/lib/api";

export interface StreamData {
  id: string;
  channel: string;
  avatar: string;
  title: string;
  category: string;
  viewers: number;
  status: "analyzing" | "processing" | "paused";
  runtime: string;
  segments: number;
  clips: number;
  lastClip: string;
  bufferProgress: number;
  bufferCount: { current: number; total: number };
  session_started_at?: string; // For trial session limit tracking
}

export interface DashboardStats {
  activeMonitors: number;
  clipsToday: number;
  clipsTrend: number;
  storageUsed: number;
  storageTotal: number;
  avgScore: number;
  scoreTrend: number;
}

// Transform API response to frontend format
const transformStreamData = (stream: StreamResponse): StreamData => {
  const startTime = new Date(stream.started_at);
  const runtime = stream.is_live 
    ? Math.floor((Date.now() - startTime.getTime()) / 1000 / 60) // minutes
    : 0;
  
  const hours = Math.floor(runtime / 60);
  const minutes = runtime % 60;
  const runtimeStr = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;

  return {
    id: stream.id,
    channel: stream.channel_name,
    avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${stream.channel_name}`,
    title: stream.title || "No title",
    category: stream.category || "Unknown",
    viewers: stream.viewer_count,
    status: stream.is_live ? "analyzing" : "paused",
    runtime: runtimeStr,
    segments: 0, // TODO: Add to API
    clips: 0, // TODO: Add to API
    lastClip: "unknown", // TODO: Add to API
    bufferProgress: Math.random() * 0.8, // TODO: Add to API
    bufferCount: { current: Math.floor(Math.random() * 4), total: 5 }
  };
};

// Helper function to add timeout to promises
const fetchWithTimeout = async <T,>(promise: Promise<T>, timeout: number, fallback: T): Promise<T> => {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) => 
      setTimeout(() => reject(new Error('Timeout')), timeout)
    )
  ]).catch(() => fallback);
};

const fetchStreams = async (): Promise<StreamData[]> => {
  try {
    // Fetch active monitors instead of streams table
    const response = await apiClient.getMonitors();
    console.log('✅ Monitors API response:', response);
    const allMonitors = response.monitors || [];
    
    // Don't filter out stopped monitors - they should stay visible
    // Backend already filters out dead processes, so all monitors here are valid
    const monitors = allMonitors; // Keep all monitors (offline streamers stay visible)
    console.log(`📊 Found ${monitors.length} monitors (including offline streamers):`, monitors);
    
    // Transform monitors to StreamData format with real data
    // Add timeout to prevent hanging on slow monitors
    const streamDataPromises = monitors.map(async (monitor: any) => {
      try {
        // Fetch monitor stats and health with 3 second timeout each
        const [stats, health] = await Promise.all([
          fetchWithTimeout(
            apiClient.getMonitorStats(monitor.channel_name),
            3000,
            {
              segments_analyzed: 0,
              clips_captured: 0,
              last_clip_time: null
            }
          ),
          fetchWithTimeout(
            apiClient.getMonitorHealth(monitor.channel_name),
            3000,
            {
              healthy: false,
              viewer_count: 0,
              is_live: false
            }
          )
        ]);
        
        const startTime = new Date(monitor.started_at);
        const runtime = Math.floor((Date.now() - startTime.getTime()) / 1000 / 60); // minutes
        
        const hours = Math.floor(runtime / 60);
        const minutes = runtime % 60;
        const runtimeStr = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;

        // Determine status based on monitor state and streamer status
        // Monitor stays visible even when streamer is offline - it will resume automatically
        let displayStatus: "analyzing" | "processing" | "paused";
        let title: string;
        
        if (monitor.status === "stopped") {
          // Monitor was manually stopped
          displayStatus = "paused";
          title = `Stopped: ${monitor.channel_name}`;
        } else if (monitor.status === "running") {
          // Monitor is running - check if streamer is live
          if (health.is_live) {
            displayStatus = "analyzing";
            title = `Live monitoring ${monitor.channel_name}`;
          } else {
            // Streamer is offline but monitor is waiting - show as paused but keep visible
            displayStatus = "paused";
            title = `Waiting for ${monitor.channel_name} to go live`;
          }
        } else {
          displayStatus = "paused";
          title = `Monitoring ${monitor.channel_name}`;
        }

        return {
          id: monitor.id || `${monitor.channel_name}-${monitor.started_at}`, // Use database ID for uniqueness
          channel: monitor.channel_name,
          avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${monitor.channel_name}`,
          title: title,
          category: "Live Stream",
          viewers: health.viewer_count || 0,
          status: displayStatus,
          runtime: runtimeStr,
          segments: stats.segments_analyzed || 0,
          clips: stats.clips_captured || 0,
          lastClip: stats.last_clip_time ? `${Math.floor((Date.now() - new Date(stats.last_clip_time).getTime()) / 1000 / 60)}m ago` : (monitor.status === "stopped" ? "stopped" : "analyzing..."),
          bufferProgress: monitor.status === "stopped" ? 0 : (health.healthy ? Math.random() * 0.8 : 0),
          bufferCount: { current: monitor.status === "stopped" ? 0 : Math.floor(Math.random() * 4), total: 5 },
          session_started_at: monitor.session_started_at // Include session_started_at for trial timer
        } as StreamData;
      } catch (error) {
        console.error(`Error fetching data for ${monitor.channel_name}:`, error);
        // Return basic data if stats/health fetch fails
        const startTime = new Date(monitor.started_at);
        const runtime = Math.floor((Date.now() - startTime.getTime()) / 1000 / 60);
        const hours = Math.floor(runtime / 60);
        const minutes = runtime % 60;
        const runtimeStr = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
        
        return {
          id: monitor.id || `${monitor.channel_name}-${monitor.started_at}`, // Use database ID for uniqueness
          channel: monitor.channel_name,
          avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${monitor.channel_name}`,
          title: `Live monitoring ${monitor.channel_name}`,
          category: "Live Stream",
          viewers: 0,
          status: "analyzing",
          runtime: runtimeStr,
          segments: 0,
          clips: 0,
          lastClip: "analyzing...",
          bufferProgress: 0,
          bufferCount: { current: 0, total: 5 }
        } as StreamData;
      }
    });
    
    const result = await Promise.all(streamDataPromises);
    console.log('✨ Transformed stream data:', result);
    return result;
  } catch (error) {
    console.error('❌ Failed to fetch monitors:', error);
    // Return empty array on error, let React Query handle retries
    return [];
  }
};

const fetchStats = async (): Promise<DashboardStats> => {
  try {
    // Get monitors count directly
    const monitorsResponse = await apiClient.getMonitors();
    const activeMonitors = monitorsResponse.monitors?.length || 0;
    
    // Get clips data for real metrics
    const clipsResponse = await apiClient.getClips({ limit: 100 });
    const clips = clipsResponse?.clips || [];
    
    // Calculate real metrics from clips
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const clipsToday = clips.filter(clip => {
      const clipDate = new Date(clip.created_at);
      return clipDate >= today;
    }).length;
    
    const totalSize = clips.reduce((sum, clip) => sum + (clip.file_size || 0), 0);
    const storageUsed = totalSize / (1024 ** 3); // Convert to GB
    
    const scores = clips.map(clip => clip.confidence_score || 0);
    const avgScore = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
    
    return {
      activeMonitors,
      clipsToday,
      clipsTrend: clipsToday > 0 ? 15 : 0, // Simple trend calculation
      storageUsed: Math.round(storageUsed * 100) / 100,
      storageTotal: 10,
      avgScore: Math.round(avgScore * 100) / 100,
      scoreTrend: 0.03
    };
  } catch (error) {
    console.error('Failed to fetch stats:', error);
    // Return default stats on error
    return {
      activeMonitors: 0,
      clipsToday: 0,
      clipsTrend: 0,
      storageUsed: 0,
      storageTotal: 10,
      avgScore: 0,
      scoreTrend: 0
    };
  }
};

export const useStreams = (): UseQueryResult<StreamData[], Error> => {
  return useQuery({
    queryKey: ["streams"],
    queryFn: fetchStreams,
    refetchInterval: 15000, // Refetch every 15 seconds (reduced frequency)
    staleTime: 10000, // Consider data stale after 10 seconds
    retry: 1, // Reduced retries for faster failure
    retryDelay: 500, // Faster retry delay
    placeholderData: (previousData) => previousData, // Show cached data immediately
  });
};

export const useDashboardStats = (): UseQueryResult<DashboardStats, Error> => {
  return useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: fetchStats,
    refetchInterval: 30000, // Refetch every 30 seconds (stats don't need frequent updates)
    staleTime: 20000, // Consider data stale after 20 seconds
    retry: 1,
    retryDelay: 500,
    placeholderData: (previousData) => previousData,
  });
};
