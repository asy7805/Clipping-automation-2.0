import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Plug, Settings, Zap } from "lucide-react";

const Process = () => {
  const steps = [
    {
      step: "Step 1",
      icon: Plug,
      title: "Connect Your Tools",
      description: "Seamlessly bring in projects, campaigns, and data from every platform you use — all in just a few clicks."
    },
    {
      step: "Step 2",
      icon: Settings,
      title: "Build Your Workflows",
      description: "Create growth loops, automate task assignments, and set up detailed reporting dashboards that run themselves."
    },
    {
      step: "Step 3",
      icon: Zap,
      title: "Let AI Take Over",
      description: "Sit back as AI keeps your team on track, hitting deadlines, staying ahead of KPIs, and catching issues before they snowball."
    }
  ];

  return (
    <section className="py-24 px-6 relative overflow-hidden">
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-accent/20 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto relative z-10">
        <div className="text-center mb-16">
          <Badge variant="outline" className="mb-4">Process</Badge>
          <h2 className="text-4xl md:text-5xl font-bold mb-4">
            From Chaos to Clarity in 3 Steps
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Getting started is fast, easy, and doesn't disrupt your workflow.
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
