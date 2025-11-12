import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

interface AdminCheckResponse {
  user_id: string;
  is_admin: boolean;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Hook to check if current user is admin
 * Uses lightweight /admin/check endpoint instead of fetching full stats
 */
export function useAdminCheck() {
  return useQuery<AdminCheckResponse>({
    queryKey: ["admin-check"],
    queryFn: async () => {
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/check`, {
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
        },
      });
      
      if (response.status === 403) {
        return { user_id: session?.user?.id || '', is_admin: false };
      }
      
      if (!response.ok) {
        throw new Error("Failed to check admin status");
      }
      
      return response.json();
    },
    retry: 1,
    staleTime: 5 * 60 * 1000, // Consider admin status fresh for 5 minutes
  });
}

