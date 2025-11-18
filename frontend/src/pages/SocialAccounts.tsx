import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  ExternalLink, 
  Trash2, 
  Plus, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Users,
  Video,
  Calendar
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { toast } from "sonner";

interface SocialAccount {
  id: string;
  platform: string;
  account_id: string;
  account_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface OAuthResponse {
  oauth_url: string;
  state: string;
  platform: string;
}

const SocialAccounts = () => {
  const [isConnecting, setIsConnecting] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // Fetch social accounts
  const { data: accounts, isLoading, error } = useQuery({
    queryKey: ["social-accounts"],
    queryFn: async () => {
      const response = await apiClient.getSocialAccounts();
      return response.accounts as SocialAccount[];
    },
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Initiate OAuth connection
  const initiateOAuth = useMutation({
    mutationFn: async (platform: string) => {
      const response = await apiClient.initiateSocialAuth(platform);
      return response as OAuthResponse;
    },
    onSuccess: (data) => {
      // Open OAuth URL in new window
      const popup = window.open(
        data.oauth_url,
        'oauth',
        'width=600,height=700,scrollbars=yes,resizable=yes'
      );
      
      // Listen for messages from popup (OAuth completion)
      const handleMessage = (event: MessageEvent) => {
        if (event.origin !== window.location.origin) return;
        
        if (event.data.type === 'OAUTH_SUCCESS') {
          window.removeEventListener('message', handleMessage);
          setIsConnecting(null);
          // Refetch accounts
          queryClient.invalidateQueries({ queryKey: ["social-accounts"] });
          toast.success(`${data.platform} account connected successfully!`);
        } else if (event.data.type === 'OAUTH_ERROR') {
          window.removeEventListener('message', handleMessage);
          setIsConnecting(null);
          toast.error(`Failed to connect ${data.platform} account`);
        }
      };
      
      window.addEventListener('message', handleMessage);
      
      // Fallback: check if popup is closed (with error handling)
      const checkClosed = setInterval(() => {
        try {
          if (popup?.closed) {
            clearInterval(checkClosed);
            window.removeEventListener('message', handleMessage);
            setIsConnecting(null);
            // Refetch accounts
            queryClient.invalidateQueries({ queryKey: ["social-accounts"] });
          }
        } catch (error) {
          // COOP policy blocks access to popup.closed
          // This is expected, so we just ignore the error
          clearInterval(checkClosed);
        }
      }, 1000);
    },
    onError: (error: any) => {
      toast.error(`Failed to initiate ${isConnecting} connection: ${error.message}`);
      setIsConnecting(null);
    },
  });

  // Unlink account
  const unlinkAccount = useMutation({
    mutationFn: async (accountId: string) => {
      await apiClient.unlinkSocialAccount(accountId);
    },
    onSuccess: () => {
      toast.success("Account unlinked successfully");
      queryClient.invalidateQueries({ queryKey: ["social-accounts"] });
    },
    onError: (error: any) => {
      toast.error(`Failed to unlink account: ${error.message}`);
    },
  });

  const handleConnect = async (platform: string) => {
    setIsConnecting(platform);
    try {
      await initiateOAuth.mutateAsync(platform);
    } catch (error) {
      setIsConnecting(null);
    }
  };

  const hasYouTubeAccount = accounts?.some(acc => acc.platform === 'youtube' && acc.is_active);
  const hasTikTokAccount = accounts?.some(acc => acc.platform === 'tiktok' && acc.is_active);

  const handleUnlink = async (accountId: string, platform: string) => {
    if (window.confirm(`Are you sure you want to unlink your ${platform} account?`)) {
      await unlinkAccount.mutateAsync(accountId);
    }
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

  const getPlatformColor = (platform: string) => {
    switch (platform) {
      case 'tiktok':
        return 'bg-pink-500';
      case 'youtube':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading social accounts...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to load social accounts: {(error as Error).message}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Social Accounts</h1>
          <p className="text-muted-foreground mt-2">
            Connect your social media accounts to automatically post clips
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="flex items-center gap-1">
            <Users className="w-3 h-3" />
            {accounts?.length || 0} Connected
          </Badge>
        </div>
      </div>

      {/* Platform Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* TikTok */}
        <Card className="relative overflow-hidden">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-pink-500 flex items-center justify-center text-white text-xl">
                  🎵
                </div>
                <div>
                  <CardTitle className="text-lg">TikTok</CardTitle>
                  <CardDescription>Post clips as TikTok videos</CardDescription>
                </div>
              </div>
              <Badge variant="secondary">Popular</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {accounts?.find(acc => acc.platform === 'tiktok') ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-green-600">
                  <CheckCircle className="w-4 h-4" />
                  <span className="font-medium">Connected</span>
                </div>
                <div className="text-sm text-muted-foreground">
                  @{accounts.find(acc => acc.platform === 'tiktok')?.account_name}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleUnlink(
                      accounts.find(acc => acc.platform === 'tiktok')?.id || '',
                      'tiktok'
                    )}
                    disabled={unlinkAccount.isPending}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Unlink
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <XCircle className="w-4 h-4" />
                  <span className="text-sm">Not connected</span>
                </div>
                <Button
                  onClick={() => handleConnect('tiktok')}
                  disabled={isConnecting === 'tiktok'}
                  className="w-full"
                >
                  {isConnecting === 'tiktok' ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Connecting...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4 mr-2" />
                      Connect TikTok
                    </>
                  )}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* YouTube */}
        <Card className="relative overflow-hidden">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-red-500 flex items-center justify-center text-white text-xl">
                  📺
                </div>
                <div>
                  <CardTitle className="text-lg">YouTube</CardTitle>
                  <CardDescription>Post clips as YouTube Shorts</CardDescription>
                </div>
              </div>
              <Badge variant="secondary">Shorts</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {hasYouTubeAccount ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-green-600">
                  <CheckCircle className="w-4 h-4" />
                  <span className="font-medium">
                    {accounts?.filter(acc => acc.platform === 'youtube' && acc.is_active).length || 0} Channel(s) Connected
                  </span>
                </div>
                <div className="text-sm text-muted-foreground">
                  See all connected channels below
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={() => handleConnect('youtube')}
                    disabled={isConnecting === 'youtube'}
                    variant="outline"
                    size="sm"
                    className="flex-1"
                  >
                    {isConnecting === 'youtube' ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary mr-2"></div>
                        Connecting...
                      </>
                    ) : (
                      <>
                        <Plus className="w-4 h-4 mr-2" />
                        Connect Another Channel
                      </>
                    )}
                  </Button>
                </div>
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-xs">
                    You can connect multiple YouTube channels from the same Gmail account
                  </AlertDescription>
                </Alert>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <XCircle className="w-4 h-4" />
                  <span className="text-sm">Not connected</span>
                </div>
                <Button
                  onClick={() => handleConnect('youtube')}
                  disabled={isConnecting === 'youtube'}
                  className="w-full"
                >
                  {isConnecting === 'youtube' ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Connecting...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4 mr-2" />
                      Connect YouTube
                    </>
                  )}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Connected Accounts List */}
      {accounts && accounts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="w-5 h-5" />
              Connected Accounts
            </CardTitle>
            <CardDescription>
              Manage your linked social media accounts
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {accounts.map((account) => (
                <div
                  key={account.id}
                  className="flex items-center justify-between p-3 rounded-lg border bg-muted/20"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg ${getPlatformColor(account.platform)} flex items-center justify-center text-white text-sm`}>
                      {getPlatformIcon(account.platform)}
                    </div>
                    <div>
                      <div className="font-medium capitalize">{account.platform}</div>
                      <div className="text-sm text-muted-foreground">
                        @{account.account_name}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={account.is_active ? "default" : "secondary"}>
                      {account.is_active ? "Active" : "Inactive"}
                    </Badge>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleUnlink(account.id, account.platform)}
                      disabled={unlinkAccount.isPending}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Help Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            How it works
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center space-y-2">
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
                <Plus className="w-4 h-4 text-primary" />
              </div>
              <h3 className="font-medium">Connect Accounts</h3>
              <p className="text-sm text-muted-foreground">
                Link your TikTok and YouTube accounts securely
              </p>
            </div>
            <div className="text-center space-y-2">
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
                <Video className="w-4 h-4 text-primary" />
              </div>
              <h3 className="font-medium">Auto Post</h3>
              <p className="text-sm text-muted-foreground">
                Clips are automatically posted to your connected accounts
              </p>
            </div>
            <div className="text-center space-y-2">
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
                <Calendar className="w-4 h-4 text-primary" />
              </div>
              <h3 className="font-medium">Schedule Posts</h3>
              <p className="text-sm text-muted-foreground">
                Schedule posts for optimal engagement times
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SocialAccounts;
