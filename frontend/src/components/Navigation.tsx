import { Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/Logo";

const Navigation = () => {
  const location = useLocation();
  
  const handleNavClick = (e: React.MouseEvent<HTMLAnchorElement>, sectionId: string) => {
    e.preventDefault();
    
    // If not on home page, navigate to home first
    if (location.pathname !== '/') {
      window.location.href = `/#${sectionId}`;
      return;
    }
    
    // Otherwise, smooth scroll to section
    const element = document.getElementById(sectionId);
    if (element) {
      const offset = 80; // Account for fixed navbar height
      const elementPosition = element.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - offset;
      
      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });
    }
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <Logo size="md" showText={true} />
          </Link>
          
          <div className="hidden md:flex items-center gap-8">
            <a 
              href="#home" 
              className="text-sm hover:text-primary transition-colors"
              onClick={(e) => handleNavClick(e, 'home')}
            >
              Home
            </a>
            <a 
              href="#features" 
              className="text-sm hover:text-primary transition-colors"
              onClick={(e) => handleNavClick(e, 'features')}
            >
              Features
            </a>
            <a 
              href="#benefits" 
              className="text-sm hover:text-primary transition-colors"
              onClick={(e) => handleNavClick(e, 'benefits')}
            >
              Benefits
            </a>
            <a 
              href="#how-it-works" 
              className="text-sm hover:text-primary transition-colors"
              onClick={(e) => handleNavClick(e, 'how-it-works')}
            >
              How It Works
            </a>
            <a 
              href="#pricing" 
              className="text-sm hover:text-primary transition-colors"
              onClick={(e) => handleNavClick(e, 'pricing')}
            >
              Pricing
            </a>
            <a 
              href="#faq" 
              className="text-sm hover:text-primary transition-colors"
              onClick={(e) => handleNavClick(e, 'faq')}
            >
              FAQ
            </a>
          </div>

          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/login">Sign In</Link>
            </Button>
            <Button variant="hero" asChild>
              <Link to="/signup">Get Started Free</Link>
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
