import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { supabase } from "@/lib/supabase";
import { clampScore } from "@/lib/utils";
import { Navigate } from "react-router-dom";
import { Users, Video, Database, Activity, HardDrive, TrendingUp, Search, Shield, ShieldCheck, Trash2, RefreshCw, AlertCircle, Coins, Crown } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAdminCheck } from "@/hooks/useAdminCheck";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface AdminStats {
  total_users: number;
  total_clips: number;
  total_monitors: number;
  active_monitors: number;
  clips_today: number;
  clips_this_week: number;
  avg_clips_per_user: number;
  avg_score: number;
  storage_used_gb: number;
  new_users_this_week: number;
  user_growth?: Array<{ date: string; users: number }>;
  monitor_activity?: Array<{ date: string; active: number }>;
}

interface User {
  id: string;
  email: string;
  created_at: string;
  last_sign_in_at?: string;
  monitor_count?: number;
  clip_count?: number;
  subscription_tier?: string;
  credits_remaining?: number;
}

interface Clip {
  id: string;
  user_id: string;
  channel_name: string;
  confidence_score: number;
  created_at: string;
  storage_url: string;
  file_size?: number;
}

interface Monitor {
  id: string;
  user_id: string;
  channel_name: string;
  status: string;
  started_at: string;
  process_id?: number;
}

const Admin = () => {
  const queryClient = useQueryClient();
  const { data: adminCheck, isLoading: adminCheckLoading } = useAdminCheck();
  const isAdmin = adminCheck?.is_admin ?? false;

  // Pagination states
  const [usersPage, setUsersPage] = useState(0);
  const [clipsPage, setClipsPage] = useState(0);
  const [usersSearch, setUsersSearch] = useState("");
  const [clipsSearch, setClipsSearch] = useState("");
  const itemsPerPage = 20;
  
  // Credit and subscription management states
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [creditsDialogOpen, setCreditsDialogOpen] = useState(false);
  const [subscriptionDialogOpen, setSubscriptionDialogOpen] = useState(false);
  const [creditsAmount, setCreditsAmount] = useState("");
  const [creditsDescription, setCreditsDescription] = useState("");
  const [selectedTier, setSelectedTier] = useState<string>("free_trial");
  const [tierCredits, setTierCredits] = useState("");

  // Fetch admin stats
  const { data: stats, isLoading: statsLoading } = useQuery<AdminStats>({
    queryKey: ["admin-stats"],
    queryFn: async () => {
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/stats`, {
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
        },
      });
      if (!response.ok) throw new Error("Failed to fetch stats");
      return response.json();
    },
    enabled: isAdmin,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch all users with pagination
  const { data: usersData, isLoading: usersLoading } = useQuery<{ users: User[]; limit: number; offset: number; total?: number }>({
    queryKey: ["admin-users", usersPage],
    queryFn: async () => {
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/users?limit=${itemsPerPage}&offset=${usersPage * itemsPerPage}`, {
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
        },
      });
      if (!response.ok) {
        const errorText = await response.text().catch(() => response.statusText);
        throw new Error(`Failed to fetch users: ${errorText}`);
      }
      const data = await response.json();
      // Ensure all users have an id field and fetch subscription info
      if (data.users) {
        const usersWithSubscription = await Promise.all(
          data.users.map(async (u: any) => {
            const userId = u.id || u.user_id || u.uid || null;
            if (!userId) return { ...u, id: null };
            
            // Fetch subscription info for each user
            try {
              const subResponse = await fetch(`${API_BASE_URL}/api/v1/admin/users/${encodeURIComponent(userId)}/subscription`, {
                headers: {
                  Authorization: `Bearer ${session?.access_token}`,
                },
              });
              if (subResponse.ok) {
                const subData = await subResponse.json();
                return {
                  ...u,
                  id: userId,
                  subscription_tier: subData.tier,
                  credits_remaining: subData.credits_remaining,
                };
              }
            } catch (error) {
              console.warn(`Failed to fetch subscription for user ${userId}:`, error);
            }
            
            return {
              ...u,
              id: userId,
              subscription_tier: 'free_trial',
              credits_remaining: 0,
            };
          })
        );
        data.users = usersWithSubscription;
      }
      return data;
    },
    enabled: isAdmin,
  });

  // Fetch all clips with pagination
  const { data: clipsData, isLoading: clipsLoading } = useQuery<{ clips: Clip[]; limit: number; offset: number; total?: number }>({
    queryKey: ["admin-clips", clipsPage],
    queryFn: async () => {
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/clips?limit=${itemsPerPage}&offset=${clipsPage * itemsPerPage}`, {
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
        },
      });
      if (!response.ok) {
        const errorText = await response.text().catch(() => response.statusText);
        throw new Error(`Failed to fetch clips: ${errorText}`);
      }
      return response.json();
    },
    enabled: isAdmin,
  });

  // Fetch all monitors
  const { data: monitorsData, isLoading: monitorsLoading } = useQuery<{ monitors: Monitor[]; total: number }>({
    queryKey: ["admin-monitors"],
    queryFn: async () => {
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/monitors`, {
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
        },
      });
      if (!response.ok) throw new Error("Failed to fetch monitors");
      return response.json();
    },
    enabled: isAdmin,
    refetchInterval: 15000, // Refresh every 15 seconds
  });

  // Grant admin mutation
  const grantAdminMutation = useMutation({
    mutationFn: async (userId: string) => {
      if (!userId || userId === 'undefined') {
        throw new Error("Invalid user ID");
      }
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/admins/${encodeURIComponent(userId)}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
          "Content-Type": "application/json",
        },
      });
      if (!response.ok) {
        const errorText = await response.text().catch(() => response.statusText);
        throw new Error(errorText || "Failed to grant admin");
      }
      return response.json();
    },
    onSuccess: (data) => {
      toast.success(data.message || "Admin access granted");
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      queryClient.invalidateQueries({ queryKey: ["admin-check"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to grant admin access");
    },
  });

  // Revoke admin mutation
  const revokeAdminMutation = useMutation({
    mutationFn: async (userId: string) => {
      if (!userId || userId === 'undefined') {
        throw new Error("Invalid user ID");
      }
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/admins/${encodeURIComponent(userId)}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
        },
      });
      if (!response.ok) {
        const errorText = await response.text().catch(() => response.statusText);
        throw new Error(errorText || "Failed to revoke admin");
      }
      return response.json();
    },
    onSuccess: (data) => {
      toast.success(data.message || "Admin access revoked");
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      queryClient.invalidateQueries({ queryKey: ["admin-check"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to revoke admin access");
    },
  });

  // Delete clip mutation
  const deleteClipMutation = useMutation({
    mutationFn: async (clipId: string) => {
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/clips/${clipId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
        },
      });
      if (!response.ok) {
        const errorText = await response.text().catch(() => response.statusText);
        throw new Error(errorText || "Failed to delete clip");
      }
      return response.json();
    },
    onSuccess: (data) => {
      toast.success(data.message || "Clip deleted");
      queryClient.invalidateQueries({ queryKey: ["admin-clips"] });
      queryClient.invalidateQueries({ queryKey: ["clips"] });
      queryClient.invalidateQueries({ queryKey: ["admin-stats"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to delete clip");
    },
  });

  // Stop monitor mutation
  const stopMonitorMutation = useMutation({
    mutationFn: async (channelName: string) => {
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(`${API_BASE_URL}/api/v1/monitors/stop/${encodeURIComponent(channelName)}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
        },
      });
      if (!response.ok) {
        const errorText = await response.text().catch(() => response.statusText);
        throw new Error(errorText || "Failed to stop monitor");
      }
      return response.json();
    },
    onSuccess: (data) => {
      toast.success(data.message || "Monitor stopped");
      queryClient.invalidateQueries({ queryKey: ["admin-monitors"] });
      queryClient.invalidateQueries({ queryKey: ["streams"] });
      queryClient.invalidateQueries({ queryKey: ["admin-stats"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to stop monitor");
    },
  });

  // Add credits mutation
  const addCreditsMutation = useMutation({
    mutationFn: async ({ userId, amount, description }: { userId: string; amount: number; description?: string }) => {
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/users/${encodeURIComponent(userId)}/credits`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ amount, description }),
      });
      if (!response.ok) {
        const errorText = await response.text().catch(() => response.statusText);
        throw new Error(errorText || "Failed to add credits");
      }
      return response.json();
    },
    onSuccess: (data) => {
      toast.success(data.message || `Added ${data.credits_added} credits`);
      setCreditsDialogOpen(false);
      setCreditsAmount("");
      setCreditsDescription("");
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      // Also invalidate subscription queries so the user sees the update immediately
      queryClient.invalidateQueries({ queryKey: ["userSubscription"] });
      queryClient.invalidateQueries({ queryKey: ["subscription"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to add credits");
    },
  });

  // Update subscription tier mutation
  const updateSubscriptionMutation = useMutation({
    mutationFn: async ({ userId, tier, credits, expiresAt }: { userId: string; tier: string; credits?: number; expiresAt?: string }) => {
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/users/${encodeURIComponent(userId)}/subscription`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ tier, credits, expires_at: expiresAt }),
      });
      if (!response.ok) {
        const errorText = await response.text().catch(() => response.statusText);
        throw new Error(errorText || "Failed to update subscription");
      }
      return response.json();
    },
    onSuccess: (data) => {
      toast.success(data.message || `Subscription updated to ${data.tier}`);
      setSubscriptionDialogOpen(false);
      setSelectedTier("free_trial");
      setTierCredits("");
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      // Also invalidate subscription queries so the user sees the update immediately
      queryClient.invalidateQueries({ queryKey: ["userSubscription"] });
      queryClient.invalidateQueries({ queryKey: ["subscription"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to update subscription");
    },
  });

  // Filter users and clips by search
  const filteredUsers = (usersData?.users || []).filter((u) =>
    u.email?.toLowerCase().includes(usersSearch.toLowerCase()) ||
    u.id?.toLowerCase().includes(usersSearch.toLowerCase())
  );

  const filteredClips = (clipsData?.clips || []).filter((c) =>
    c.channel_name?.toLowerCase().includes(clipsSearch.toLowerCase()) ||
    c.user_id?.toLowerCase().includes(clipsSearch.toLowerCase())
  );

  // Prepare chart data
  const clipsChartData = [
    { name: "Today", clips: stats?.clips_today || 0 },
    { name: "This Week", clips: stats?.clips_this_week || 0 },
  ];

  // Prepare user growth chart data (last 7 days for better visibility)
  const userGrowthData = stats?.user_growth?.slice(-7).map(item => ({
    date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    users: item.users
  })) || [];

  // Prepare monitor activity chart data (last 7 days)
  const monitorActivityData = stats?.monitor_activity?.slice(-7).map(item => ({
    date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    active: item.active
  })) || [];

  // Loading state
  if (adminCheckLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Verifying admin access...</p>
        </div>
      </div>
    );
  }

  // Redirect if not admin
  if (!isAdmin) {
    toast.error("Access denied: Admin privileges required");
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Admin Dashboard</h1>
        <p className="text-muted-foreground">System overview and management</p>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <>
                <div className="text-2xl font-bold">{stats?.total_users || 0}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {stats?.new_users_this_week || 0} new this week
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Clips</CardTitle>
            <Video className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <>
                <div className="text-2xl font-bold">{stats?.total_clips || 0}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {stats?.clips_today || 0} today • {stats?.clips_this_week || 0} this week
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Monitors</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <>
                <div className="text-2xl font-bold">
                  {stats?.active_monitors || 0} / {stats?.total_monitors || 0}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {stats?.avg_clips_per_user?.toFixed(1) || 0} clips/user avg
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Storage Used</CardTitle>
            <HardDrive className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <>
                <div className="text-2xl font-bold">{stats?.storage_used_gb?.toFixed(2) || "0.00"} GB</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Avg score: {stats?.avg_score?.toFixed(2) || "0.00"}
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>User Growth</CardTitle>
            <CardDescription>Total users over the last 7 days</CardDescription>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : userGrowthData.length === 0 ? (
              <div className="flex items-center justify-center h-64 text-muted-foreground">
                No data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={userGrowthData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="date" 
                    label={{ value: 'Date', position: 'insideBottom', offset: -5 }}
                  />
                  <YAxis 
                    label={{ value: 'Users', angle: -90, position: 'insideLeft' }}
                  />
                  <Tooltip />
                  <Line type="monotone" dataKey="users" stroke="hsl(var(--primary))" strokeWidth={2} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Active Monitors</CardTitle>
            <CardDescription>Active monitors over the last 7 days</CardDescription>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : monitorActivityData.length === 0 ? (
              <div className="flex items-center justify-center h-64 text-muted-foreground">
                No data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={monitorActivityData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="date" 
                    label={{ value: 'Date', position: 'insideBottom', offset: -5 }}
                  />
                  <YAxis 
                    label={{ value: 'Active Monitors', angle: -90, position: 'insideLeft' }}
                  />
                  <Tooltip />
                  <Line type="monotone" dataKey="active" stroke="hsl(var(--primary))" strokeWidth={2} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Additional Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Clips Activity</CardTitle>
            <CardDescription>Recent clip creation</CardDescription>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={clipsChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="name" 
                    label={{ value: 'Period', position: 'insideBottom', offset: -5 }}
                  />
                  <YAxis 
                    label={{ value: 'Clips', angle: -90, position: 'insideLeft' }}
                  />
                  <Tooltip />
                  <Bar dataKey="clips" fill="hsl(var(--primary))" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>System Health</CardTitle>
            <CardDescription>Monitor status overview</CardDescription>
          </CardHeader>
          <CardContent>
            {monitorsLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Active</span>
                  <Badge variant="default">
                    {monitorsData?.monitors?.filter((m) => m.status === "running").length || 0}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Stopped</span>
                  <Badge variant="secondary">
                    {monitorsData?.monitors?.filter((m) => m.status === "stopped").length || 0}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Total</span>
                  <Badge variant="outline">
                    {monitorsData?.total || 0}
                  </Badge>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Detailed Views */}
      <Tabs defaultValue="users" className="w-full">
        <TabsList>
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="clips">All Clips</TabsTrigger>
          <TabsTrigger value="monitors">Monitors</TabsTrigger>
        </TabsList>

        <TabsContent value="users" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>All Users</CardTitle>
              <CardDescription>Registered users in the system</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mb-4">
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search users..."
                    value={usersSearch}
                    onChange={(e) => setUsersSearch(e.target.value)}
                    className="pl-8"
                  />
                </div>
              </div>
              {usersLoading ? (
                <div className="space-y-2">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={`user-skeleton-${i}`} className="h-16 w-full" />
                  ))}
                </div>
              ) : filteredUsers.length === 0 ? (
                <div className="text-center py-8">
                  <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">No users found</p>
                </div>
              ) : (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Email</TableHead>
                        <TableHead>User ID</TableHead>
                        <TableHead>Tier</TableHead>
                        <TableHead>Credits</TableHead>
                        <TableHead>Joined</TableHead>
                        <TableHead>Last Login</TableHead>
                        <TableHead>Monitors</TableHead>
                        <TableHead>Clips</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredUsers.map((u, index) => (
                        <TableRow key={u.id || `user-${index}`}>
                          <TableCell className="font-medium">{u.email || 'Unknown'}</TableCell>
                          <TableCell className="font-mono text-xs">{u.id?.slice(0, 8)}...</TableCell>
                          <TableCell>
                            <Badge variant={u.subscription_tier === 'pro' ? 'default' : u.subscription_tier === 'free_trial' ? 'secondary' : 'outline'}>
                              {u.subscription_tier || 'free_trial'}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-mono">{u.credits_remaining ?? 'N/A'}</TableCell>
                          <TableCell>{u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A'}</TableCell>
                          <TableCell>{u.last_sign_in_at ? new Date(u.last_sign_in_at).toLocaleDateString() : 'Never'}</TableCell>
                          <TableCell>{u.monitor_count || 0}</TableCell>
                          <TableCell>{u.clip_count || 0}</TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-2 flex-wrap">
                              <Dialog open={creditsDialogOpen && selectedUser?.id === u.id} onOpenChange={(open) => {
                                setCreditsDialogOpen(open);
                                if (!open) {
                                  setSelectedUser(null);
                                  setCreditsAmount("");
                                  setCreditsDescription("");
                                }
                              }}>
                                <DialogTrigger asChild>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => {
                                      setSelectedUser(u);
                                      setCreditsDialogOpen(true);
                                    }}
                                    disabled={!u.id || u.id === 'undefined' || u.id === 'null'}
                                  >
                                    <Coins className="h-4 w-4 mr-1" />
                                    Credits
                                  </Button>
                                </DialogTrigger>
                                <DialogContent>
                                  <DialogHeader>
                                    <DialogTitle>Add Credits</DialogTitle>
                                    <DialogDescription>
                                      Add credits to {u.email || u.id?.slice(0, 8)}... account
                                    </DialogDescription>
                                  </DialogHeader>
                                  <div className="space-y-4 py-4">
                                    <div className="space-y-2">
                                      <Label htmlFor="credits-amount">Amount</Label>
                                      <Input
                                        id="credits-amount"
                                        type="number"
                                        min="1"
                                        placeholder="Enter credit amount"
                                        value={creditsAmount}
                                        onChange={(e) => setCreditsAmount(e.target.value)}
                                      />
                                    </div>
                                    <div className="space-y-2">
                                      <Label htmlFor="credits-description">Description (Optional)</Label>
                                      <Input
                                        id="credits-description"
                                        placeholder="Reason for credit grant"
                                        value={creditsDescription}
                                        onChange={(e) => setCreditsDescription(e.target.value)}
                                      />
                                    </div>
                                  </div>
                                  <DialogFooter>
                                    <Button variant="outline" onClick={() => {
                                      setCreditsDialogOpen(false);
                                      setSelectedUser(null);
                                      setCreditsAmount("");
                                      setCreditsDescription("");
                                    }}>
                                      Cancel
                                    </Button>
                                    <Button
                                      onClick={() => {
                                        if (!u.id || !creditsAmount || parseInt(creditsAmount) <= 0) {
                                          toast.error("Please enter a valid credit amount");
                                          return;
                                        }
                                        addCreditsMutation.mutate({
                                          userId: u.id,
                                          amount: parseInt(creditsAmount),
                                          description: creditsDescription || undefined
                                        });
                                      }}
                                      disabled={addCreditsMutation.isPending || !creditsAmount || parseInt(creditsAmount) <= 0}
                                    >
                                      {addCreditsMutation.isPending ? "Adding..." : "Add Credits"}
                                    </Button>
                                  </DialogFooter>
                                </DialogContent>
                              </Dialog>
                              
                              <Dialog open={subscriptionDialogOpen && selectedUser?.id === u.id} onOpenChange={(open) => {
                                setSubscriptionDialogOpen(open);
                                if (!open) {
                                  setSelectedUser(null);
                                  setSelectedTier("free_trial");
                                  setTierCredits("");
                                }
                              }}>
                                <DialogTrigger asChild>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => {
                                      setSelectedUser(u);
                                      setSelectedTier(u.subscription_tier || 'free_trial');
                                      setSubscriptionDialogOpen(true);
                                    }}
                                    disabled={!u.id || u.id === 'undefined' || u.id === 'null'}
                                  >
                                    <Crown className="h-4 w-4 mr-1" />
                                    Tier
                                  </Button>
                                </DialogTrigger>
                                <DialogContent>
                                  <DialogHeader>
                                    <DialogTitle>Update Subscription Tier</DialogTitle>
                                    <DialogDescription>
                                      Change subscription tier for {u.email || u.id?.slice(0, 8)}...
                                    </DialogDescription>
                                  </DialogHeader>
                                  <div className="space-y-4 py-4">
                                    <div className="space-y-2">
                                      <Label htmlFor="subscription-tier">Subscription Tier</Label>
                                      <Select value={selectedTier} onValueChange={setSelectedTier}>
                                        <SelectTrigger id="subscription-tier">
                                          <SelectValue placeholder="Select tier" />
                                        </SelectTrigger>
                                        <SelectContent>
                                          <SelectItem value="free_trial">Free Trial</SelectItem>
                                          <SelectItem value="pro">Pro</SelectItem>
                                          <SelectItem value="pay_as_you_go">Pay As You Go</SelectItem>
                                          <SelectItem value="expired">Expired</SelectItem>
                                        </SelectContent>
                                      </Select>
                                    </div>
                                    <div className="space-y-2">
                                      <Label htmlFor="tier-credits">Credits (Optional - defaults based on tier)</Label>
                                      <Input
                                        id="tier-credits"
                                        type="number"
                                        min="0"
                                        placeholder="Leave empty for default"
                                        value={tierCredits}
                                        onChange={(e) => setTierCredits(e.target.value)}
                                      />
                                      <p className="text-xs text-muted-foreground">
                                        Defaults: Free Trial = 20, Pro = 150, Pay As You Go = 0, Expired = 0
                                      </p>
                                    </div>
                                  </div>
                                  <DialogFooter>
                                    <Button variant="outline" onClick={() => {
                                      setSubscriptionDialogOpen(false);
                                      setSelectedUser(null);
                                      setSelectedTier("free_trial");
                                      setTierCredits("");
                                    }}>
                                      Cancel
                                    </Button>
                                    <Button
                                      onClick={() => {
                                        if (!u.id) {
                                          toast.error("Invalid user ID");
                                          return;
                                        }
                                        updateSubscriptionMutation.mutate({
                                          userId: u.id,
                                          tier: selectedTier,
                                          credits: tierCredits ? parseInt(tierCredits) : undefined
                                        });
                                      }}
                                      disabled={updateSubscriptionMutation.isPending}
                                    >
                                      {updateSubscriptionMutation.isPending ? "Updating..." : "Update Tier"}
                                    </Button>
                                  </DialogFooter>
                                </DialogContent>
                              </Dialog>
                              
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  const userId = u.id;
                                  console.log("Grant Admin clicked for user:", u, "ID:", userId);
                                  if (!userId || userId === 'undefined' || userId === 'null') {
                                    toast.error("User ID is missing or invalid");
                                    console.error("Invalid user ID:", userId);
                                    return;
                                  }
                                  console.log("Calling grantAdminMutation with ID:", userId);
                                  grantAdminMutation.mutate(userId);
                                }}
                                disabled={grantAdminMutation.isPending || !u.id || u.id === 'undefined' || u.id === 'null'}
                              >
                                <Shield className="h-4 w-4 mr-1" />
                                Grant Admin
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  const userId = u.id;
                                  console.log("Revoke Admin clicked for user:", u, "ID:", userId);
                                  if (!userId || userId === 'undefined' || userId === 'null') {
                                    toast.error("User ID is missing or invalid");
                                    console.error("Invalid user ID:", userId);
                                    return;
                                  }
                                  console.log("Calling revokeAdminMutation with ID:", userId);
                                  revokeAdminMutation.mutate(userId);
                                }}
                                disabled={revokeAdminMutation.isPending || !u.id || u.id === 'undefined' || u.id === 'null'}
                              >
                                <ShieldCheck className="h-4 w-4 mr-1" />
                                Revoke
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  <div className="flex items-center justify-between mt-4">
                    <p className="text-sm text-muted-foreground">
                      Showing {filteredUsers.length} of {usersData?.users.length || 0} users
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setUsersPage((p) => Math.max(0, p - 1))}
                        disabled={usersPage === 0 || usersLoading}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setUsersPage((p) => p + 1)}
                        disabled={filteredUsers.length < itemsPerPage || usersLoading || (usersData?.users.length || 0) < itemsPerPage}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="clips" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>All Clips</CardTitle>
              <CardDescription>Recent clips from all users</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mb-4">
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search clips..."
                    value={clipsSearch}
                    onChange={(e) => setClipsSearch(e.target.value)}
                    className="pl-8"
                  />
                </div>
              </div>
              {clipsLoading ? (
                <div className="space-y-2">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={`clip-skeleton-${i}`} className="h-16 w-full" />
                  ))}
                </div>
              ) : filteredClips.length === 0 ? (
                <div className="text-center py-8">
                  <Video className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">No clips found</p>
                </div>
              ) : (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Channel</TableHead>
                        <TableHead>User ID</TableHead>
                        <TableHead>Created</TableHead>
                        <TableHead>Score</TableHead>
                        <TableHead>Size</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredClips.map((clip, index) => (
                        <TableRow key={clip.id || `clip-${index}`}>
                          <TableCell className="font-medium">{clip.channel_name || 'Unknown'}</TableCell>
                          <TableCell className="font-mono text-xs">{clip.user_id?.slice(0, 8)}...</TableCell>
                          <TableCell>{clip.created_at ? new Date(clip.created_at).toLocaleDateString() : 'N/A'}</TableCell>
                          <TableCell>
                            <Badge
                              variant={clampScore(clip.confidence_score) >= 0.7 ? "default" : clampScore(clip.confidence_score) >= 0.5 ? "secondary" : "outline"}
                            >
                              {clampScore(clip.confidence_score).toFixed(2)}
                            </Badge>
                          </TableCell>
                          <TableCell>{clip.file_size ? `${(clip.file_size / 1024 / 1024).toFixed(2)} MB` : 'N/A'}</TableCell>
                          <TableCell className="text-right">
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  disabled={deleteClipMutation.isPending}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>Delete Clip</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    Are you sure you want to delete this clip from {clip.channel_name}? This action cannot be undone.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                                  <AlertDialogAction
                                    onClick={() => deleteClipMutation.mutate(clip.id)}
                                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                  >
                                    Delete
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  <div className="flex items-center justify-between mt-4">
                    <p className="text-sm text-muted-foreground">
                      Showing {filteredClips.length} of {clipsData?.clips.length || 0} clips
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setClipsPage((p) => Math.max(0, p - 1))}
                        disabled={clipsPage === 0 || clipsLoading}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setClipsPage((p) => p + 1)}
                        disabled={filteredClips.length < itemsPerPage || clipsLoading || (clipsData?.clips.length || 0) < itemsPerPage}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="monitors" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>All Monitors</CardTitle>
              <CardDescription>Active monitoring processes across all users</CardDescription>
            </CardHeader>
            <CardContent>
              {monitorsLoading ? (
                <div className="space-y-2">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={`monitor-skeleton-${i}`} className="h-16 w-full" />
                  ))}
                </div>
              ) : !monitorsData?.monitors || monitorsData.monitors.length === 0 ? (
                <div className="text-center py-8">
                  <Activity className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">No monitors found</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Channel</TableHead>
                      <TableHead>User ID</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Started</TableHead>
                      <TableHead>Process ID</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {monitorsData.monitors.map((monitor, index) => (
                      <TableRow key={monitor.id || `monitor-${index}`}>
                        <TableCell className="font-medium">{monitor.channel_name}</TableCell>
                        <TableCell className="font-mono text-xs">{monitor.user_id?.slice(0, 8)}...</TableCell>
                        <TableCell>
                          <Badge variant={monitor.status === "running" ? "default" : "secondary"}>
                            {monitor.status}
                          </Badge>
                        </TableCell>
                        <TableCell>{monitor.started_at ? new Date(monitor.started_at).toLocaleString() : 'N/A'}</TableCell>
                        <TableCell>{monitor.process_id || 'N/A'}</TableCell>
                        <TableCell className="text-right">
                          {monitor.status === "running" && (
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  disabled={stopMonitorMutation.isPending}
                                >
                                  <AlertCircle className="h-4 w-4 mr-1" />
                                  Stop
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>Stop Monitor</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    Are you sure you want to stop monitoring {monitor.channel_name}? This will terminate the monitoring process.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                                  <AlertDialogAction
                                    onClick={() => stopMonitorMutation.mutate(monitor.channel_name)}
                                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                  >
                                    Stop Monitor
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Admin;
