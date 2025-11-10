import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tv, Brain, Video } from "lucide-react";

const Process = () => {
  const steps = [
    {
      step: "Step 1",
      icon: Tv,
      title: "Connect Your Twitch",
      description: "Link your Twitch channel in under 2 minutes. No complex setup, just simple authentication."
    },
    {
      step: "Step 2",
      icon: Brain,
      title: "AI Watches Automatically",
      description: "Our AI monitors every stream in real-time, detecting viral moments using advanced audio analysis."
    },
    {
      step: "Step 3",
      icon: Video,
      title: "Get Clips Delivered",
      description: "Review your AI-scored highlights, edit them with our built-in tools, and post to social media."
    }
  ];

  return (
    <section id="how-it-works" className="py-24 px-6 relative overflow-hidden">
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-accent/20 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto relative z-10">
        <div className="text-center mb-16">
          <Badge variant="outline" className="mb-4">How It Works</Badge>
          <h2 className="text-4xl md:text-5xl font-bold mb-4">
            From Stream to Viral Clip in 3 Steps
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Getting started is fast, easy, and takes less than 5 minutes to set up.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {steps.map((item, index) => (
            <Card 
              key={index}
              className="group p-8 glass hover:bg-card/50 transition-all duration-300 cursor-pointer hover:scale-105 hover:shadow-lg hover:shadow-primary/20 border-border/50"
            >
              <Badge variant="secondary" className="mb-4">{item.step}</Badge>
              <div className="mb-6">
                <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                  <item.icon className="w-7 h-7 text-primary" />
                </div>
              </div>
              <h3 className="text-2xl font-bold mb-4">{item.title}</h3>
              <p className="text-muted-foreground">{item.description}</p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Process;
