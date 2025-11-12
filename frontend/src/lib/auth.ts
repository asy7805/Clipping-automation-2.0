import { supabase } from './supabase'
import { toast } from 'sonner'
import { User, AuthError } from '@supabase/supabase-js'

export interface AuthResponse {
  data: { user: User | null } | null;
  error: AuthError | null;
}

export const signIn = async (email: string, password: string): Promise<AuthResponse> => {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  })
  
  if (error) {
    toast.error(error.message)
    return { data: null, error }
  }
  
  toast.success('Welcome back!')
  return { data, error: null }
}

export const signUp = async (email: string, password: string): Promise<AuthResponse> => {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      emailRedirectTo: `${window.location.origin}/dashboard`,
    },
  })

  if (error) {
    toast.error(error.message)
    return { data: null, error }
  }

  if (data.user) {
    toast.success('Account created! Check your email to verify your account.')
  }

  return { data, error: null }
}

export const signOut = async () => {
  const { error } = await supabase.auth.signOut()
  if (error) {
    toast.error(error.message)
  }
  return { error }
}

export const getCurrentUser = async (): Promise<User | null> => {
  const { data: { user } } = await supabase.auth.getUser()
  return user
}

export const resetPassword = async (email: string) => {
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${window.location.origin}/reset-password`,
  })

  if (error) {
    toast.error(error.message)
    return { error }
  }

  toast.success('Password reset email sent!')
  return { error: null }
}

export const updatePassword = async (newPassword: string) => {
  const { error } = await supabase.auth.updateUser({
    password: newPassword,
  })

  if (error) {
    toast.error(error.message)
    return { error }
  }

  toast.success('Password updated successfully!')
  return { error: null }
}

export const getSession = async () => {
  const { data: { session }, error } = await supabase.auth.getSession()
  return { session, error }
}

