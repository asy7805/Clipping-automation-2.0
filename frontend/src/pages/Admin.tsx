import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { apiClient } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { clampScore } from "@/lib/utils";
import { Navigate } from "react-router-dom";
import { Users, Video, Database, Activity } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

interface AdminStats {
  total_users: number;
  total_clips: number;
  total_monitors: number;
  active_monitors: number;
  clips_today: number;
  clips_this_week: number;
  avg_clips_per_user: number;
  avg_score: number;
}

interface User {
  id: string;
  email: string;
  created_at: string;
  last_sign_in_at?: string;
}

interface Clip {
  id: string;
  user_id: string;
  channel_name: string;
  confidence_score: number;
  created_at: string;
  storage_url: string;
}

const Admin = () => {
  const { user, isAdmin } = useAuth();
  const [adminVerified, setAdminVerified] = useState<boolean | null>(null);

  // Verify admin status
  useEffect(() => {
    const verifyAdmin = async () => {
      if (!user) {
        setAdminVerified(false);
        return;
      }
      
      // Check with backend if user is admin
      try {
        const { data: { session } } = await supabase.auth.getSession();
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/admin/stats`, {
          headers: {
            Authorization: `Bearer ${session?.access_token}`,
          },
        });
        
        if (response.status === 403) {
          setAdminVerified(false);
          toast.error("Access denied: Admin privileges required");
        } else if (response.ok) {
          setAdminVerified(true);
        } else {
          setAdminVerified(false);
        }
      } catch (error) {
        console.error("Admin verification failed:", error);
        setAdminVerified(false);
      }
    };

    verifyAdmin();
  }, [user]);

  // Fetch admin stats
  const { data: stats, isLoading: statsLoading } = useQuery<AdminStats>({
    queryKey: ["admin-stats"],
    queryFn: async () => {
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/admin/stats`, {
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
        },
      });
      if (!response.ok) throw new Error("Failed to fetch stats");
      return response.json();
    },
    enabled: adminVerified === true,
  });

  // Fetch all users (admin only)
  const { data: usersData, isLoading: usersLoading } = useQuery<{ users: User[] }>({
    queryKey: ["admin-users"],
    queryFn: async () => {
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/admin/users`, {
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
        },
      });
      if (!response.ok) throw new Error("Failed to fetch users");
      return response.json();
    },
    enabled: adminVerified === true,
  });
  
  const users = usersData?.users || [];

  // Fetch all clips (admin sees all clips with the updated endpoint)
  const { data: clips, isLoading: clipsLoading } = useQuery<{ clips: Clip[] }>({
    queryKey: ["admin-clips"],
    queryFn: async () => apiClient.getClips(50, 0, "newest"),
    enabled: adminVerified === true,
  });

  // Redirect if not admin
  if (adminVerified === false) {
    toast.error("Access denied: Admin privileges required");
    return <Navigate to="/dashboard" replace />;
  }

  if (adminVerified === null) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Verifying admin access...</p>
        </div>
      </div>
    );
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
            <div className="text-2xl font-bold">{stats?.total_users || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Clips</CardTitle>
            <Video className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_clips || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {stats?.clips_today || 0} today
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Monitors</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.active_monitors || 0} / {stats?.total_monitors || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Score</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.avg_score?.toFixed(2) || "0.00"}</div>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Views */}
      <Tabs defaultValue="users" className="w-full">
        <TabsList>
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="clips">All Clips</TabsTrigger>
        </TabsList>

        <TabsContent value="users" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>All Users</CardTitle>
              <CardDescription>Registered users in the system</CardDescription>
            </CardHeader>
            <CardContent>
              {usersLoading ? (
                <div className="text-center py-8">Loading users...</div>
              ) : (
                <div className="space-y-2">
                  {users?.map((u, index) => (
                    <div
                      key={u.id || index}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div>
                        <p className="font-medium">{u.email || 'Unknown'}</p>
                        <p className="text-xs text-muted-foreground">
                          {u.id ? `ID: ${u.id.slice(0, 8)}...` : 'No ID'} {u.created_at && `| Joined: ${new Date(u.created_at).toLocaleDateString()}`}
                        </p>
                      </div>
                      {u.last_sign_in_at && (
                        <Badge variant="outline">
                          Last login: {new Date(u.last_sign_in_at).toLocaleDateString()}
                        </Badge>
                      )}
                    </div>
                  ))}
                </div>
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
              {clipsLoading ? (
                <div className="text-center py-8">Loading clips...</div>
              ) : (
                <div className="space-y-2">
                  {clips?.clips?.map((clip, index) => (
                    <div
                      key={clip.id || index}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div className="flex-1">
                        <p className="font-medium">{clip.channel_name || 'Unknown'}</p>
                        <p className="text-xs text-muted-foreground">
                          {clip.user_id ? `User: ${clip.user_id.slice(0, 8)}...` : 'No user'} {clip.created_at && `| ${new Date(clip.created_at).toLocaleDateString()}`}
                        </p>
                      </div>
                      <Badge
                        variant={clampScore(clip.confidence_score) >= 0.7 ? "default" : "secondary"}
                      >
                        Score: {clampScore(clip.confidence_score).toFixed(2)}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Admin;

