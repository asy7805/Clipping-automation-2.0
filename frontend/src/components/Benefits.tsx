import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Repeat, Brain, Command, Workflow, Users, Clock } from "lucide-react";

const Benefits = () => {
  const benefits = [
    {
      icon: Repeat,
      title: "Automate Growth Loops",
      description: "Onboarding, lead nurture, and campaign follow-ups - hands-free."
    },
    {
      icon: Brain,
      title: "AI-Driven Insights",
      description: "Predict bottlenecks and optimize team performance automatically."
    },
    {
      icon: Command,
      title: "Central Command Center",
      description: "One dashboard for projects, sprints, and growth KPIs."
    },
    {
      icon: Workflow,
      title: "Custom Workflows",
      description: "Tailor workflows to fit your team's unique needs."
    },
    {
      icon: Users,
      title: "Task Accountability",
      description: "Assign tasks clearly to ensure responsibility and ownership."
    },
    {
      icon: Clock,
      title: "Save 20+ Hours a Week",
      description: "Focus on outcomes, not operations. Save upto 20 hours a week."
    }
  ];

  return (
    <section className="py-24 px-6 relative overflow-hidden">
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-primary/20 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto relative z-10">
        <div className="text-center mb-16">
          <Badge variant="outline" className="mb-4">Benefits</Badge>
          <h2 className="text-4xl md:text-5xl font-bold mb-4">
            Why Businesses Choose Stryve?
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            We're so glad you asked.
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
