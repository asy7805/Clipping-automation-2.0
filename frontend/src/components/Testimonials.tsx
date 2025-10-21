import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Star } from "lucide-react";

const Testimonials = () => {
  const testimonials = [
    {
      metric: "8x",
      metricLabel: "Increase in conversion rate",
      quote: "We automated 80% of our workflows and shipped 3 product updates in the same quarter — without burning out the team. Before using this AI platform, we were constantly scrambling to meet deadlines and dealing with endless back-and-forth on Slack.",
      author: "Sarah Johnson",
      role: "Marketing Director, Watch Rank",
      image: "https://framerusercontent.com/images/4Uw2YvhlvjVKC90RgCYJiJA7xto.jpg"
    },
    {
      metric: "2x",
      metricLabel: "Increase in Lead Generation",
      quote: "Our onboarding time dropped from 2 weeks to 3 days — and that's changed our entire growth trajectory. The AI project manager assigns tasks, pings the right people, and keeps everyone accountable without me micromanaging.",
      author: "Mark Bishop",
      role: "Head of Growth, Flex",
      image: "https://framerusercontent.com/images/P0zs6n56b4YsrIF1fN0pdmO0fnk.png"
    },
    {
      metric: "5%",
      metricLabel: "Less Client Acquisition Cost",
      quote: "We closed 2x more deals last quarter because nothing slips through the cracks anymore. The autonomous follow-ups make sure every lead gets nurtured and every task gets completed on time.",
      author: "James Lee",
      role: "Sales Director",
      image: "https://framerusercontent.com/images/kGbwa4d6dl3T9qSyfhfxB8oHqp4.jpg"
    }
  ];

  return (
    <section className="py-24 px-6 relative overflow-hidden">
      <div className="absolute inset-0 opacity-10">
        <div className="absolute bottom-0 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto relative z-10">
        <div className="text-center mb-16">
          <Badge variant="outline" className="mb-4">Testimonials</Badge>
          <h2 className="text-4xl md:text-5xl font-bold mb-4">
            Results that speaks volume
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Find out how happy clients are raving about us.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {testimonials.map((testimonial, index) => (
            <Card 
              key={index}
              className="group p-8 glass hover:bg-card/50 transition-all duration-300 cursor-pointer hover:scale-105 hover:shadow-lg hover:shadow-primary/20 border-border/50"
            >
              <div className="mb-6">
                <h3 className="text-5xl font-bold text-primary mb-2">{testimonial.metric}</h3>
                <p className="text-sm text-muted-foreground">{testimonial.metricLabel}</p>
              </div>

              <div className="flex gap-1 mb-4">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="w-4 h-4 fill-primary text-primary" />
                ))}
              </div>

              <p className="text-muted-foreground mb-6 italic">"{testimonial.quote}"</p>

              <div className="flex items-center gap-4">
                <img 
                  src={testimonial.image} 
                  alt={testimonial.author}
                  className="w-12 h-12 rounded-full object-cover"
                />
                <div>
                  <p className="font-semibold">{testimonial.author}</p>
                  <p className="text-sm text-muted-foreground">{testimonial.role}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Testimonials;
