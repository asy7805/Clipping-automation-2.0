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
      <div className="relative">
        <div className="flex animate-scroll gap-16">
          {[...logos, ...logos, ...logos].map((logo, index) => (
            <div
              key={index}
              className="flex items-center gap-3 opacity-40 hover:opacity-100 transition-opacity whitespace-nowrap"
            >
              <span className="text-2xl">{logo.symbol}</span>
              <span className="text-lg font-semibold">{logo.name}</span>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        @keyframes scroll {
          0% {
            transform: translateX(0);
          }
          100% {
            transform: translateX(-33.333%);
          }
        }

        .animate-scroll {
          animation: scroll 30s linear infinite;
          width: max-content;
        }

        .animate-scroll:hover {
          animation-play-state: paused;
        }
      `}</style>
    </section>
  );
};

export default LogosCarousel;
