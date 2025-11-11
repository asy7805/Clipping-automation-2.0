/**
 * API client for Clipping Automation 2.0 backend
 * Connects to FastAPI server at http://localhost:8000
 */

import { supabase } from './supabase';

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

  private async request<T>(endpoint: string, options?: RequestInit, timeout: number = 10000): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    try {
      // Get session token from Supabase (but don't fail if unavailable)
      let authToken: string | undefined;
      try {
        const { data: { session } } = await supabase.auth.getSession();
        authToken = session?.access_token;
      } catch (err) {
        // Continue without auth token if Supabase fails
        console.warn('Could not get auth session:', err);
      }
      
      // Don't set Content-Type for FormData - let the browser set it with the boundary
      const isFormData = options?.body instanceof FormData;
      
      // Create AbortController for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);
      
      try {
        const response = await fetch(url, {
          ...options,
          signal: controller.signal,
          headers: {
            ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
            // Only include Authorization header if we have a valid token
            ...(authToken && {
              'Authorization': `Bearer ${authToken}`
            }),
            ...options?.headers,
          },
        });
        
        clearTimeout(timeoutId);

      // Handle 401 responses - but only redirect if we're on a protected page
      if (response.status === 401) {
        console.warn('API returned 401 - authentication may be required');
        // Don't auto-redirect for now, let the app handle it
        // The backend doesn't have JWT verification yet anyway
      }

        if (!response.ok) {
          const errorText = await response.text().catch(() => response.statusText);
          throw new Error(`API error (${response.status}): ${errorText}`);
        }

        return response.json();
      } catch (error: any) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
          throw new Error(`Request timeout after ${timeout}ms: ${endpoint}`);
        }
        throw error;
      }
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
    max_score?: number;
    limit?: number;
    offset?: number;
    sort_by?: "newest" | "oldest" | "highest" | "lowest";
    search_query?: string;
  }): Promise<any> {
    const queryParams = new URLSearchParams();
    // Backend expects 'channel_name', not 'channel'
    if (params?.channel) queryParams.set('channel_name', params.channel);
    if (params?.min_score !== undefined) queryParams.set('min_score', params.min_score.toString());
    if (params?.max_score !== undefined) queryParams.set('max_score', params.max_score.toString());
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    if (params?.offset) queryParams.set('offset', params.offset.toString());
    if (params?.sort_by) queryParams.set('sort_by', params.sort_by);
    if (params?.search_query) queryParams.set('search_query', params.search_query);
    
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

  // Social Media
  async getSocialAccounts() {
    return this.request('/api/v1/social/accounts');
  }

  async initiateSocialAuth(platform: string) {
    return this.request(`/api/v1/social/auth/${platform}/initiate`, {
      method: 'POST',
    });
  }

  async oauthCallback(platform: string, data: { code: string; state: string; platform: string; channel_id?: string }) {
    return this.request(`/api/v1/social/auth/${platform}/callback`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getYouTubeChannels(accessToken: string, refreshToken?: string) {
    const params = new URLSearchParams({ access_token: accessToken });
    if (refreshToken) params.set('refresh_token', refreshToken);
    
    return this.request(`/api/v1/social/youtube/channels?${params.toString()}`);
  }

  async unlinkSocialAccount(accountId: string) {
    return this.request(`/api/v1/social/accounts/${accountId}`, {
      method: 'DELETE',
    });
  }

  async schedulePost(clipId: string, accountIds: string[], scheduledAt?: string, caption?: string) {
    return this.request('/api/v1/social/post', {
      method: 'POST',
      body: JSON.stringify({
        clip_id: clipId,
        account_ids: accountIds,
        scheduled_at: scheduledAt,
        caption: caption,
      }),
    });
  }

  async getPostingQueue(status?: string) {
    const queryParams = new URLSearchParams();
    if (status) queryParams.set('status', status);
    
    const query = queryParams.toString();
    return this.request(`/api/v1/social/queue${query ? `?${query}` : ''}`);
  }

  async getNotifications() {
    return this.request('/api/v1/social/notifications');
  }

  async retryQueueItem(queueId: string) {
    return this.request(`/api/v1/social/queue/${queueId}/retry`, {
      method: 'POST',
    });
  }

  async cancelQueueItem(queueId: string) {
    return this.request(`/api/v1/social/queue/${queueId}`, {
      method: 'DELETE',
    });
  }

  async createEditJob(fileId: string, edits: any) {
    const formData = new FormData();
    formData.append('file_id', fileId);
    formData.append('edits', JSON.stringify(edits));
    
    return this.request('/api/v1/editor/edit', {
      method: 'POST',
      body: formData,
    });
  }

  async getJobStatus(jobId: string) {
    return this.request(`/api/v1/editor/job/${jobId}`);
  }

  async downloadEditedVideo(jobId: string) {
    return this.request(`/api/v1/editor/download/${jobId}`, {
      method: 'GET',
    });
  }

  async listEditJobs() {
    return this.request('/api/v1/editor/jobs');
  }

  async deleteEditJob(jobId: string) {
    return this.request(`/api/v1/editor/job/${jobId}`, {
      method: 'DELETE',
    });
  }

  // Video Editor API methods (new CapCut-style editor)
  async getVideoProjects() {
    return this.request('/api/v1/editor/projects', {
      method: 'GET',
    });
  }

  async createVideoProject(projectData: { name: string; source_clip_id?: string; source_file_url: string }) {
    return this.request('/api/v1/editor/projects', {
      method: 'POST',
      body: JSON.stringify(projectData),
    });
  }

  async getVideoProject(projectId: string) {
    return this.request(`/api/v1/editor/projects/${projectId}`, {
      method: 'GET',
    });
  }

  async updateVideoProject(projectId: string, updateData: { name?: string; edit_state?: any }) {
    return this.request(`/api/v1/editor/projects/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify(updateData),
    });
  }

  async deleteVideoProject(projectId: string) {
    return this.request(`/api/v1/editor/projects/${projectId}`, {
      method: 'DELETE',
    });
  }

  async duplicateVideoProject(projectId: string) {
    return this.request(`/api/v1/editor/projects/${projectId}/duplicate`, {
      method: 'POST',
    });
  }

  async startVideoExport(projectId: string) {
    return this.request(`/api/v1/editor/projects/${projectId}/export`, {
      method: 'POST',
    });
  }

  async getVideoExports() {
    return this.request('/api/v1/editor/exports', {
      method: 'GET',
    });
  }

  async getVideoExportStatus(exportId: string) {
    return this.request(`/api/v1/editor/exports/${exportId}`, {
      method: 'GET',
    });
  }

  async downloadVideoExport(exportId: string) {
    return this.request(`/api/v1/editor/exports/${exportId}/download`, {
      method: 'GET',
    });
  }

  async getTextTemplates() {
    return this.request('/api/v1/editor/templates/text', {
      method: 'GET',
    });
  }

  async getFullTemplates() {
    return this.request('/api/v1/editor/templates/full', {
      method: 'GET',
    });
  }

  async uploadVideo(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    
    return this.request('/api/v1/editor/upload', {
      method: 'POST',
      body: formData,
    });
  }
}

export const apiClient = new APIClient();

