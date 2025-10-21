import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Workflow, Brain, LineChart, Grid, MessageSquare, BarChart3, Layout, Clock, Tag } from "lucide-react";

const Features = () => {
  const features = [
    {
      icon: Workflow,
      title: "Smart Workflow Builder",
      description: "Automate growth & marketing with drag-and-drop ease.",
      category: "Automation"
    },
    {
      icon: Brain,
      title: "AI Project Manager",
      description: "Auto-assign tasks, set deadlines, and unblock your team.",
      category: "AI"
    },
    {
      icon: LineChart,
      title: "Real-Time Analytics",
      description: "Track campaign performance and team KPIs in one view.",
      category: "Analytics"
    },
    {
      icon: Grid,
      title: "Cross-Tool Integrations",
      description: "Connect Slack, Notion, Jira, HubSpot, Zapier & more.",
      category: "Integration"
    },
    {
      icon: MessageSquare,
      title: "Autonomous Follow-Ups",
      description: "Let AI chase updates so you don't have to.",
      category: "AI"
    },
    {
      icon: BarChart3,
      title: "Advanced Analytics",
      description: "Visualize key metrics to make better, data-driven decisions.",
      category: "Analytics"
    },
    {
      icon: Layout,
      title: "Customizable Dashboards",
      description: "Personalize your dashboard with flexible options for styling.",
      category: "Customization"
    },
    {
      icon: Clock,
      title: "Simplified Time Trackers",
      description: "Log work hours directly within the platform.",
      category: "Productivity"
    },
    {
      icon: Tag,
      title: "Real Time Task Tags",
      description: "Organize tasks with customizable tags for quick filtering.",
      category: "Organization"
    }
  ];

  return (
    <section className="py-24 px-6 relative overflow-hidden">
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-accent/20 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto relative z-10">
        <div className="text-center mb-16">
          <Badge variant="outline" className="mb-4">Features</Badge>
          <h2 className="text-4xl md:text-5xl font-bold mb-4">
            Everything You Need to Scale
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            All the tools you need to run projects, grow faster, and keep your team in sync powered by AI.
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
