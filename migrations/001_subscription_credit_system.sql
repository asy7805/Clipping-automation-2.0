-- Migration: Subscription and Credit System
-- Run this in Supabase SQL Editor

-- 1. Create subscription_tier enum type
DO $$ BEGIN
    CREATE TYPE subscription_tier AS ENUM ('free_trial', 'pro', 'pay_as_you_go', 'expired');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. Create user_profiles table (if users table doesn't exist or can't be modified)
-- This table extends auth.users with subscription information
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    subscription_tier subscription_tier NOT NULL DEFAULT 'free_trial',
    credits_remaining INTEGER NOT NULL DEFAULT 0,
    trial_used BOOLEAN NOT NULL DEFAULT false,
    subscription_started_at TIMESTAMP WITH TIME ZONE,
    subscription_expires_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE, -- For Pro cancellations (active until expires_at)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Create credit_transactions table
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL, -- negative for usage, positive for grants/purchases
    transaction_type VARCHAR(50) NOT NULL, -- 'clip_created', 'trial_granted', 'purchase', 'pro_monthly_reset'
    description TEXT,
    clip_id UUID REFERENCES clips_metadata(id) ON DELETE SET NULL, -- nullable, for clip_created transactions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Create indexes for credit_transactions
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_created_at ON credit_transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_type ON credit_transactions(transaction_type);

-- 5. Add columns to clips_metadata table (if they don't exist)
DO $$ 
BEGIN
    -- Add expires_at column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'clips_metadata' AND column_name = 'expires_at'
    ) THEN
        ALTER TABLE clips_metadata ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE;
    END IF;
    
    -- Add has_watermark column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'clips_metadata' AND column_name = 'has_watermark'
    ) THEN
        ALTER TABLE clips_metadata ADD COLUMN has_watermark BOOLEAN NOT NULL DEFAULT false;
    END IF;
END $$;

-- 6. Add session_started_at to monitors table (if it doesn't exist)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'monitors' AND column_name = 'session_started_at'
    ) THEN
        ALTER TABLE monitors ADD COLUMN session_started_at TIMESTAMP WITH TIME ZONE;
    END IF;
END $$;

-- 7. Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 8. Create trigger for user_profiles updated_at
DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 9. Enable Row Level Security (RLS) on user_profiles
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- 10. Create RLS policies for user_profiles
-- Users can read their own profile
CREATE POLICY "Users can view own profile" ON user_profiles
    FOR SELECT
    USING (auth.uid() = id);

-- Users can update their own profile (limited fields)
CREATE POLICY "Users can update own profile" ON user_profiles
    FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- 11. Enable RLS on credit_transactions
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;

-- 12. Create RLS policies for credit_transactions
-- Users can view their own transactions
CREATE POLICY "Users can view own transactions" ON credit_transactions
    FOR SELECT
    USING (auth.uid() = user_id);

-- Note: Insert/update of credit_transactions should be done server-side with service role key
-- to prevent users from manipulating their own credits

-- 13. Create index on clips_metadata expires_at for cleanup queries
CREATE INDEX IF NOT EXISTS idx_clips_metadata_expires_at ON clips_metadata(expires_at) 
WHERE expires_at IS NOT NULL;

-- 14. Create index on user_profiles subscription_expires_at for renewal queries
CREATE INDEX IF NOT EXISTS idx_user_profiles_expires_at ON user_profiles(subscription_expires_at) 
WHERE subscription_expires_at IS NOT NULL;

