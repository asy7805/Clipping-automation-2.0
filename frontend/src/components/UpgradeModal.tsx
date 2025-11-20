import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Check, Crown, Coins, Zap } from "lucide-react";
import { useSubscription } from "@/hooks/useSubscription";
import { useNavigate } from "react-router-dom";

interface UpgradeModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const UpgradeModal = ({ open, onOpenChange }: UpgradeModalProps) => {
  const { tier, credits, isPro, isTrial, isExpired } = useSubscription();
  const navigate = useNavigate();

  const plans = [
    {
      name: "Free Trial",
      price: 0,
      credits: 20,
      features: [
        "20 credits total (one-time)",
        "1 monitor per account",
        "Watermarked clips",
        "30-day clip storage",
        "1-hour session limit",
        "Standard processing",
      ],
      current: isTrial,
      disabled: true,
    },
    {
      name: "Pro",
      price: 19,
      credits: 150,
      popular: true,
      features: [
        "150 credits/month (resets monthly)",
        "1 monitor per account",
        "No watermark",
        "Unlimited clip storage",
        "Unlimited session length",
        "Social posting enabled",
        "Priority processing",
      ],
      current: isPro,
      disabled: false,
    },
    {
      name: "Pay-as-You-Go",
      price: "10+",
      credits: "40+",
      features: [
        "Purchase credits as needed",
        "Credits don't expire",
        "No watermark",
        "Unlimited storage",
        "No session limits",
        "Standard processing",
      ],
      current: tier === "pay_as_you_go",
      disabled: false,
    },
  ];

  const handleUpgrade = (planName: string) => {
    // TODO: Navigate to payment page or initiate Stripe checkout
    if (planName === "Pro") {
      // Navigate to Pro checkout
      console.log("Upgrade to Pro");
    } else if (planName === "Pay-as-You-Go") {
      // Navigate to credit purchase
      console.log("Purchase credits");
    }
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold">Upgrade Your Plan</DialogTitle>
          <DialogDescription>
            Choose the plan that's right for you. Upgrade anytime to unlock more features.
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`
                relative p-6 rounded-lg border-2 transition-all
                ${plan.popular ? "border-primary bg-primary/5" : "border-border"}
                ${plan.current ? "ring-2 ring-primary" : ""}
                ${plan.disabled ? "opacity-60" : ""}
              `}
            >
              {plan.popular && (
                <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-white">
                  Most Popular
                </Badge>
              )}
              {plan.current && (
                <Badge className="absolute -top-3 right-3 bg-green-500 text-white">
                  Current
                </Badge>
              )}

              <div className="text-center mb-4">
                <h3 className="text-xl font-bold mb-2">{plan.name}</h3>
                <div className="flex items-baseline justify-center gap-1">
                  <span className="text-3xl font-bold">
                    ${typeof plan.price === "number" ? plan.price : plan.price}
                  </span>
                  {typeof plan.price === "number" && (
                    <span className="text-muted-foreground">/month</span>
                  )}
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  {plan.credits} credits
                </p>
              </div>

              <ul className="space-y-2 mb-6">
                {plan.features.map((feature, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <Check className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>

              <Button
                className="w-full"
                variant={plan.popular ? "default" : "outline"}
                disabled={plan.disabled || plan.current}
                onClick={() => handleUpgrade(plan.name)}
              >
                {plan.current ? "Current Plan" : plan.disabled ? "Unavailable" : "Upgrade"}
              </Button>
            </div>
          ))}
        </div>

        {credits < 5 && !isExpired && (
          <div className="mt-6 p-4 bg-warning/10 border border-warning/20 rounded-lg">
            <div className="flex items-start gap-3">
              <Zap className="w-5 h-5 text-warning mt-0.5" />
              <div>
                <p className="font-semibold text-warning">Low Credits Warning</p>
                <p className="text-sm text-muted-foreground mt-1">
                  You have {credits} credits remaining. Upgrade to Pro or purchase credits to continue creating clips.
                </p>
              </div>
            </div>
          </div>
        )}

        {isExpired && (
          <div className="mt-6 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
            <div className="flex items-start gap-3">
              <Crown className="w-5 h-5 text-destructive mt-0.5" />
              <div>
                <p className="font-semibold text-destructive">Subscription Expired</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Your subscription has expired. Resubscribe to Pro or purchase credits to continue creating clips.
                </p>
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

