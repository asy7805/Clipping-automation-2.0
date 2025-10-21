import { Card } from "@/components/ui/card";
import { useClips } from "@/hooks/useClips";
import { Loader2 } from "lucide-react";

const getActivityIcon = (score: number) => {
  if (score >= 0.7) return "🎉";
  if (score >= 0.5) return "⬆️";
  return "📹";
};

const getActivityColor = (score: number) => {
  if (score >= 0.7) return "text-success";
  if (score >= 0.5) return "text-primary";
  return "text-info";
};

const getTimeAgo = (dateString: string) => {
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

export const ActivityFeed = () => {
  const { data: clips, isLoading } = useClips({ limit: 10 });

  // Transform clips to activity format
  const activities = clips?.map(clip => ({
    icon: getActivityIcon(clip.confidence_score),
    message: clip.confidence_score >= 0.7
      ? `${clip.channel_name}: High-score clip captured (${clip.confidence_score.toFixed(2)})`
      : `${clip.channel_name}: Clip uploaded (${clip.confidence_score.toFixed(2)})`,
    time: getTimeAgo(clip.created_at),
    color: getActivityColor(clip.confidence_score)
  })) || [];
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">📊 Live Activity</h2>
      <Card className="p-4 bg-card border-border">
        {isLoading ? (
          <div className="flex items-center justify-center h-40">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
          </div>
        ) : activities.length === 0 ? (
          <div className="flex items-center justify-center h-40">
            <p className="text-sm text-muted-foreground">No recent activity</p>
          </div>
        ) : (
          <div className="space-y-4">
            {activities.map((activity, index) => (
              <div 
                key={index} 
                className="flex items-start gap-3 pb-4 border-b border-border last:border-0 last:pb-0 animate-in fade-in slide-in-from-right-2"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <span className="text-xl">{activity.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm ${activity.color} font-medium`}>
                    {activity.message}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">{activity.time}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};
