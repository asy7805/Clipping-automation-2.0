import Navigation from "@/components/Navigation";
import Hero from "@/components/Hero";
import LogosCarousel from "@/components/LogosCarousel";
import Features from "@/components/Features";
import Benefits from "@/components/Benefits";
import Process from "@/components/Process";
import Testimonials from "@/components/Testimonials";
import Pricing from "@/components/Pricing";
import Comparison from "@/components/Comparison";
import FAQ from "@/components/FAQ";
import CTA from "@/components/CTA";
import Footer from "@/components/Footer";

const Index = () => {
  return (
    <div className="min-h-screen">
      <Navigation />
      <Hero />
      <LogosCarousel />
      <Features />
      <Benefits />
      <Process />
      <Testimonials />
      <Pricing />
      <Comparison />
      <FAQ />
      <CTA />
      <Footer />
    </div>
  );
};

export default Index;
