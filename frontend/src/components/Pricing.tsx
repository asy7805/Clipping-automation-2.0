import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";
import { useState } from "react";

const Pricing = () => {
  const [isAnnual, setIsAnnual] = useState(false);

  const plans = [
    {
      name: "Explore",
      description: "For early stage - founders",
      price: 29,
      features: [
        "Automate up to 5 workflows",
        "Core project task management",
        "Dashboard with real time updates",
        "Basic notifications & reminders",
        "Standard support ( email )",
        "10 GB storage for files"
      ]
    },
    {
      name: "Growth",
      description: "Perfect for teams who are ready to scale.",
      price: 99,
      popular: true,
      features: [
        "Unlimited task automations",
        "Advanced analytics & reporting",
        "Unlimited team seats & collaborators",
        "Priority support (chat + email)",
        "100 GB storage & version history",
        "API access to connect your tools"
      ]
    },
    {
      name: "Scale",
      description: "Enterprise-grade automation for scale.",
      price: 299,
      features: [
        "Everything in Growth",
        "AI-powered insights & forecasting",
        "Custom roles & permissions",
        "SSO + enterprise security",
        "Dedicated account manager",
        "Unlimited storage & audit logs"
      ]
    }
  ];

  return (
    <section className="py-24 px-6 relative overflow-hidden">
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-1/2 right-1/4 w-96 h-96 bg-accent/20 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto relative z-10">
        <div className="text-center mb-16">
          <Badge variant="outline" className="mb-4">Pricing</Badge>
          <h2 className="text-4xl md:text-5xl font-bold mb-4">
            Affordable Pricing Plans
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8">
            Simple flexible pricing tailored to your needs.
          </p>

          <div className="inline-flex items-center gap-4 glass p-2 rounded-lg">
            <button
              onClick={() => setIsAnnual(false)}
              className={`px-6 py-2 rounded-md transition-all ${!isAnnual ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
            >
              Monthly
            </button>
            <button
              onClick={() => setIsAnnual(true)}
              className={`px-6 py-2 rounded-md transition-all ${isAnnual ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
            >
              Annually <span className="text-xs ml-1">(Save 20%)</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {plans.map((plan, index) => (
            <Card 
              key={index}
              className={`group p-8 transition-all duration-300 cursor-pointer hover:scale-105 border-border/50 relative ${
                plan.popular 
                  ? 'bg-primary/5 border-primary/50 shadow-lg shadow-primary/20' 
                  : 'glass hover:bg-card/50 hover:shadow-lg hover:shadow-primary/20'
              }`}
            >
              {plan.popular && (
                <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary">
                  Most Popular
                </Badge>
              )}

              <div className="mb-6">
                <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
                <p className="text-sm text-muted-foreground">{plan.description}</p>
              </div>

              <div className="mb-8">
                <div className="flex items-baseline gap-2">
                  <span className="text-5xl font-bold">
                    ${isAnnual ? Math.round(plan.price * 0.8) : plan.price}
                  </span>
                  <span className="text-muted-foreground">/ month</span>
                </div>
              </div>

              <Button 
                variant={plan.popular ? "hero" : "ghost-hero"}
                className="w-full mb-8"
                size="lg"
              >
                Get Started
              </Button>

              <div className="space-y-4">
                {plan.features.map((feature, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <div className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <Check className="w-3 h-3 text-primary" />
                    </div>
                    <span className="text-sm text-muted-foreground">{feature}</span>
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Pricing;
