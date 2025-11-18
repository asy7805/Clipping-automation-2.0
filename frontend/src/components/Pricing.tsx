import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";
import { Link } from "react-router-dom";
import { ShineBorder } from "@/components/ui/shine-border";

const Pricing = () => {
  const plans = [
    {
      name: "Free Trial",
      description: "Try it out risk-free for 14 days",
      price: 0,
      features: [
        "Monitor 1 Twitch channel",
        "Up to 50 clips saved",
        "AI confidence scoring",
        "Searchable clip library",
        "Email support",
        "14-day full access"
      ]
    },
    {
      name: "Pro",
      description: "For serious streamers and content creators",
      price: 150,
      popular: true,
      features: [
        "Monitor unlimited Twitch channels",
        "Unlimited clips saved",
        "AI confidence scoring",
        "Searchable clip library",
        "Live monitoring dashboard",
        "Priority support",
        "Export clips anytime"
      ]
    }
  ];

  return (
    <section id="pricing" className="py-24 px-6 relative overflow-hidden">
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-1/2 right-1/4 w-96 h-96 bg-accent/20 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto relative z-10">
        <div className="text-center mb-16">
          <Badge variant="outline" className="mb-4">Pricing</Badge>
          <h2 className="text-4xl md:text-5xl font-bold mb-4">
            Simple, Transparent Pricing
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Start free, upgrade when you're ready. No hidden fees.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto pt-6">
          {plans.map((plan, index) => {
            const CardComponent = plan.popular ? (
              <div key={index} className="relative rounded-xl">
                {plan.popular && (
                  <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary z-20">
                    Most Popular
                  </Badge>
                )}
                <div className="relative rounded-xl overflow-hidden transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-primary/30">
                  <ShineBorder
                    shineColor={["#A07CFE", "#FE8FB5", "#FFBE7B"]}
                    borderWidth={2}
                    duration={10}
                  />
                  <Card className="group p-8 transition-all duration-300 cursor-pointer bg-card border border-primary/20 hover:border-primary/50 relative z-10 hover:shadow-lg hover:shadow-primary/20">

              <div className="mb-6">
                <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
                <p className="text-sm text-muted-foreground">{plan.description}</p>
              </div>

              <div className="mb-8">
                <div className="flex items-baseline gap-2">
                  <span className="text-5xl font-bold">
                    ${plan.price}
                  </span>
                  <span className="text-muted-foreground">/ month</span>
                </div>
              </div>

              <Link to="/signup">
                <Button 
                  variant="hero"
                  className="w-full mb-8"
                  size="lg"
                >
                  {plan.price === 0 ? "Start Free Trial" : "Get Started"}
                </Button>
              </Link>

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
                </div>
              </div>
            ) : (
              <Card 
                key={index}
                className="group p-8 transition-all duration-300 cursor-pointer hover:scale-105 border-border/50 relative bg-card hover:shadow-lg hover:shadow-primary/20"
              >
                <div className="mb-6">
                  <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
                  <p className="text-sm text-muted-foreground">{plan.description}</p>
                </div>

                <div className="mb-8">
                  <div className="flex items-baseline gap-2">
                    <span className="text-5xl font-bold">
                      ${plan.price}
                    </span>
                    <span className="text-muted-foreground">/ month</span>
                  </div>
                </div>

                <Link to="/signup">
                  <Button 
                    variant="hero"
                    className="w-full mb-8"
                    size="lg"
                  >
                    {plan.price === 0 ? "Start Free Trial" : "Get Started"}
                  </Button>
                </Link>

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
            );
            
            return CardComponent;
          })}
        </div>
      </div>
    </section>
  );
};

export default Pricing;
