/**
 * API client for Clipping Automation 2.0 backend
 * Connects to FastAPI server at http://localhost:8000
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface StreamResponse {
  id: string;
  twitch_stream_id: string;
  channel_name: string;
  title: string;
  category: string;
  started_at: string;
  viewer_count: number;
  is_live: boolean;
  status: string;
}

export interface ClipResponse {
  id: string;
  stream_id: string;
  channel_name: string;
  transcript: string;
  score: number;
  duration: number;
  file_size: number;
  audio_energy: number;
  emotion: { label: string; score: number };
  created_at: string;
  storage_url: string;
}

export interface AnalyticsSummary {
  total_clips: number;
  avg_score: number;
  storage_used_gb: number;
  active_monitors: number;
  clips_today: number;
  trend: number;
}

class APIClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      return response.json();
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error);
      throw error;
    }
  }

  // Health check
  async getHealth() {
    return this.request('/api/v1/health');
  }

  // Streams
  async getStreams(): Promise<StreamResponse[]> {
    return this.request('/api/v1/streams');
  }

  async getStream(streamId: string): Promise<StreamResponse> {
    return this.request(`/api/v1/streams/${streamId}`);
  }

  async getLiveStreams(): Promise<StreamResponse[]> {
    return this.request('/api/v1/streams/live');
  }

  // Clips
  async getClips(params?: {
    channel?: string;
    min_score?: number;
    limit?: number;
    offset?: number;
  }): Promise<ClipResponse[]> {
    const queryParams = new URLSearchParams();
    // Backend expects 'channel_name', not 'channel'
    if (params?.channel) queryParams.set('channel_name', params.channel);
    if (params?.min_score !== undefined) queryParams.set('min_score', params.min_score.toString());
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    if (params?.offset) queryParams.set('offset', params.offset.toString());
    
    const query = queryParams.toString();
    return this.request(`/api/v1/clips${query ? `?${query}` : ''}`);
  }

  async predictClipWorthiness(transcript: string, modelVersion: string = 'latest') {
    return this.request('/api/v1/clips/predict', {
      method: 'POST',
      body: JSON.stringify({ transcript, model_version: modelVersion }),
    });
  }

  // Analytics
  async getAnalyticsSummary(days: number = 7): Promise<AnalyticsSummary> {
    return this.request(`/api/v1/analytics/summary?days=${days}`);
  }

  async getChannelAnalytics() {
    return this.request('/api/v1/analytics/channels');
  }

  async getPerformanceMetrics() {
    return this.request('/api/v1/analytics/performance');
  }

  // Monitors
  async startMonitor(twitchUrl: string) {
    return this.request('/api/v1/monitors/start', {
      method: 'POST',
      body: JSON.stringify({ twitch_url: twitchUrl }),
    });
  }

  async stopMonitor(channelName: string) {
    return this.request(`/api/v1/monitors/stop/${channelName}`, {
      method: 'POST',
    });
  }

  async getMonitors() {
    return this.request('/api/v1/monitors');
  }

  async getMonitorStatus(channelName: string) {
    return this.request(`/api/v1/monitors/${channelName}`);
  }

  async getMonitorStats(channelName: string) {
    return this.request(`/api/v1/monitors/${channelName}/stats`);
  }

  async getMonitorHealth(channelName: string) {
    return this.request(`/api/v1/monitors/${channelName}/health`);
  }
}

export const apiClient = new APIClient();

