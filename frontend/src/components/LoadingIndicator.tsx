import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface LoadingIndicatorProps {
  isLoading?: boolean;
  className?: string;
}

export const LoadingIndicator = ({ isLoading, className }: LoadingIndicatorProps) => {
  if (!isLoading) return null;

  return (
    <div className={cn(
      "fixed top-20 right-6 z-50",
      "flex items-center gap-2 px-4 py-2 rounded-lg",
      "glass-strong border-primary/30",
      "animate-in slide-in-from-top-2 fade-in",
      className
    )}>
      <Loader2 className="w-4 h-4 animate-spin text-primary" />
      <span className="text-sm text-muted-foreground">Updating...</span>
    </div>
  );
};
