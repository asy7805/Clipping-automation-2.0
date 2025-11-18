import { useState, useEffect, useRef } from "react";
import { Bell, Film, Play, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useClips } from "@/hooks/useClips";
import { useStreams } from "@/hooks/useStreamData";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";

interface Notification {
  id: string;
  type: "clip" | "monitor";
  message: string;
  timestamp: Date;
  channel_name?: string;
  clip_id?: string;
}

export const NotificationDropdown = () => {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const lastClipIdRef = useRef<string | null>(null);
  const lastMonitorIdsRef = useRef<Set<string>>(new Set());

  // Fetch clips and monitors
  const { data: clipsData } = useClips({ 
    limit: 10, 
    sort_by: "newest",
    refetchInterval: 10000 // Poll every 10 seconds
  });
  
  const { data: streamsData } = useStreams();

  const clips = clipsData?.clips || [];
  const monitors = streamsData || [];

  // Track new clips
  useEffect(() => {
    if (clips.length > 0) {
      const latestClip = clips[0];
      const latestClipId = latestClip.id;

      // Check if this is a new clip we haven't seen
      if (lastClipIdRef.current === null) {
        // First load - set initial state
        lastClipIdRef.current = latestClipId;
      } else if (latestClipId !== lastClipIdRef.current) {
        // New clip detected!
        const newNotification: Notification = {
          id: `clip-${latestClipId}`,
          type: "clip",
          message: `New clip captured from ${latestClip.channel_name}`,
          timestamp: new Date(latestClip.created_at),
          channel_name: latestClip.channel_name,
          clip_id: latestClipId,
        };

        setNotifications((prev) => [newNotification, ...prev].slice(0, 50)); // Keep last 50
        setUnreadCount((prev) => prev + 1);
        lastClipIdRef.current = latestClipId;
      }
    }
  }, [clips]);

  // Track new monitors
  useEffect(() => {
    const currentMonitorIds = new Set(monitors.map(m => m.id));

    // Find new monitors (in current but not in last)
    const newMonitorIds = [...currentMonitorIds].filter(id => !lastMonitorIdsRef.current.has(id));

    if (newMonitorIds.length > 0) {
      // New monitors detected!
      newMonitorIds.forEach((monitorId) => {
        const monitor = monitors.find(m => m.id === monitorId);
        if (monitor) {
          const newNotification: Notification = {
            id: `monitor-${monitorId}-${Date.now()}`,
            type: "monitor",
            message: `Started monitoring ${monitor.channel}`,
            timestamp: new Date(),
            channel_name: monitor.channel,
          };

          setNotifications((prev) => [newNotification, ...prev].slice(0, 50));
          setUnreadCount((prev) => prev + 1);
        }
      });

      // Update tracked IDs
      lastMonitorIdsRef.current = currentMonitorIds;
    } else if (lastMonitorIdsRef.current.size === 0) {
      // First load - initialize with current monitors
      lastMonitorIdsRef.current = currentMonitorIds;
    } else {
      // Update tracked IDs (monitors may have been removed)
      lastMonitorIdsRef.current = currentMonitorIds;
    }
  }, [monitors]);

  const handleNotificationClick = (notification: Notification) => {
    if (notification.type === "clip" && notification.clip_id) {
      navigate(`/dashboard/clips?highlight=${notification.clip_id}`);
    } else if (notification.type === "monitor") {
      navigate("/dashboard");
    }
    
    // Mark as read
    setUnreadCount((prev) => Math.max(0, prev - 1));
  };

  const handleMarkAllRead = () => {
    setNotifications([]);
    setUnreadCount(0);
  };

  const handleRemoveNotification = (notificationId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent triggering the click handler
    setNotifications((prev) => prev.filter(n => n.id !== notificationId));
    setUnreadCount((prev) => Math.max(0, prev - 1));
  };

  const formatTimeAgo = (date: Date) => {
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

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="relative"
        >
          <Bell className="w-5 h-5" />
          {unreadCount > 0 && (
            <Badge 
              className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs bg-primary text-primary-foreground"
            >
              {unreadCount > 9 ? '9+' : unreadCount}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 p-0">
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-sm">Notifications</h3>
            {notifications.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleMarkAllRead}
                className="h-6 px-2 text-xs"
              >
                Mark all read
              </Button>
            )}
          </div>
        </div>
        
        <ScrollArea className="h-[400px]">
          {notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
              <Bell className="w-12 h-12 text-muted-foreground/50 mb-2" />
              <p className="text-sm text-muted-foreground">No notifications</p>
              <p className="text-xs text-muted-foreground mt-1">
                New clips and monitors will appear here
              </p>
            </div>
          ) : (
            <div className="p-2">
              {notifications.map((notification) => (
                <div
                  key={notification.id}
                  onClick={() => handleNotificationClick(notification)}
                  className={cn(
                    "flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors group",
                    "hover:bg-muted/50 border border-transparent hover:border-border"
                  )}
                >
                  <div className={cn(
                    "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
                    notification.type === "clip" 
                      ? "bg-primary/10 text-primary" 
                      : "bg-success/10 text-success"
                  )}>
                    {notification.type === "clip" ? (
                      <Film className="w-4 h-4" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground">
                      {notification.message}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatTimeAgo(notification.timestamp)}
                    </p>
                  </div>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => handleRemoveNotification(notification.id, e)}
                    className={cn(
                      "h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity",
                      "hover:bg-destructive/10 hover:text-destructive"
                    )}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

