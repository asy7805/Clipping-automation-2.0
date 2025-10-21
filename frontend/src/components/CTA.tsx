import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const CTA = () => {
  const stats = [
    { value: "80%", label: "Growth Users" },
    { value: "5k+", label: "Workflows Made" },
    { value: "40+", label: "Integrations" },
    { value: "70+", label: "Countries" }
  ];

  return (
    <section className="py-24 px-6 relative overflow-hidden">
      <div className="absolute inset-0 opacity-20">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/30 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent/30 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }} />
      </div>

      <div className="container mx-auto relative z-10">
        <Card className="glass border-border/50 p-12 md:p-16 text-center max-w-4xl mx-auto">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Ready to Supercharge Your Productivity with AI?
          </h2>
          <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
            With AI-powered workflows, real-time project management, and automated follow-ups, your team gets clarity, speed, and focus
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Button variant="hero" size="lg" className="text-base px-8">
              Get Started For Free
            </Button>
            <Button variant="ghost-hero" size="lg" className="text-base px-8">
              Ask for a Demo
            </Button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat, index) => (
              <div key={index} className="text-center">
                <h3 className="text-4xl md:text-5xl font-bold text-primary mb-2">{stat.value}</h3>
                <p className="text-sm text-muted-foreground">{stat.label}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </section>
  );
};

export default CTA;
