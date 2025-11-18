import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Plus } from "lucide-react";
import { StreamMonitorCard } from "@/components/StreamMonitorCard";
import { useStreams } from "@/hooks/useStreamData";
import { AddMonitorModal } from "@/components/AddMonitorModal";

export const LiveMonitors = () => {
  const { data: streams, isLoading } = useStreams();
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <>
      <div>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl md:text-2xl font-semibold flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-success animate-pulse" />
            Live Monitors
          </h2>
          <Button 
            className="bg-primary hover:bg-primary/90" 
            onClick={() => setIsModalOpen(true)}
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Monitor
          </Button>
        </div>

        {/* Desktop: Grid layout */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {streams?.map((stream) => (
            <div 
              key={stream.id}
              className="animate-in fade-in slide-in-from-bottom-4"
              style={{ animationDuration: '500ms' }}
            >
              <StreamMonitorCard stream={stream} />
            </div>
          ))}
          
          {/* Loading skeleton */}
          {isLoading && !streams && [1, 2, 3].map((i) => (
            <Card key={i} className="p-6 animate-pulse">
              <div className="space-y-4">
                <div className="h-6 bg-muted rounded w-1/2" />
                <div className="h-4 bg-muted rounded w-3/4" />
                <div className="h-20 bg-muted rounded" />
              </div>
            </Card>
          ))}
        </div>
      </div>

      <AddMonitorModal open={isModalOpen} onOpenChange={setIsModalOpen} />
    </>
  );
};
