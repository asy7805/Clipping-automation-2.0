import { createContext, useContext, useState, ReactNode } from "react";
import { Clip } from "@/hooks/useClips";

interface VideoPlayerContextType {
  currentClip: Clip | null;
  isOpen: boolean;
  openPlayer: (clip: Clip) => void;
  closePlayer: () => void;
  playNext?: () => void;
  playPrevious?: () => void;
}

const VideoPlayerContext = createContext<VideoPlayerContextType | undefined>(undefined);

export function VideoPlayerProvider({ children }: { children: ReactNode }) {
  const [currentClip, setCurrentClip] = useState<Clip | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const openPlayer = (clip: Clip) => {
    setCurrentClip(clip);
    setIsOpen(true);
  };

  const closePlayer = () => {
    setIsOpen(false);
    setCurrentClip(null);
  };

  return (
    <VideoPlayerContext.Provider
      value={{
        currentClip,
        isOpen,
        openPlayer,
        closePlayer,
      }}
    >
      {children}
    </VideoPlayerContext.Provider>
  );
}

export function useVideoPlayer() {
  const context = useContext(VideoPlayerContext);
  if (!context) {
    throw new Error("useVideoPlayer must be used within VideoPlayerProvider");
  }
  return context;
}

