import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  BarChart3, 
  TrendingUp, 
  Clock, 
  Star,
  ChevronDown,
  ArrowUpRight,
  ArrowDownRight,
  Loader2
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useAnalytics } from "@/hooks/useAnalytics";
import { getChannelAvatarProps } from "@/lib/avatarUtils";

const Analytics = () => {
  const { data: analytics, isLoading } = useAnalytics();

  if (isLoading || !analytics) {
    return (
      <div className="container mx-auto px-6 py-8 flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }
  return (
    <div className="container mx-auto px-6 py-8 space-y-8">
      {/* Time Period Selector */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">📈 Analytics</h1>
        <Tabs defaultValue="7d">
          <TabsList>
            <TabsTrigger value="24h">24h</TabsTrigger>
            <TabsTrigger value="7d">7 Days</TabsTrigger>
            <TabsTrigger value="30d">30 Days</TabsTrigger>
            <TabsTrigger value="all">All Time</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* KPI Cards - Real Data */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="p-6 bg-card border-border">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-muted-foreground">Total Clips</p>
            <BarChart3 className="w-5 h-5 text-primary" />
          </div>
          <p className="text-3xl font-bold mb-2">{analytics.totalClips.toLocaleString()}</p>
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <span>All time</span>
          </div>
        </Card>

        <Card className="p-6 bg-card border-border">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-muted-foreground">Avg AI Score</p>
            <Star className="w-5 h-5 text-warning" />
          </div>
          <div className="flex items-baseline gap-2 mb-2">
            <p className="text-3xl font-bold">{analytics.avgScore.toFixed(2)}</p>
            <div className="flex gap-0.5">
              {[1, 2, 3, 4, 5].map((i) => (
                <Star 
                  key={i} 
                  className={`w-3 h-3 ${
                    i <= Math.round(analytics.avgScore * 5) 
                      ? 'fill-score-green text-score-green' 
                      : 'text-muted'
                  }`}
                />
              ))}
            </div>
          </div>
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <span>{analytics.highScoreClips} high-score clips</span>
          </div>
        </Card>

        <Card className="p-6 bg-card border-border">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-muted-foreground">Storage Used</p>
            <TrendingUp className="w-5 h-5 text-info" />
          </div>
          <p className="text-3xl font-bold mb-2">{analytics.storageUsedGB.toFixed(2)} GB</p>
          <div className="w-full bg-muted rounded-full h-2 mb-2">
            <div 
              className="h-full rounded-full bg-gradient-to-r from-primary to-pink-500"
              style={{ width: `${Math.min(100, (analytics.storageUsedGB / 10) * 100)}%` }}
            />
          </div>
          <p className="text-xs text-muted-foreground">of 10 GB quota</p>
        </Card>

        <Card className="p-6 bg-card border-border">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-muted-foreground">Channels</p>
            <Clock className="w-5 h-5 text-success" />
          </div>
          <p className="text-3xl font-bold mb-2">{analytics.topChannels.length}</p>
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <span>Monitored streamers</span>
          </div>
        </Card>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Clips Over Time */}
        <Card className="p-6 bg-card border-border col-span-2">
          <h3 className="text-lg font-semibold mb-6">Clips Over Time</h3>
          <div className="h-64 flex items-end justify-between gap-2">
            {[42, 58, 45, 72, 88, 65, 93, 78, 95, 82, 110, 98, 115, 102].map((height, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-2">
                <div 
                  className="w-full bg-gradient-to-t from-primary to-pink-500 rounded-t-sm hover:opacity-80 transition-opacity cursor-pointer"
                  style={{ height: `${height}%` }}
                />
                <span className="text-xs text-muted-foreground">
                  {i % 2 === 0 ? `${i + 1}` : ''}
                </span>
              </div>
            ))}
          </div>
        </Card>

        {/* Score Distribution */}
        <Card className="p-6 bg-card border-border">
          <h3 className="text-lg font-semibold mb-6">Score Distribution</h3>
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground w-20">0.7-1.0</span>
              <div className="flex-1 bg-muted rounded-full h-8">
                <div className="h-full bg-score-gold rounded-full flex items-center justify-end pr-3" style={{ width: '85%' }}>
                  <span className="text-xs font-bold">142</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground w-20">0.5-0.69</span>
              <div className="flex-1 bg-muted rounded-full h-8">
                <div className="h-full bg-score-green rounded-full flex items-center justify-end pr-3" style={{ width: '65%' }}>
                  <span className="text-xs font-bold">298</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground w-20">0.3-0.49</span>
              <div className="flex-1 bg-muted rounded-full h-8">
                <div className="h-full bg-score-blue rounded-full flex items-center justify-end pr-3" style={{ width: '45%' }}>
                  <span className="text-xs font-bold">487</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground w-20">0.0-0.29</span>
              <div className="flex-1 bg-muted rounded-full h-8">
                <div className="h-full bg-score-gray rounded-full flex items-center justify-end pr-3" style={{ width: '25%' }}>
                  <span className="text-xs font-bold">357</span>
                </div>
              </div>
            </div>
          </div>
        </Card>

        {/* Channel Breakdown - Real Data */}
        <Card className="p-6 bg-card border-border">
          <h3 className="text-lg font-semibold mb-6">Top Channels</h3>
          <div className="space-y-4">
            {analytics.topChannels.map((channel) => {
              const { gradient, initials } = getChannelAvatarProps(channel.name);
              return (
              <div key={channel.name} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${gradient} flex items-center justify-center text-white font-bold text-sm`}>
                    {initials}
                  </div>
                  <div>
                    <p className="font-semibold text-foreground">{channel.name}</p>
                    <p className="text-xs text-muted-foreground">{channel.clips} clips</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold text-score-green">{channel.avgScore.toFixed(2)}</p>
                  <div className="flex gap-0.5 justify-end">
                    {[1,2,3,4,5].map((i) => (
                      <Star 
                        key={i}
                        className={`w-2.5 h-2.5 ${
                          i <= Math.round(channel.avgScore * 5)
                            ? 'fill-score-green text-score-green'
                            : 'text-muted'
                        }`}
                      />
                    ))}
                  </div>
                </div>
              </div>
            );
            })}
          </div>
        </Card>
      </div>

      {/* Performance Table */}
      <Card className="p-6 bg-card border-border">
        <h3 className="text-lg font-semibold mb-6">Channel Performance</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 text-sm font-semibold text-muted-foreground">Channel</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-muted-foreground">Total Clips</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-muted-foreground">Avg Score</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-muted-foreground">Storage</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-muted-foreground">Last Active</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-muted-foreground">Status</th>
              </tr>
            </thead>
            <tbody>
              {analytics.topChannels.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-muted-foreground">
                    No channels with clips yet. Start monitoring streams!
                  </td>
                </tr>
              ) : (
                analytics.topChannels.map((channel, i) => {
                  const { gradient, initials } = getChannelAvatarProps(channel.name);
                  return (
                <tr key={channel.name} className={`border-b border-border hover:bg-muted/50 ${i % 2 === 0 ? 'bg-muted/20' : ''}`}>
                  <td className="py-4 px-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-full bg-gradient-to-br ${gradient} flex items-center justify-center text-white font-bold text-xs`}>
                        {initials}
                      </div>
                      <span className="font-medium">{channel.name}</span>
                    </div>
                  </td>
                  <td className="py-4 px-4 font-bold">{channel.clips}</td>
                  <td className="py-4 px-4">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-score-green">{channel.avgScore.toFixed(2)}</span>
                      <div className="flex gap-0.5">
                        {[1,2,3,4,5].map((starNum) => (
                          <Star 
                            key={starNum} 
                            className={`w-3 h-3 ${
                              starNum <= Math.round(channel.avgScore * 5)
                                ? 'fill-score-green text-score-green'
                                : 'text-muted'
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <div className="w-24 bg-muted rounded-full h-2">
                      <div className="h-full bg-primary rounded-full" style={{ width: `${Math.min(100, (channel.clips * 0.01 / 0.2) * 100)}%` }} />
                    </div>
                    <span className="text-xs text-muted-foreground mt-1">{(channel.clips * 0.01).toFixed(1)} GB</span>
                  </td>
                  <td className="py-4 px-4 text-sm text-muted-foreground">Recently</td>
                  <td className="py-4 px-4">
                    <Badge className="bg-success/10 text-success">
                      active
                    </Badge>
                  </td>
                </tr>
              );
              }))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};

export default Analytics;
