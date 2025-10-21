import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { StreamMonitorCard } from "@/components/StreamMonitorCard";
import { useStreams } from "@/hooks/useStreamData";
import { useIsMobile } from "@/hooks/use-mobile";
import { AddMonitorModal } from "@/components/AddMonitorModal";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from "@/components/ui/carousel";

export const LiveMonitors = () => {
  const { data: streams, isLoading } = useStreams();
  const isMobile = useIsMobile();
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <>
      <div>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl md:text-2xl font-bold flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-success animate-pulse" />
            Live Monitors
          </h2>
          <Button 
            className="bg-primary hover:bg-primary/90" 
            size={isMobile ? "sm" : "default"}
            onClick={() => setIsModalOpen(true)}
          >
            <Plus className="w-4 h-4 md:mr-2" />
            <span className="hidden md:inline">Add Monitor</span>
          </Button>
        </div>

      {isMobile ? (
        // Mobile: Swipeable carousel
        <Carousel className="w-full">
          <CarouselContent className="-ml-4">
            {streams?.map((stream) => (
              <CarouselItem key={stream.id} className="pl-4">
                <StreamMonitorCard stream={stream} />
              </CarouselItem>
            ))}
            {isLoading && !streams && [1, 2, 3].map((i) => (
              <CarouselItem key={i} className="pl-4">
                <div className="p-6 glass-strong border-white/10 rounded-lg shimmer h-64" />
              </CarouselItem>
            ))}
          </CarouselContent>
        </Carousel>
      ) : (
        // Desktop: Grid layout
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
            <div 
              key={i}
              className="p-6 glass-strong border-white/10 rounded-lg shimmer h-64"
            />
          ))}
        </div>
      )}
      </div>

      <AddMonitorModal open={isModalOpen} onOpenChange={setIsModalOpen} />
    </>
  );
};
