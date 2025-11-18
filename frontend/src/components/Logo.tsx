import { cn } from "@/lib/utils";

interface LogoProps {
  className?: string;
  showText?: boolean;
  size?: "sm" | "md" | "lg";
  useImage?: boolean;
  imageSrc?: string;
}

export const Logo = ({ 
  className, 
  showText = true, 
  size = "lg",
  useImage = true,  // Default to using image file
  imageSrc = "/Ascension Clips Logo.png"  // Your uploaded logo file
}: LogoProps) => {
  const sizeClasses = {
    sm: "w-10 h-10",
    md: "w-16 h-16",
    lg: "w-20 h-20"
  };

  const textSizeClasses = {
    sm: "text-lg",
    md: "text-xl",
    lg: "text-2xl"
  };

  // Use image file by default - place your logo at public/logo.svg or public/logo.png
  if (useImage) {
    return (
      <div className={cn("flex items-center gap-3", className)}>
        {/* Glow effect wrapper */}
        <div className="relative group">
          {/* Outer glow layer - animated pulse */}
          <div 
            className={cn(
              "absolute inset-0 rounded-full",
              "bg-gradient-to-br from-primary/40 via-primary/20 to-primary/10",
              "blur-2xl opacity-70 animate-pulse",
              sizeClasses[size],
              "-z-0"
            )}
            style={{
              transform: "scale(1.3)",
              animationDuration: "3s"
            }}
          />
          {/* Inner glow layer - subtle constant glow */}
          <div 
            className={cn(
              "absolute inset-0 rounded-full",
              "bg-primary/30 blur-xl opacity-50",
              sizeClasses[size],
              "-z-0"
            )}
            style={{
              transform: "scale(1.15)"
            }}
          />
          {/* Logo image with enhanced styling */}
          <img 
            src={imageSrc} 
            alt="AscensionClips Logo" 
            className={cn(
              sizeClasses[size], 
              "object-contain relative z-10",
              "drop-shadow-2xl shadow-[0_0_30px_rgba(var(--primary)/0.5)]",
              "transition-all duration-500 ease-in-out",
              "group-hover:drop-shadow-[0_0_40px_rgba(var(--primary)/0.7)]",
              "group-hover:scale-105",
              "brightness-110 contrast-105"
            )}
          />
        </div>
        {showText && (
          <span className={cn(
            "font-bold text-foreground relative",
            "bg-gradient-to-r from-foreground to-foreground/80 bg-clip-text",
            textSizeClasses[size],
            "drop-shadow-sm"
          )}>
            AscensionClips
          </span>
        )}
      </div>
    );
  }

  return (
    <div className={cn("flex items-center gap-3", className)}>
      {/* Logo Graphic - Mountain with Play Button + Ascending Arrow */}
      <div className={cn("relative flex items-center justify-center", sizeClasses[size])}>
        <svg
          viewBox="0 0 40 40"
          className="w-full h-full"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            {/* Mask for play button cutout */}
            <mask id="mountainMask">
              <rect width="40" height="40" fill="white" />
              <path d="M27 28 L29.5 28 L28.25 26.5 Z" fill="black" />
            </mask>
          </defs>
          
          {/* Ascending Arrow/Path - curves upward from lower-left, sweeps right */}
          <path
            d="M6 30 Q8 26, 10 22 Q12 18, 14 16 Q16 14, 18 13 Q20 12, 22 11.5 Q24 11, 26 10.5"
            stroke="#006B7D"
            strokeWidth="2.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />
          
          {/* Arrow tip pointing upward-right */}
          <path
            d="M24.5 10 L27 10.5 L25.5 12.5"
            stroke="#006B7D"
            strokeWidth="2.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />
          
          {/* Jagged base/small peak for ascending path */}
          <path
            d="M6 30 L7 32 L6.5 34 L8 34 L6 30"
            fill="#006B7D"
            opacity="0.9"
          />
          
          {/* Main Mountain Peak - large triangle on right with play button cutout */}
          <path
            d="M18 34 L32 34 L26 16 Z"
            fill="#006B7D"
            mask="url(#mountainMask)"
          />
        </svg>
      </div>
      
      {/* Wordmark */}
      {showText && (
        <span className={cn("font-bold text-foreground", textSizeClasses[size])}>
          AscensionClips
        </span>
      )}
    </div>
  );
};

