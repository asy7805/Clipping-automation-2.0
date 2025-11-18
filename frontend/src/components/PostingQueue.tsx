import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  RefreshCw,
  ExternalLink,
  Trash2,
  Filter,
  Calendar,
  Video
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { toast } from "sonner";

interface PostingQueueItem {
  id: string;
  clip_id: string;
  status: string;
  scheduled_at?: string;
  posted_at?: string;
  post_url?: string;
  caption?: string;
  error_message?: string;
  retry_count: number;
  created_at: string;
  social_account?: {
    platform: string;
    account_name: string;
  };
}

interface PostingQueueProps {
  className?: string;
}

const PostingQueue: React.FC<PostingQueueProps> = ({ className }) => {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const queryClient = useQueryClient();

  // Fetch posting queue
  const { data: queueData, isLoading, error } = useQuery({
    queryKey: ["posting-queue", statusFilter],
    queryFn: async () => {
      const response = await apiClient.getPostingQueue(statusFilter === "all" ? undefined : statusFilter);
      return response;
    },
    refetchInterval: 10000, // Refetch every 10 seconds
  });

  // Retry failed post
  const retryPost = useMutation({
    mutationFn: async (queueId: string) => {
      return await apiClient.retryQueueItem(queueId);
    },
    onSuccess: () => {
      toast.success("Post queued for retry");
      queryClient.invalidateQueries({ queryKey: ["posting-queue"] });
    },
    onError: (error: any) => {
      toast.error(`Failed to retry post: ${error.message}`);
    },
  });

  // Cancel scheduled post
  const cancelPost = useMutation({
    mutationFn: async (queueId: string) => {
      return await apiClient.cancelQueueItem(queueId);
    },
    onSuccess: () => {
      toast.success("Post cancelled");
      queryClient.invalidateQueries({ queryKey: ["posting-queue"] });
    },
    onError: (error: any) => {
      toast.error(`Failed to cancel post: ${error.message}`);
    },
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'processing':
        return <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'posted':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'cancelled':
        return <AlertCircle className="w-4 h-4 text-gray-500" />;
      default:
        return <AlertCircle className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      pending: "secondary",
      processing: "default",
      posted: "default",
      failed: "destructive",
      cancelled: "outline"
    } as const;

    const colors = {
      pending: "bg-yellow-500",
      processing: "bg-blue-500",
      posted: "bg-green-500",
      failed: "bg-red-500",
      cancelled: "bg-gray-500"
    };

    return (
      <Badge variant={variants[status as keyof typeof variants] || "outline"} className="flex items-center gap-1">
        {getStatusIcon(status)}
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    );
  };

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'tiktok':
        return '🎵';
      case 'youtube':
        return '📺';
      default:
        return '🔗';
    }
  };

  const formatDateTime = (dateTime: string) => {
    return new Date(dateTime).toLocaleString();
  };

  const formatRelativeTime = (dateTime: string) => {
    const now = new Date();
    const date = new Date(dateTime);
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Video className="w-5 h-5" />
            Posting Queue
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
              <p className="text-muted-foreground">Loading posting queue...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Video className="w-5 h-5" />
            Posting Queue
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Failed to load posting queue: {(error as Error).message}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  const queueItems = queueData?.queue_items || [];

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Video className="w-5 h-5" />
              Posting Queue
            </CardTitle>
            <CardDescription>
              Manage your scheduled and posted content
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1 rounded-md border bg-background text-sm"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="posted">Posted</option>
              <option value="failed">Failed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {queueItems.length === 0 ? (
          <div className="text-center py-8">
            <Video className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium text-foreground mb-2">No posts yet</h3>
            <p className="text-muted-foreground">
              Start posting clips to see them appear here
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Summary Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-3 rounded-lg bg-muted/20">
                <div className="text-2xl font-bold text-yellow-600">
                  {queueItems.filter(item => item.status === 'pending').length}
                </div>
                <div className="text-sm text-muted-foreground">Pending</div>
              </div>
              <div className="text-center p-3 rounded-lg bg-muted/20">
                <div className="text-2xl font-bold text-blue-600">
                  {queueItems.filter(item => item.status === 'processing').length}
                </div>
                <div className="text-sm text-muted-foreground">Processing</div>
              </div>
              <div className="text-center p-3 rounded-lg bg-muted/20">
                <div className="text-2xl font-bold text-green-600">
                  {queueItems.filter(item => item.status === 'posted').length}
                </div>
                <div className="text-sm text-muted-foreground">Posted</div>
              </div>
              <div className="text-center p-3 rounded-lg bg-muted/20">
                <div className="text-2xl font-bold text-red-600">
                  {queueItems.filter(item => item.status === 'failed').length}
                </div>
                <div className="text-sm text-muted-foreground">Failed</div>
              </div>
            </div>

            {/* Queue Items Table */}
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Platform</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Caption</TableHead>
                    <TableHead>Schedule</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {queueItems.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className="text-lg">
                            {getPlatformIcon(item.social_account?.platform || 'unknown')}
                          </span>
                          <div>
                            <div className="font-medium capitalize">
                              {item.social_account?.platform || 'Unknown'}
                            </div>
                            <div className="text-sm text-muted-foreground">
                              @{item.social_account?.account_name || 'Unknown'}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        {getStatusBadge(item.status)}
                        {item.retry_count > 0 && (
                          <div className="text-xs text-muted-foreground mt-1">
                            Retry #{item.retry_count}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="max-w-[200px]">
                          {item.caption ? (
                            <div className="truncate" title={item.caption}>
                              {item.caption}
                            </div>
                          ) : (
                            <span className="text-muted-foreground">No caption</span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {item.scheduled_at ? (
                            <div>
                              <div className="flex items-center gap-1">
                                <Calendar className="w-3 h-3" />
                                {formatDateTime(item.scheduled_at)}
                              </div>
                              <div className="text-muted-foreground">
                                {formatRelativeTime(item.scheduled_at)}
                              </div>
                            </div>
                          ) : (
                            <span className="text-muted-foreground">Immediate</span>
                          )}
                        </div>
                        {item.posted_at && (
                          <div className="text-xs text-muted-foreground mt-1">
                            Posted: {formatRelativeTime(item.posted_at)}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {item.status === 'failed' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => retryPost.mutate(item.id)}
                              disabled={retryPost.isPending}
                            >
                              <RefreshCw className="w-3 h-3 mr-1" />
                              Retry
                            </Button>
                          )}
                          {item.status === 'pending' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => cancelPost.mutate(item.id)}
                              disabled={cancelPost.isPending}
                            >
                              <Trash2 className="w-3 h-3 mr-1" />
                              Cancel
                            </Button>
                          )}
                          {item.post_url && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => window.open(item.post_url, '_blank')}
                            >
                              <ExternalLink className="w-3 h-3 mr-1" />
                              View
                            </Button>
                          )}
                        </div>
                        {item.error_message && (
                          <div className="text-xs text-red-600 mt-1 max-w-[200px] truncate" title={item.error_message}>
                            {item.error_message}
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default PostingQueue;
