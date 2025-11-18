import { Card, CardContent } from "@/components/ui/card";

interface SkeletonLoaderProps {
  variant?: "card" | "text" | "list";
  count?: number;
}

export const SkeletonLoader = ({ variant = "card", count = 1 }: SkeletonLoaderProps) => {
  if (variant === "card") {
    return (
      <>
        {Array.from({ length: count }).map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardContent className="p-6">
              <div className="space-y-4">
                <div className="h-4 bg-muted rounded w-3/4" />
                <div className="h-4 bg-muted rounded w-1/2" />
                <div className="h-20 bg-muted rounded" />
              </div>
            </CardContent>
          </Card>
        ))}
      </>
    );
  }

  if (variant === "list") {
    return (
      <div className="space-y-3">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 animate-pulse">
            <div className="w-10 h-10 bg-muted rounded-full" />
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-muted rounded w-3/4" />
              <div className="h-3 bg-muted rounded w-1/2" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-2 animate-pulse">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="h-4 bg-muted rounded" style={{ width: `${Math.random() * 40 + 60}%` }} />
      ))}
    </div>
  );
};

