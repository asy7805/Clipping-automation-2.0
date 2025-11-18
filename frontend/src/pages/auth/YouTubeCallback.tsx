import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Loader2,
  ExternalLink
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { toast } from "sonner";
import ChannelSelectorModal from "@/components/ChannelSelectorModal";

interface Channel {
  channel_id: string;
  title: string;
  description: string;
  subscriber_count: number;
  video_count: number;
  thumbnail: string;
  custom_url: string;
}

const YouTubeCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'loading' | 'success' | 'error' | 'select_channel'>('loading');
  const [message, setMessage] = useState<string>('');
  const [accountName, setAccountName] = useState<string>('');
  const [channels, setChannels] = useState<Channel[]>([]);
  const [oauthData, setOauthData] = useState<{ code: string; state: string; accessToken?: string; refreshToken?: string } | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');

        if (error) {
          setStatus('error');
          setMessage(`YouTube authorization failed: ${error}`);
          return;
        }

        if (!code || !state) {
          setStatus('error');
          setMessage('Missing authorization code or state parameter');
          return;
        }

        // Call backend to exchange code for tokens
        const response = await apiClient.oauthCallback('youtube', {
          code,
          state,
          platform: 'youtube'
        });

        setStatus('success');
        setMessage('YouTube account connected successfully!');
        setAccountName(response.account.account_name);

        // Show success toast
        toast.success(`Connected to YouTube: @${response.account.account_name}`);

        // Send success message to parent window
        if (window.opener) {
          window.opener.postMessage({
            type: 'OAUTH_SUCCESS',
            platform: 'youtube',
            account: response.account
          }, window.location.origin);
          window.close();
        } else {
          // Navigate back to social accounts page after delay
          setTimeout(() => {
            navigate('/dashboard/social');
          }, 2000);
        }

      } catch (error: any) {
        console.error('YouTube callback error:', error);
        setStatus('error');
        setMessage(error.message || 'Failed to connect YouTube account');
        
        toast.error(`YouTube connection failed: ${error.message}`);
        
        // Send error message to parent window
        if (window.opener) {
          window.opener.postMessage({
            type: 'OAUTH_ERROR',
            platform: 'youtube',
            error: error.message
          }, window.location.origin);
        }
      }
    };

    handleCallback();
  }, [searchParams, navigate]);

  const handleRetry = () => {
    navigate('/dashboard/social');
  };

  const handleClose = () => {
    if (window.opener) {
      window.close();
    } else {
      navigate('/dashboard/social');
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="w-16 h-16 rounded-full bg-red-500 flex items-center justify-center text-white text-2xl mx-auto mb-4">
            📺
          </div>
          <CardTitle className="text-2xl">YouTube Connection</CardTitle>
          <CardDescription>
            Connecting your YouTube account...
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {status === 'loading' && (
            <div className="text-center space-y-4">
              <div className="flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-red-500" />
              </div>
              <p className="text-muted-foreground">
                Processing YouTube authorization...
              </p>
            </div>
          )}

          {status === 'success' && (
            <div className="text-center space-y-4">
              <div className="flex items-center justify-center">
                <CheckCircle className="w-8 h-8 text-green-500" />
              </div>
              <div>
                <p className="font-medium text-green-600">Success!</p>
                <p className="text-sm text-muted-foreground">
                  Connected to YouTube: @{accountName}
                </p>
              </div>
              <Alert>
                <CheckCircle className="h-4 w-4" />
                <AlertDescription>
                  Your YouTube account is now connected and ready for posting Shorts!
                </AlertDescription>
              </Alert>
              <div className="flex gap-2">
                <Button onClick={handleClose} className="flex-1">
                  Continue
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => window.open('https://www.youtube.com', '_blank')}
                  className="flex-1"
                >
                  <ExternalLink className="w-4 h-4 mr-2" />
                  View YouTube
                </Button>
              </div>
            </div>
          )}

          {status === 'error' && (
            <div className="text-center space-y-4">
              <div className="flex items-center justify-center">
                <XCircle className="w-8 h-8 text-red-500" />
              </div>
              <div>
                <p className="font-medium text-red-600">Connection Failed</p>
                <p className="text-sm text-muted-foreground">
                  {message}
                </p>
              </div>
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {message}
                </AlertDescription>
              </Alert>
              <div className="flex gap-2">
                <Button onClick={handleRetry} className="flex-1">
                  Try Again
                </Button>
                <Button variant="outline" onClick={handleClose} className="flex-1">
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default YouTubeCallback;
