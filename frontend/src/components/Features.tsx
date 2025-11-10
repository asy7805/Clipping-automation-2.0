import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tv, Sparkles, TrendingUp, Video, Clock, Users } from "lucide-react";

const Features = () => {
  const features = [
    {
      icon: Clock,
      title: "24/7 Stream Monitoring",
      description: "AI watches your Twitch streams around the clock, never missing a moment.",
      category: "Automation"
    },
    {
      icon: Sparkles,
      title: "Smart Clip Detection",
      description: "Automatically identifies viral-worthy moments using advanced audio analysis.",
      category: "AI"
    },
    {
      icon: TrendingUp,
      title: "AI Confidence Scoring",
      description: "Each clip gets rated for viral potential so you know what to post first.",
      category: "AI"
    },
    {
      icon: Video,
      title: "Searchable Clip Library",
      description: "All captured moments organized and ready to review in one place.",
      category: "Organization"
    },
    {
      icon: Users,
      title: "Multi-Stream Support",
      description: "Monitor multiple Twitch channels simultaneously from one dashboard.",
      category: "Monitoring"
    },
    {
      icon: Tv,
      title: "Live Dashboard",
      description: "See exactly what's being monitored and captured in real-time.",
      category: "Monitoring"
    }
  ];

  return (
    <section id="features" className="py-24 px-6 relative overflow-hidden">
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-accent/20 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto relative z-10">
        <div className="text-center mb-16">
          <Badge variant="outline" className="mb-4">Features</Badge>
          <h2 className="text-4xl md:text-5xl font-bold mb-4">
            Everything You Need to Go Viral
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            All the tools you need to capture, edit, and share your best streaming moments—powered by AI.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <Card 
              key={index}
              className="group p-6 glass hover:bg-card/50 transition-all duration-300 cursor-pointer hover:scale-105 hover:shadow-lg hover:shadow-primary/20 border-border/50"
            >
              <div className="mb-4">
                <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                  <feature.icon className="w-6 h-6 text-primary" />
                </div>
              </div>
              <Badge variant="secondary" className="mb-3 text-xs">
                {feature.category}
              </Badge>
              <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
              <p className="text-muted-foreground text-sm">{feature.description}</p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Features;
