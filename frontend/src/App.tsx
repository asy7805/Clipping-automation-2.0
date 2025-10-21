import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { VideoPlayerProvider } from "./contexts/VideoPlayerContext";
import { VideoPlayerModal } from "./components/VideoPlayerModal";
import { useVideoPlayer } from "./contexts/VideoPlayerContext";
import Index from "./pages/Index";
import Dashboard from "./pages/Dashboard";
import Clips from "./pages/Clips";
import Analytics from "./pages/Analytics";
import Settings from "./pages/Settings";
import NotFound from "./pages/NotFound";
import { DashboardLayout } from "./components/DashboardLayout";

const queryClient = new QueryClient();

function AppContent() {
  const { currentClip, isOpen, closePlayer } = useVideoPlayer();
  
  return (
    <>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          {/* Landing page without dashboard layout */}
          <Route path="/" element={<Index />} />
          
          {/* Dashboard routes with layout */}
          <Route element={<DashboardLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/dashboard/clips" element={<Clips />} />
            <Route path="/dashboard/analytics" element={<Analytics />} />
            <Route path="/dashboard/settings" element={<Settings />} />
          </Route>
          
          {/* 404 page */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>

      {/* Global Video Player Modal */}
      {isOpen && currentClip && (
        <VideoPlayerModal
          clipId={currentClip.id}
          onClose={closePlayer}
          clipData={currentClip}
        />
      )}
    </>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <VideoPlayerProvider>
          <AppContent />
        </VideoPlayerProvider>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
