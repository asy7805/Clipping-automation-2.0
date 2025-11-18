import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  ExternalLink,
  RefreshCw,
  Bell,
  BellOff
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { toast } from "sonner";

interface Notification {
  id: string;
  clip_id: string;
  status: 'posted' | 'failed';
  platform: string;
  account_name: string;
  post_url?: string;
  caption?: string;
  error_message?: string;
  posted_at?: string;
  created_at: string;
}

interface NotificationCenterProps {
  isOpen: boolean;
  onClose: () => void;
}

const NotificationCenter: React.FC<NotificationCenterProps> = ({ isOpen, onClose }) => {
  const [isEnabled, setIsEnabled] = useState(true);

  // Fetch notifications
  const { data: notificationsData, isLoading, refetch } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => apiClient.getNotifications(),
    enabled: isOpen && isEnabled,
    refetchInterval: 10000, // Poll every 10 seconds when open
  });

  const notifications = notificationsData?.notifications || [];

  // Show toast notifications for new posts
  useEffect(() => {
    if (notifications.length > 0) {
      const latestNotification = notifications[0];
      const isRecent = new Date(latestNotification.created_at).getTime() > Date.now() - 30000; // Last 30 seconds
      
      if (isRecent && latestNotification.status === 'posted') {
        toast.success(
          `✅ Posted to ${latestNotification.platform}: @${latestNotification.account_name}`,
          {
            description: latestNotification.caption || 'Your clip has been posted successfully!',
            action: latestNotification.post_url ? {
              label: "View Post",
              onClick: () => window.open(latestNotification.post_url, '_blank')
            } : undefined,
            duration: 8000,
          }
        );
      } else if (isRecent && latestNotification.status === 'failed') {
        toast.error(
          `❌ Failed to post to ${latestNotification.platform}: @${latestNotification.account_name}`,
          {
            description: latestNotification.error_message || 'There was an error posting your clip.',
            duration: 10000,
          }
        );
      }
    }
  }, [notifications]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'posted':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-yellow-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'posted':
        return <Badge variant="default" className="bg-green-500">Posted</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="secondary">Pending</Badge>;
    }
  };

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'youtube':
        return '📺';
      case 'tiktok':
        return '🎵';
      default:
        return '🔗';
    }
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <Card className="w-full max-w-2xl max-h-[80vh] mx-4">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Bell className="w-5 h-5" />
              Posting Notifications
            </CardTitle>
            <CardDescription>
              Recent social media posting activity
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsEnabled(!isEnabled)}
            >
              {isEnabled ? <Bell className="w-4 h-4 mr-2" /> : <BellOff className="w-4 h-4 mr-2" />}
              {isEnabled ? 'Enabled' : 'Disabled'}
            </Button>
            <Button variant="outline" size="sm" onClick={refetch}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            <Button variant="outline" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[400px] w-full">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                <span className="ml-2">Loading notifications...</span>
              </div>
            ) : notifications.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Bell className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No recent notifications</p>
                <p className="text-sm">Your posting activity will appear here</p>
              </div>
            ) : (
              <div className="space-y-3">
                {notifications.map((notification: Notification) => (
                  <div
                    key={notification.id}
                    className="flex items-start gap-3 p-3 rounded-lg border bg-card"
                  >
                    <div className="flex-shrink-0">
                      {getStatusIcon(notification.status)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-lg">
                          {getPlatformIcon(notification.platform)}
                        </span>
                        <span className="font-medium text-sm">
                          @{notification.account_name}
                        </span>
                        {getStatusBadge(notification.status)}
                      </div>
                      
                      {notification.caption && (
                        <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
                          "{notification.caption}"
                        </p>
                      )}
                      
                      {notification.status === 'failed' && notification.error_message && (
                        <p className="text-sm text-red-600 mb-2">
                          Error: {notification.error_message}
                        </p>
                      )}
                      
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">
                          {formatTimeAgo(notification.created_at)}
                        </span>
                        
                        {notification.post_url && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => window.open(notification.post_url, '_blank')}
                            className="h-6 px-2 text-xs"
                          >
                            <ExternalLink className="w-3 h-3 mr-1" />
                            View Post
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
};

export default NotificationCenter;
