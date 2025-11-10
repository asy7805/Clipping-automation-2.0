import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { VideoPlayerProvider } from "./contexts/VideoPlayerContext";
import { FFmpegProvider } from "./contexts/FFmpegContext";
import { AuthProvider } from "./contexts/AuthContext";
import { VideoPlayerModal } from "./components/VideoPlayerModal";
import { useVideoPlayer } from "./contexts/VideoPlayerContext";
import { ErrorBoundary } from "./components/ErrorBoundary";
import Index from "./pages/Index";
import Dashboard from "./pages/Dashboard";
import Clips from "./pages/Clips";
import { StreamerClips } from "./pages/StreamerClips";
import Analytics from "./pages/Analytics";
import SocialAccounts from "./pages/SocialAccounts";
import Settings from "./pages/Settings";
import Admin from "./pages/Admin";
import TikTokCallback from "./pages/auth/TikTokCallback";
import YouTubeCallback from "./pages/auth/YouTubeCallback";
import Login from "./pages/auth/Login";
import SignUp from "./pages/auth/SignUp";
import ForgotPassword from "./pages/auth/ForgotPassword";
import ResetPassword from "./pages/auth/ResetPassword";
import NotFound from "./pages/NotFound";
import { DashboardLayout } from "./components/DashboardLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";

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
  const location = useLocation();
  
  const shouldShowVideoPlayer = isOpen && currentClip;
  
  return (
    <>
      <Toaster />
      <Sonner />
      <Routes>
        {/* Landing page without dashboard layout */}
        <Route path="/" element={<Index />} />
        
        {/* Auth routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<SignUp />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        
        {/* Dashboard routes with layout - Protected */}
        <Route path="/dashboard" element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }>
          <Route index element={<Dashboard />} />
          <Route path="clips" element={<Clips />} />
          <Route path="clips/:streamerName" element={<StreamerClips />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="social" element={<SocialAccounts />} />
          <Route path="settings" element={<Settings />} />
          <Route path="admin" element={<Admin />} />
        </Route>
        
        {/* OAuth callback routes */}
        <Route path="/auth/tiktok/callback" element={<TikTokCallback />} />
        <Route path="/auth/youtube/callback" element={<YouTubeCallback />} />
        
        {/* 404 page */}
        <Route path="*" element={<NotFound />} />
      </Routes>

      {/* Global Video Player Modal */}
      {shouldShowVideoPlayer && (
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
        <AuthProvider>
          <QueryClientProvider client={queryClient}>
            <TooltipProvider>
              <FFmpegProvider>
                <VideoPlayerProvider>
                  <AppContent />
                </VideoPlayerProvider>
              </FFmpegProvider>
            </TooltipProvider>
          </QueryClientProvider>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
