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
  ArrowDownRight
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

const Analytics = () => {
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

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="p-6 bg-card border-border">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-muted-foreground">Total Clips</p>
            <BarChart3 className="w-5 h-5 text-primary" />
          </div>
          <p className="text-3xl font-bold mb-2">1,284</p>
          <div className="flex items-center gap-1 text-sm text-success">
            <ArrowUpRight className="w-4 h-4" />
            <span>+23% vs last period</span>
          </div>
        </Card>

        <Card className="p-6 bg-card border-border">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-muted-foreground">Avg AI Score</p>
            <Star className="w-5 h-5 text-warning" />
          </div>
          <div className="flex items-baseline gap-2 mb-2">
            <p className="text-3xl font-bold">0.58</p>
            <div className="flex gap-0.5">
              {[1, 2, 3, 4].map((i) => (
                <Star key={i} className="w-3 h-3 fill-score-green text-score-green" />
              ))}
              <Star className="w-3 h-3 text-muted" />
            </div>
          </div>
          <div className="flex items-center gap-1 text-sm text-success">
            <ArrowUpRight className="w-4 h-4" />
            <span>+0.08</span>
          </div>
        </Card>

        <Card className="p-6 bg-card border-border">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-muted-foreground">Storage Used</p>
            <TrendingUp className="w-5 h-5 text-info" />
          </div>
          <p className="text-3xl font-bold mb-2">48.2 GB</p>
          <div className="w-full bg-muted rounded-full h-2 mb-2">
            <div 
              className="h-full rounded-full bg-gradient-to-r from-primary to-pink-500"
              style={{ width: '48%' }}
            />
          </div>
          <p className="text-xs text-muted-foreground">of 100 GB</p>
        </Card>

        <Card className="p-6 bg-card border-border">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-muted-foreground">Avg Duration</p>
            <Clock className="w-5 h-5 text-success" />
          </div>
          <p className="text-3xl font-bold mb-2">28.4s</p>
          <div className="flex items-center gap-1 text-sm text-destructive">
            <ArrowDownRight className="w-4 h-4" />
            <span>-2.1s vs last period</span>
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

        {/* Channel Breakdown */}
        <Card className="p-6 bg-card border-border">
          <h3 className="text-lg font-semibold mb-6">Top Channels</h3>
          <div className="space-y-4">
            {[
              { name: "nater4l", clips: 487, score: 0.68, growth: 23 },
              { name: "jordanbentley", clips: 356, score: 0.54, growth: 15 },
              { name: "stableronaldo", clips: 298, score: 0.62, growth: -5 },
              { name: "asspizza730", clips: 143, score: 0.45, growth: 8 },
            ].map((channel) => (
              <div key={channel.name} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Avatar className="w-10 h-10">
                    <AvatarImage src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${channel.name}`} />
                    <AvatarFallback>{channel.name[0]}</AvatarFallback>
                  </Avatar>
                  <div>
                    <p className="font-semibold text-foreground">{channel.name}</p>
                    <p className="text-xs text-muted-foreground">{channel.clips} clips</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold text-score-green">{channel.score.toFixed(2)}</p>
                  <p className={`text-xs ${channel.growth > 0 ? 'text-success' : 'text-destructive'}`}>
                    {channel.growth > 0 ? '+' : ''}{channel.growth}%
                  </p>
                </div>
              </div>
            ))}
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
              {[
                { name: "nater4l", clips: 487, score: 0.68, storage: 15.2, active: "2m ago", status: "active" },
                { name: "jordanbentley", clips: 356, score: 0.54, storage: 12.8, active: "5m ago", status: "active" },
                { name: "stableronaldo", clips: 298, score: 0.62, storage: 9.4, active: "1h ago", status: "paused" },
              ].map((channel, i) => (
                <tr key={channel.name} className={`border-b border-border hover:bg-muted/50 ${i % 2 === 0 ? 'bg-muted/20' : ''}`}>
                  <td className="py-4 px-4">
                    <div className="flex items-center gap-3">
                      <Avatar className="w-8 h-8">
                        <AvatarImage src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${channel.name}`} />
                        <AvatarFallback>{channel.name[0]}</AvatarFallback>
                      </Avatar>
                      <span className="font-medium">{channel.name}</span>
                    </div>
                  </td>
                  <td className="py-4 px-4 font-bold">{channel.clips}</td>
                  <td className="py-4 px-4">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-score-green">{channel.score.toFixed(2)}</span>
                      <div className="flex gap-0.5">
                        {[...Array(4)].map((_, i) => (
                          <Star key={i} className="w-3 h-3 fill-score-green text-score-green" />
                        ))}
                      </div>
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <div className="w-24 bg-muted rounded-full h-2">
                      <div className="h-full bg-primary rounded-full" style={{ width: `${(channel.storage / 20) * 100}%` }} />
                    </div>
                    <span className="text-xs text-muted-foreground mt-1">{channel.storage} GB</span>
                  </td>
                  <td className="py-4 px-4 text-sm text-muted-foreground">{channel.active}</td>
                  <td className="py-4 px-4">
                    <Badge className={channel.status === "active" ? "bg-success/10 text-success" : "bg-muted text-muted-foreground"}>
                      {channel.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};

export default Analytics;
