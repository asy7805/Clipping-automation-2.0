import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { VideoPlayerProvider } from "./contexts/VideoPlayerContext";
import { VideoPlayerModal } from "./components/VideoPlayerModal";
import { useVideoPlayer } from "./contexts/VideoPlayerContext";
import { ErrorBoundary } from "./components/ErrorBoundary";
import Index from "./pages/Index";
import Dashboard from "./pages/Dashboard";
import Clips from "./pages/Clips";
import Analytics from "./pages/Analytics";
import Settings from "./pages/Settings";
import NotFound from "./pages/NotFound";
import { DashboardLayout } from "./components/DashboardLayout";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function AppContent() {
  const { currentClip, isOpen, closePlayer } = useVideoPlayer();
  
  return (
    <>
      <Toaster />
      <Sonner />
      <Routes>
        {/* Landing page without dashboard layout */}
        <Route path="/" element={<Index />} />
        
        {/* Dashboard routes with layout */}
        <Route path="/dashboard" element={<DashboardLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="clips" element={<Clips />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        
        {/* 404 page */}
        <Route path="*" element={<NotFound />} />
      </Routes>

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
    <ErrorBoundary>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <QueryClientProvider client={queryClient}>
          <TooltipProvider>
            <VideoPlayerProvider>
              <AppContent />
            </VideoPlayerProvider>
          </TooltipProvider>
        </QueryClientProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
