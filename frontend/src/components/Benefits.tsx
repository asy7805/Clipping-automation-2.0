import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Clock, TrendingUp, Brain, Zap, Target } from "lucide-react";

const Benefits = () => {
  const benefits = [
    {
      icon: Sparkles,
      title: "Never Miss a Viral Moment",
      description: "AI catches every highlight-worthy moment, even when you're asleep or offline."
    },
    {
      icon: Clock,
      title: "Save 20+ Hours Per Week",
      description: "No more rewatching entire VODs to find clips. AI does it for you automatically."
    },
    {
      icon: TrendingUp,
      title: "Grow Faster on Social Media",
      description: "More clips means more content for TikTok and YouTube. Consistent posting = faster growth."
    },
    {
      icon: Brain,
      title: "AI-Powered Quality Control",
      description: "Only get clips with high viral potential. AI scores every moment before saving it."
    },
    {
      icon: Zap,
      title: "Always-On Coverage",
      description: "Your personal highlight reel creator, monitoring 24/7 without breaks or burnout."
    },
    {
      icon: Target,
      title: "Focus on Streaming",
      description: "Stop worrying about content creation. Stream better knowing AI has your back."
    }
  ];

  return (
    <section id="benefits" className="py-24 px-6 relative overflow-hidden">
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-primary/20 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto relative z-10">
        <div className="text-center mb-16">
          <Badge variant="outline" className="mb-4">Benefits</Badge>
          <h2 className="text-4xl md:text-5xl font-bold mb-4">
            Why Streamers Love Our Platform
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Stop spending hours hunting for clips. Let AI work for you.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {benefits.map((benefit, index) => (
            <Card 
              key={index}
              className="group p-8 glass hover:bg-card/50 transition-all duration-300 cursor-pointer hover:scale-105 hover:shadow-lg hover:shadow-primary/20 border-border/50 text-center"
            >
              <div className="mb-6 flex justify-center">
                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors group-hover:scale-110 duration-300">
                  <benefit.icon className="w-8 h-8 text-primary" />
                </div>
              </div>
              <h3 className="text-xl font-semibold mb-3">{benefit.title}</h3>
              <p className="text-muted-foreground">{benefit.description}</p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Benefits;
