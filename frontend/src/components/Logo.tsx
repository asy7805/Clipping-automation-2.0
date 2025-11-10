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
  useImage = false,
  imageSrc = "/logo.svg"
}: LogoProps) => {
  const sizeClasses = {
    sm: "w-8 h-8",
    md: "w-12 h-12",
    lg: "w-16 h-16"
  };

  const textSizeClasses = {
    sm: "text-lg",
    md: "text-xl",
    lg: "text-2xl"
  };

  // If using image file, render that instead
  if (useImage) {
    return (
      <div className={cn("flex items-center gap-3", className)}>
        <img 
          src={imageSrc} 
          alt="Prism Logo" 
          className={cn(sizeClasses[size], "object-contain")}
        />
        {showText && (
          <span className={cn("font-bold text-foreground", textSizeClasses[size])}>
            Prism
          </span>
        )}
      </div>
    );
  }

  return (
    <div className={cn("flex items-center gap-3", className)}>
      {/* Logo Graphic - Play button + Scissors + Sparkle */}
      <div className={cn("relative flex items-center justify-center", sizeClasses[size])}>
        <svg
          viewBox="0 0 24 24"
          className="w-full h-full"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Play button triangle - off-white */}
          <path
            d="M8 5L16 12L8 19V5Z"
            fill="#F5F5DC"
            className="drop-shadow-lg"
          />
          
          {/* Scissors outline - light teal */}
          <g stroke="#4DD0E1" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none">
            {/* Left handle */}
            <path d="M6 7C6 7 7 6 8 6C9 6 10 7 10 8C10 9 9 10 8 10C7 10 6 9 6 8" />
            {/* Right handle */}
            <path d="M18 7C18 7 17 6 16 6C15 6 14 7 14 8C14 9 15 10 16 10C17 10 18 9 18 8" />
            {/* Blade connection */}
            <path d="M10 8L12 12M14 8L12 12" />
            {/* Handles to center */}
            <path d="M6 8L12 12M18 8L12 12" />
          </g>
          
          {/* Sparkle - light teal, positioned top-right */}
          <g transform="translate(16, 4)">
            <path
              d="M2 2L3 4L4 2M2 4L4 4M3 1L3 3"
              stroke="#4DD0E1"
              strokeWidth="1.2"
              strokeLinecap="round"
              fill="none"
            />
          </g>
        </svg>
      </div>
      
      {/* Wordmark */}
      {showText && (
        <span className={cn("font-bold text-foreground", textSizeClasses[size])}>
          Prism
        </span>
      )}
    </div>
  );
};

