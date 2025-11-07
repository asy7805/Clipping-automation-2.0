import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Infinity } from "lucide-react";

const Hero = () => {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-20">
      <div className="absolute inset-0 opacity-20">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/30 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent/30 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }} />
      </div>

      <div className="container mx-auto px-6 relative z-10">
        <div className="text-center max-w-5xl mx-auto space-y-8">
          <Badge variant="hero" className="mb-4">
            <span className="text-xs font-semibold">🤖 AI-Powered</span>
            <span className="mx-2 text-muted-foreground">•</span>
            <span className="text-xs">Fully Automated</span>
          </Badge>

          <h1 className="text-6xl md:text-7xl lg:text-8xl font-bold leading-tight">
            Never Miss
            <br />
            <span className="inline-flex items-center gap-4 bg-gradient-to-r from-primary via-pink-500 to-primary bg-clip-text text-transparent">
              A Viral Moment
            </span>
          </h1>

          <p className="text-lg md:text-xl text-muted-foreground max-w-3xl mx-auto leading-relaxed">
            AI watches your Twitch streams 24/7, automatically detecting and saving the most clip-worthy moments. 
            No manual work. No missed opportunities. Just viral clips, delivered.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <Link to="/login">
              <Button variant="hero" size="lg" className="text-base px-8">
                Get Started Free
              </Button>
            </Link>
            <Button variant="ghost-hero" size="lg" className="text-base px-8">
              See How It Works
            </Button>
          </div>

          <p className="text-sm text-muted-foreground pt-8">
            🎬 16 clips already captured • 5 streamers monitored • 100% automated
          </p>
        </div>
      </div>
    </section>
  );
};

export default Hero;
