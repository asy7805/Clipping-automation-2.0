import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { X, Check } from "lucide-react";

const Comparison = () => {
  const comparisons = [
    {
      others: "Slower execution and manual setup",
      stryve: "Fast setup with ready AI workflows"
    },
    {
      others: "Requires manual updates as you scale",
      stryve: "AI Task Assignment built to grow with you"
    },
    {
      others: "Limited or delayed reporting & notifications",
      stryve: "Real-time, AI-powered analytics & notifications"
    },
    {
      others: "Higher labor costs, less automation",
      stryve: "Automates tasks, reducing overhead"
    },
    {
      others: "Generic support or none at all",
      stryve: "Expert support + AI guidance"
    }
  ];

  return (
    <section className="py-24 px-6 relative overflow-hidden">
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-primary/20 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto relative z-10">
        <div className="text-center mb-16">
          <Badge variant="outline" className="mb-4">Comparison</Badge>
          <h2 className="text-4xl md:text-5xl font-bold mb-4">
            Choosing Stryve over others?
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            We combine growth automation + project management into one platform
          </p>
        </div>

        <Card className="max-w-4xl mx-auto glass border-border/50 overflow-hidden">
          <div className="grid grid-cols-2 divide-x divide-border/50">
            <div className="p-6 bg-muted/30">
              <h3 className="text-xl font-bold text-center mb-6">Other Tools</h3>
            </div>
            <div className="p-6 bg-primary/5">
              <h3 className="text-xl font-bold text-center mb-6 text-primary">Stryve</h3>
            </div>
          </div>

          {comparisons.map((item, index) => (
            <div 
              key={index}
              className="grid grid-cols-2 divide-x divide-border/50 hover:bg-card/50 transition-colors"
            >
              <div className="p-6 flex items-start gap-3">
                <X className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
                <p className="text-sm text-muted-foreground">{item.others}</p>
              </div>
              <div className="p-6 flex items-start gap-3 bg-primary/5">
                <Check className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                <p className="text-sm">{item.stryve}</p>
              </div>
            </div>
          ))}
        </Card>
      </div>
    </section>
  );
};

export default Comparison;
