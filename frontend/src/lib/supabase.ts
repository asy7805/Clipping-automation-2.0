import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || ''
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

// Validate environment variables
if (!supabaseUrl || !supabaseAnonKey) {
  console.error('❌ Supabase configuration missing!', {
    url: supabaseUrl ? '✅ Set' : '❌ Missing',
    key: supabaseAnonKey ? '✅ Set' : '❌ Missing',
  });
}

// Create Supabase client with better error handling
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    // Automatically refresh the session when it expires
    autoRefreshToken: true,
    // Persist the session in localStorage
    persistSession: true,
    // Detect session from URL (for OAuth callbacks)
    detectSessionInUrl: true,
    // Storage options
    storage: typeof window !== 'undefined' ? window.localStorage : undefined,
    // Reduce retry attempts on network failures
    flowType: 'pkce',
  },
  global: {
    headers: {
      'X-Client-Info': 'ascension-clips-frontend',
    },
  },
})

// Test Supabase connection on initialization
if (typeof window !== 'undefined' && supabaseUrl && supabaseAnonKey) {
  supabase.auth.getSession()
    .then(({ data, error }) => {
      if (error) {
        console.warn('⚠️ Supabase session check failed:', error.message);
      } else {
        console.log('✅ Supabase connection OK');
      }
    })
    .catch((err) => {
      console.error('❌ Supabase connection error:', err);
    });
}

