import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Link } from "react-router-dom";

const CTA = () => {
  const stats = [
    { value: "10K+", label: "Clips Captured" },
    { value: "500+", label: "Streamers" },
    { value: "24/7", label: "Monitoring" },
    { value: "95%", label: "Accuracy" }
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
            Ready to Never Miss a Viral Moment?
          </h2>
          <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
            Join hundreds of streamers who use AI to automatically capture their best moments. Start your free trial today.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Link to="/signup">
            <Button variant="hero" size="lg" className="text-base px-8">
              Get Started For Free
            </Button>
            </Link>
            <Button 
              variant="ghost-hero" 
              size="lg" 
              className="text-base px-8"
              onClick={() => {
                window.location.href = 'mailto:support@clippingautomation.com?subject=Demo Request';
              }}
            >
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
