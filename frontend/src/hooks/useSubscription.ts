import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/lib/api";

interface SubscriptionStatus {
  tier: string;
  credits_remaining: number;
  trial_used: boolean;
  subscription_started_at: string | null;
  subscription_expires_at: string | null;
  cancelled_at: string | null;
  is_cancelled: boolean;
}

interface CreditTransaction {
  id: string;
  amount: number;
  transaction_type: string;
  description: string | null;
  clip_id: string | null;
  created_at: string;
}

export const useSubscription = () => {
  const { user, isAuthenticated, isAdmin } = useAuth();
  const queryClient = useQueryClient();

  // Fetch subscription status
  const { data: subscription, isLoading, error } = useQuery<SubscriptionStatus>({
    queryKey: ["subscription", user?.id],
    queryFn: async () => {
      const response = await apiClient.get("/subscription/status");
      return response.data;
    },
    enabled: isAuthenticated && !!user,
    refetchInterval: 60000, // Refetch every minute
  });

  // Claim trial mutation
  const claimTrialMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.post("/subscription/claim-trial");
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subscription", user?.id] });
    },
  });

  // Fetch credit transactions
  const { data: transactions } = useQuery<CreditTransaction[]>({
    queryKey: ["subscription-transactions", user?.id],
    queryFn: async () => {
      const response = await apiClient.get("/subscription/transactions");
      return response.data;
    },
    enabled: isAuthenticated && !!user,
  });

  // Admins always have Pro access and unlimited credits
  const effectiveTier = isAdmin ? "pro" : (subscription?.tier || "free_trial");
  const effectiveCredits = isAdmin ? 999999 : (subscription?.credits_remaining || 0);
  
  return {
    subscription,
    isLoading,
    error,
    tier: effectiveTier,
    credits: effectiveCredits,
    isPro: isAdmin || subscription?.tier === "pro", // Admins always have Pro access
    isTrial: !isAdmin && subscription?.tier === "free_trial",
    isPayAsYouGo: !isAdmin && subscription?.tier === "pay_as_you_go",
    isExpired: !isAdmin && subscription?.tier === "expired",
    hasCredits: isAdmin || (subscription?.credits_remaining || 0) > 0, // Admins always have credits
    trialUsed: isAdmin || (subscription?.trial_used || false), // Admins don't need trial
    transactions,
    claimTrial: claimTrialMutation.mutate,
    isClaimingTrial: claimTrialMutation.isPending,
  };
};

