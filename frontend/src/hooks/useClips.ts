import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";

export interface ScoreBreakdown {
  energy: number;
  pitch: number;
  emotion: number;
  keyword: number;
  final_score: number;
}

export interface Clip {
  id: string;
  transcript: string;
  is_clip_worthy: boolean;
  confidence_score: number;
  created_at: string;
  stream_id: string;
  channel_name: string;
  storage_url?: string;
  file_size?: number;
  thumbnail?: string;
  thumbnail_url?: string; // Real thumbnail from video first frame
  duration?: string;
  audio_energy?: number;
  emotion?: string;
  emotion_score?: number;
  score_breakdown?: ScoreBreakdown;
  expires_at?: string | null; // For trial clip expiration
  has_watermark?: boolean; // For trial clip watermark indicator
}

interface UseClipsOptions {
  limit?: number;
  offset?: number;
  channel_name?: string;
  is_clip_worthy?: boolean;
  min_score?: number;
  max_score?: number;
  sort_by?: "newest" | "oldest" | "highest" | "lowest";
  search_query?: string;
  enabled?: boolean;
  refetchInterval?: number;
}

interface PaginatedClipsResponse {
  clips: Clip[];
  pagination: {
    total: number;
    page: number;
    limit: number;
    offset: number;
    has_next: boolean;
    has_prev: boolean;
    total_pages: number;
  };
}

export function useClips(options: UseClipsOptions = {}) {
  const {
    limit = 20,
    offset = 0,
    channel_name,
    is_clip_worthy,
    min_score,
    max_score,
    sort_by = "newest",
    search_query,
    enabled = true,
    refetchInterval = 30000, // Refresh every 30 seconds
  } = options;

  return useQuery({
    queryKey: ["clips", limit, offset, channel_name, is_clip_worthy, min_score, max_score, sort_by, search_query],
    queryFn: async () => {
      // Add timeout wrapper to prevent hanging
      const timeoutPromise = new Promise<PaginatedClipsResponse>((_, reject) => 
        setTimeout(() => reject(new Error('Request timeout')), 10000)
      );
      
      const fetchPromise = apiClient.getClips({
        channel: channel_name,
        limit,
        offset,
        min_score,
        max_score,
        sort_by,
        search_query,
      }).then(response => {
        console.log('✅ Clips API response:', response);
        console.log(`📹 Found ${response?.clips?.length || 0} clips`);
        return response as PaginatedClipsResponse;
      });
      
      return Promise.race([fetchPromise, timeoutPromise]);
    },
    enabled,
    refetchInterval,
    staleTime: Math.min(refetchInterval || 30000, 15000), // Increased stale time for better caching
    retry: 1, // Reduced retries for faster failure
    retryDelay: 500, // Faster retry delay
    // Return cached data immediately while fetching in background
    placeholderData: (previousData) => previousData,
  });
}

export function useClipById(clipId: string) {
  return useQuery({
    queryKey: ["clip", clipId],
    queryFn: async () => {
      // For now, get all clips and find the one we need
      // TODO: Add getClip(id) method to apiClient
      const clips = await apiClient.getClips({ limit: 100 });
      const clip = clips.find(c => c.id === clipId);
      if (!clip) throw new Error("Clip not found");
      return clip as Clip;
    },
    enabled: !!clipId,
  });
}

