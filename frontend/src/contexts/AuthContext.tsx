import { createContext, useContext, useEffect, useState, useCallback, ReactNode, useRef } from 'react';
import { User } from '@supabase/supabase-js';
import { supabase } from '@/lib/supabase';
import { toast } from 'sonner';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<{ error: Error | null }>;
  signUp: (email: string, password: string) => Promise<{ error: Error | null }>;
  signOut: () => Promise<void>;
  isAuthenticated: boolean;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const ADMIN_CHECK_ENABLED =
  import.meta.env.VITE_ENABLE_ADMIN_CHECK !== "false" &&
  import.meta.env.VITE_ENABLE_ADMIN_CHECK !== "0";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const adminCheckInProgress = useRef(false);
  const lastAdminCheckRef = useRef<number>(0);
  const ADMIN_CHECK_COOLDOWN_MS = 10000;

  // Function to check admin status from backend (non-blocking)
  const checkAdminStatus = useCallback(async (userId: string) => {
    if (!ADMIN_CHECK_ENABLED) {
      setIsAdmin(false);
      return;
    }

    const now = Date.now();
    if (adminCheckInProgress.current) {
      console.debug('⏳ Admin check already in progress, skipping duplicate call');
      return;
    }

    if (now - lastAdminCheckRef.current < ADMIN_CHECK_COOLDOWN_MS) {
      console.debug('🛑 Admin check skipped due to cooldown');
      return;
    }

    lastAdminCheckRef.current = now;

    console.log('🔍 Checking admin status for user:', userId);

    const apiBaseUrl = import.meta.env.VITE_API_URL;
    if (!apiBaseUrl) {
      console.warn('⚠️ VITE_API_URL not set, skipping admin check');
      setIsAdmin(false);
      adminCheckInProgress.current = false;
      return;
    }

    adminCheckInProgress.current = true;

    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        console.log('❌ No session token, setting isAdmin = false');
        setIsAdmin(false);
        return;
      }

      // Add timeout to prevent hanging
      const controller = new AbortController();
      timeoutId = setTimeout(() => {
        console.warn('⏱️ Admin check timed out after 5 seconds');
        controller.abort();
      }, 5000); // 5 second timeout

      console.log('📡 Calling /api/v1/admin/check...');
      const startTime = performance.now();
      
      // Use the faster /admin/check endpoint instead of /admin/stats
      const response = await fetch(`${apiBaseUrl}/api/v1/admin/check`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
        signal: controller.signal,
      });

      const elapsed = performance.now() - startTime;
      console.log(`⏱️ Admin check took ${elapsed.toFixed(0)}ms`);
      
      clearTimeout(timeoutId);
      
      if (response.ok) {
        const data = await response.json();
        console.log('✅ Admin check response:', data);
        setIsAdmin(data.is_admin === true);
      } else {
        console.log(`❌ Admin check failed with status ${response.status}`);
        setIsAdmin(false);
      }
    } catch (error) {
      // Always set isAdmin to false on error
      setIsAdmin(false);
      
      // Log errors for debugging
      if (error instanceof Error && error.name === 'AbortError') {
        console.warn('⏱️ Admin check timed out after 5 seconds - backend may be slow or unreachable');
      } else {
        console.error('❌ Error checking admin status:', error);
      }
    } finally {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      adminCheckInProgress.current = false;
    }
  }, []);

  useEffect(() => {
    // Check active session on mount
    const initializeAuth = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession();
        
        if (error) {
          console.error('Error getting session:', error);
          // Clear any stale sessions on error
          await supabase.auth.signOut();
          setUser(null);
          setIsAdmin(false);
        } else {
          const currentUser = session?.user ?? null;
          setUser(currentUser);
          
          // Check admin status if user is logged in (non-blocking)
          if (currentUser) {
            checkAdminStatus(currentUser.id); // Don't await - let it run in background
          } else {
            setIsAdmin(false);
          }
        }
      } catch (error) {
        console.error('Error initializing auth:', error);
        // Clear localStorage on network errors
        try {
          await supabase.auth.signOut();
        } catch (signOutError) {
          // If signOut fails, clear localStorage manually
          localStorage.removeItem('supabase.auth.token');
        }
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log('Auth state changed:', event);
        
        // Handle TOKEN_REFRESHED errors
        if (event === 'TOKEN_REFRESHED' && !session) {
          console.warn('Token refresh failed, signing out');
          setUser(null);
          setIsAdmin(false);
          return;
        }
        
        const currentUser = session?.user ?? null;
        setUser(currentUser);
        setLoading(false);

        // Check admin status on sign in (non-blocking)
        if (currentUser && (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED')) {
          checkAdminStatus(currentUser.id); // Don't await - let it run in background
        } else if (!currentUser) {
          setIsAdmin(false);
        }

        // Handle different auth events (only show toast for user-initiated actions)
        if (event === 'SIGNED_IN') {
          toast.success('Welcome back!');
        } else if (event === 'SIGNED_OUT') {
          setIsAdmin(false);
          // Don't show toast if it was an automatic sign-out
          if (session === null) {
            toast.success('Signed out successfully');
          }
        } else if (event === 'USER_UPDATED') {
          toast.success('Profile updated');
        } else if (event === 'PASSWORD_RECOVERY') {
          toast.info('Check your email for password reset instructions');
        }
      }
    );

    return () => {
      subscription.unsubscribe();
    };
  }, [checkAdminStatus]);

  const signIn = async (email: string, password: string) => {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        // Provide user-friendly error messages
        if (error.message.includes('Email not confirmed')) {
          toast.error('Please confirm your email address before signing in. Check your inbox!');
        } else if (error.message.includes('Invalid login credentials')) {
          toast.error('Invalid email or password. Please try again.');
        } else if (error.message.includes('rate limit')) {
          toast.error('Too many attempts. Please wait a few minutes and try again.');
        } else {
          toast.error(error.message);
        }
        return { error };
      }

      setUser(data.user);
      return { error: null };
    } catch (error: any) {
      toast.error(error.message || 'An unexpected error occurred');
      return { error };
    }
  };

  const signUp = async (email: string, password: string) => {
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/dashboard`,
        },
      });

      if (error) {
        // Handle specific signup errors
        if (error.message.includes('rate limit')) {
          toast.error('Too many signup attempts. Please wait 10 minutes and try again.');
        } else if (error.message.includes('already registered')) {
          toast.error('This email is already registered. Try signing in instead.');
        } else {
          toast.error(error.message);
        }
        return { error };
      }

      if (data.user) {
        // Check if email confirmation is required
        if (data.user.email_confirmed_at) {
          toast.success('Account created! You can now sign in.');
        } else {
          toast.success('Account created! Check your email to verify your account before signing in.', {
            duration: 7000,
          });
        }
      }

      return { error: null };
    } catch (error: any) {
      toast.error(error.message || 'An unexpected error occurred');
      return { error };
    }
  };

  const signOut = async () => {
    try {
      const { error } = await supabase.auth.signOut();
      if (error) {
        toast.error(error.message);
        return;
      }
      setUser(null);
      setIsAdmin(false);
    } catch (error: any) {
      toast.error(error.message || 'Error signing out');
    }
  };

  const value: AuthContextType = {
    user,
    loading,
    signIn,
    signUp,
    signOut,
    isAuthenticated: !!user,
    isAdmin,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

