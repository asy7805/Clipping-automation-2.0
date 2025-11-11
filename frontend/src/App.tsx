import { lazy, Suspense } from "react";
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
import { DashboardLayout } from "./components/DashboardLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Loader2 } from "lucide-react";

// Lazy load all pages for code splitting
const Index = lazy(() => import("./pages/Index"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Clips = lazy(() => import("./pages/Clips"));
const StreamerClips = lazy(() => import("./pages/StreamerClips"));
const Analytics = lazy(() => import("./pages/Analytics"));
const SocialAccounts = lazy(() => import("./pages/SocialAccounts"));
const Settings = lazy(() => import("./pages/Settings"));
const Admin = lazy(() => import("./pages/Admin"));
const Login = lazy(() => import("./pages/auth/Login"));
const SignUp = lazy(() => import("./pages/auth/SignUp"));
const ForgotPassword = lazy(() => import("./pages/auth/ForgotPassword"));
const ResetPassword = lazy(() => import("./pages/auth/ResetPassword"));
const TikTokCallback = lazy(() => import("./pages/auth/TikTokCallback"));
const YouTubeCallback = lazy(() => import("./pages/auth/YouTubeCallback"));
const NotFound = lazy(() => import("./pages/NotFound"));

// Loading fallback component
const PageLoader = () => (
  <div className="min-h-screen flex items-center justify-center bg-background">
    <div className="text-center space-y-4">
      <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
      <p className="text-sm text-muted-foreground">Loading...</p>
    </div>
  </div>
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30000, // Consider data fresh for 30s
      gcTime: 5 * 60 * 1000, // Keep cache for 5 minutes (was cacheTime)
      refetchOnMount: false, // Use cache if available
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
      <Suspense fallback={<PageLoader />}>
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
      </Suspense>

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
