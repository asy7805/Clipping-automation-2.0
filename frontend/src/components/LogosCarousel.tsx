import { Marquee } from "@/components/ui/marquee";

const LogosCarousel = () => {
  const logos = [
    { name: "Nova", symbol: "△" },
    { name: "Stellar", symbol: "✦" },
    { name: "Fusion", symbol: "≋" },
    { name: "Synergy", symbol: "⚡" },
    { name: "Apex", symbol: "◈" },
    { name: "Quantum", symbol: "◉" },
  ];

  return (
    <section className="py-16 overflow-hidden">
      <Marquee pauseOnHover className="[--duration:40s]">
        {logos.map((logo, index) => (
            <div
              key={index}
            className="flex items-center gap-3 opacity-40 hover:opacity-100 transition-opacity whitespace-nowrap mx-8"
            >
              <span className="text-2xl">{logo.symbol}</span>
              <span className="text-lg font-semibold">{logo.name}</span>
            </div>
          ))}
      </Marquee>
    </section>
  );
};

export default LogosCarousel;
