import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Youtube, Users, Video, Check } from "lucide-react";

interface Channel {
  channel_id: string;
  title: string;
  description: string;
  subscriber_count: number;
  video_count: number;
  thumbnail: string;
  custom_url: string;
}

interface ChannelSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  channels: Channel[];
  onSelectChannel: (channelId: string) => void;
  isLoading?: boolean;
}

const ChannelSelectorModal: React.FC<ChannelSelectorModalProps> = ({
  isOpen,
  onClose,
  channels,
  onSelectChannel,
  isLoading = false,
}) => {
  const [selectedChannelId, setSelectedChannelId] = useState<string | null>(null);

  const handleConfirm = () => {
    if (selectedChannelId) {
      onSelectChannel(selectedChannelId);
    }
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Youtube className="w-5 h-5 text-red-500" />
            Select YouTube Channel
          </DialogTitle>
          <DialogDescription>
            You have multiple YouTube channels. Please select which channel you want to connect.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-3 pr-2">
          {channels.map((channel) => (
            <Card
              key={channel.channel_id}
              className={`cursor-pointer transition-all hover:shadow-md ${
                selectedChannelId === channel.channel_id
                  ? "ring-2 ring-primary"
                  : "hover:border-primary/50"
              }`}
              onClick={() => setSelectedChannelId(channel.channel_id)}
            >
              <CardContent className="p-4">
                <div className="flex items-start gap-4">
                  {/* Channel Thumbnail */}
                  <Avatar className="w-16 h-16">
                    <AvatarImage src={channel.thumbnail} alt={channel.title} />
                    <AvatarFallback>
                      <Youtube className="w-8 h-8" />
                    </AvatarFallback>
                  </Avatar>

                  {/* Channel Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h3 className="font-semibold text-lg truncate">{channel.title}</h3>
                        {channel.custom_url && (
                          <p className="text-sm text-muted-foreground">@{channel.custom_url}</p>
                        )}
                      </div>
                      
                      {selectedChannelId === channel.channel_id && (
                        <div className="flex-shrink-0">
                          <Badge className="bg-green-500">
                            <Check className="w-3 h-3 mr-1" />
                            Selected
                          </Badge>
                        </div>
                      )}
                    </div>

                    {channel.description && (
                      <p className="text-sm text-muted-foreground line-clamp-2 mt-2">
                        {channel.description}
                      </p>
                    )}

                    {/* Stats */}
                    <div className="flex gap-4 mt-3">
                      <div className="flex items-center gap-1 text-sm text-muted-foreground">
                        <Users className="w-4 h-4" />
                        <span className="font-medium">
                          {formatNumber(channel.subscriber_count)}
                        </span>
                        <span className="hidden sm:inline">subscribers</span>
                      </div>
                      <div className="flex items-center gap-1 text-sm text-muted-foreground">
                        <Video className="w-4 h-4" />
                        <span className="font-medium">
                          {formatNumber(channel.video_count)}
                        </span>
                        <span className="hidden sm:inline">videos</span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button 
            onClick={handleConfirm} 
            disabled={!selectedChannelId || isLoading}
          >
            {isLoading ? "Connecting..." : "Connect Channel"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ChannelSelectorModal;

