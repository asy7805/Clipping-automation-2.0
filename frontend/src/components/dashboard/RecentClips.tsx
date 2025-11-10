import { ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useClips } from "@/hooks/useClips";
import { Link } from "react-router-dom";
import { NetflixClipCard } from "@/components/clips/NetflixClipCard";

export const RecentClips = () => {
  const { data: clipsData, isLoading, error } = useClips({ limit: 6 });
  
  // Extract clips array from paginated response
  const clips = clipsData?.clips || [];
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl md:text-2xl font-semibold">📹 Recent Clips</h2>
        <Link to="/dashboard/clips">
          <Button variant="ghost" className="text-primary hover:text-primary/90">
            View All <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </Link>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : error ? (
        <div className="flex items-center justify-center h-40">
          <p className="text-destructive">Failed to load clips. Please try again.</p>
        </div>
      ) : !clips || clips.length === 0 ? (
        <div className="flex items-center justify-center h-40">
          <p className="text-muted-foreground">No clips found. Start monitoring streams to capture clips!</p>
        </div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-thin">
          {clips.map((clip) => (
            <div key={clip.id} className="min-w-[280px] flex-shrink-0">
              <NetflixClipCard clip={clip} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

