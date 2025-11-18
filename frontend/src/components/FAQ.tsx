import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const FAQ = () => {
  const faqs = [
    {
      question: "Do I need to know how to code to use this?",
      answer: "Not at all. Our builder is 100% no-code — just drag, drop, and launch workflows in minutes. Your entire team can build automations without touching a single line of code."
    },
    {
      question: "Can this actually replace my project management tool?",
      answer: "Yes — and it integrates with your existing tools if you're not ready to switch. Whether you use Jira, Trello, Asana, or ClickUp, our AI can sit on top of your workflow or completely take over as your main project hub."
    },
    {
      question: "How secure is my company data?",
      answer: "Extremely secure. We are SOC 2 Type II compliant, use bank-grade encryption, and follow strict role-based access control so your data stays private — always."
    },
    {
      question: "How quickly can we get set up?",
      answer: "Lightning fast. Most teams are fully onboarded and running automations in under 30 minutes. We also offer step-by-step guided setup and live chat support to get you going even faster."
    },
    {
      question: "What happens if my team grows — do I need to migrate later?",
      answer: "No migration headaches here. You can upgrade plans instantly as your team scales. All your workflows, data, and analytics stay intact — just add more seats and keep moving."
    }
  ];

  return (
    <section id="faq" className="py-24 px-6 relative overflow-hidden">
      <div className="absolute inset-0 opacity-10">
        <div className="absolute bottom-1/4 right-1/3 w-96 h-96 bg-accent/20 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto relative z-10 max-w-3xl">
        <div className="text-center mb-16">
          <Badge variant="outline" className="mb-4">FAQs</Badge>
          <h2 className="text-4xl md:text-5xl font-bold mb-4">
            Frequently Asked Questions
          </h2>
          <p className="text-lg text-muted-foreground">
            Find quick answers to the most common support questions.
          </p>
        </div>

        <Accordion type="single" collapsible className="w-full space-y-4">
          {faqs.map((faq, index) => (
            <AccordionItem 
              key={index} 
              value={`item-${index}`}
              className="glass border-border/50 rounded-lg px-6 hover:bg-card/50 transition-colors"
            >
              <AccordionTrigger className="text-left hover:no-underline py-6">
                <span className="font-semibold">{faq.question}</span>
              </AccordionTrigger>
              <AccordionContent className="text-muted-foreground pb-6">
                {faq.answer}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
};

export default FAQ;
