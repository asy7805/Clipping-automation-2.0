import { Badge } from "@/components/ui/badge";
import { Crown, Coins, Clock, AlertCircle } from "lucide-react";
import { useSubscription } from "@/hooks/useSubscription";
import { cn } from "@/lib/utils";
import { UpgradeModal } from "./UpgradeModal";
import { useState } from "react";

export const SubscriptionBadge = ({ showCredits = true, className }: { showCredits?: boolean; className?: string }) => {
  const { tier, credits, isPro, isTrial, isExpired, isLoading } = useSubscription();
  const [showUpgrade, setShowUpgrade] = useState(false);

  if (isLoading) {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        <div className="h-5 w-20 bg-muted animate-pulse rounded" />
      </div>
    );
  }

  const getTierBadge = () => {
    if (isPro) {
      return (
        <Badge variant="default" className="bg-gradient-to-r from-yellow-500 to-orange-500 text-white border-0">
          <Crown className="w-3 h-3 mr-1" />
          Pro
        </Badge>
      );
    }
    if (isTrial) {
      return (
        <Badge variant="secondary" className="bg-blue-500/20 text-blue-400 border-blue-500/30">
          <Clock className="w-3 h-3 mr-1" />
          Free Trial
        </Badge>
      );
    }
    if (isExpired) {
      return (
        <Badge variant="destructive" className="bg-red-500/20 text-red-400 border-red-500/30">
          <AlertCircle className="w-3 h-3 mr-1" />
          Expired
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="bg-purple-500/20 text-purple-400 border-purple-500/30">
        <Coins className="w-3 h-3 mr-1" />
        Pay-as-You-Go
      </Badge>
    );
  };

  const getCreditsDisplay = () => {
    if (!showCredits) return null;
    
    const creditsColor = credits < 5 ? "text-destructive" : credits < 10 ? "text-warning" : "text-success";
    
    return (
      <div className={cn("flex items-center gap-1.5 text-sm", creditsColor)}>
        <Coins className="w-3.5 h-3.5" />
        <span className="font-semibold">{credits}</span>
        <span className="text-muted-foreground text-xs">credits</span>
      </div>
    );
  };

  return (
    <>
      <div className={cn("flex items-center gap-3", className)}>
        {getTierBadge()}
        {getCreditsDisplay()}
        {(credits < 5 || isExpired) && (
          <button
            onClick={() => setShowUpgrade(true)}
            className="text-xs text-primary hover:text-primary/80 underline"
          >
            Upgrade
          </button>
        )}
      </div>
      <UpgradeModal open={showUpgrade} onOpenChange={setShowUpgrade} />
    </>
  );
};

