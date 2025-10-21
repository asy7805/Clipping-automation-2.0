import { Button } from "@/components/ui/button";
import { Infinity } from "lucide-react";

const Navigation = () => {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <Infinity className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold">Stryve</span>
          </div>
          
          <div className="hidden md:flex items-center gap-8">
            <a href="#home" className="text-sm hover:text-primary transition-colors">Home</a>
            <a href="#features" className="text-sm hover:text-primary transition-colors">Features</a>
            <a href="#pricing" className="text-sm hover:text-primary transition-colors">Pricing</a>
            <a href="#blog" className="text-sm hover:text-primary transition-colors">Blog</a>
            <a href="#waitlist" className="text-sm hover:text-primary transition-colors">Waitlist</a>
            <a href="#contact" className="text-sm hover:text-primary transition-colors">Contact</a>
          </div>

          <Button variant="hero">Get Started for Free</Button>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
