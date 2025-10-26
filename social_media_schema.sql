-- Social Media Automation Database Schema
-- Run this in Supabase SQL Editor

-- Social Media Accounts Table
CREATE TABLE IF NOT EXISTS social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('tiktok', 'youtube')),
    account_id VARCHAR(255) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, platform, account_id)
);

-- Posting Queue Table
CREATE TABLE IF NOT EXISTS posting_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id VARCHAR(255) NOT NULL,
    user_id UUID REFERENCES auth.users(id),
    social_account_id UUID REFERENCES social_accounts(id),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'posted', 'failed', 'cancelled')),
    scheduled_at TIMESTAMP,
    posted_at TIMESTAMP,
    post_url TEXT,
    caption TEXT,
    platform_specific_data JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_posting_queue_status ON posting_queue(status);
CREATE INDEX IF NOT EXISTS idx_posting_queue_scheduled ON posting_queue(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_posting_queue_user ON posting_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_social_accounts_user ON social_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_social_accounts_platform ON social_accounts(platform);

-- Row Level Security (RLS) Policies
ALTER TABLE social_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE posting_queue ENABLE ROW LEVEL SECURITY;

-- Users can only see their own social accounts
CREATE POLICY "Users can view own social accounts" ON social_accounts
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own social accounts" ON social_accounts
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own social accounts" ON social_accounts
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own social accounts" ON social_accounts
    FOR DELETE USING (auth.uid() = user_id);

-- Users can only see their own posting queue
CREATE POLICY "Users can view own posting queue" ON posting_queue
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own posting queue" ON posting_queue
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own posting queue" ON posting_queue
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own posting queue" ON posting_queue
    FOR DELETE USING (auth.uid() = user_id);

-- Functions for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_social_accounts_updated_at 
    BEFORE UPDATE ON social_accounts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_posting_queue_updated_at 
    BEFORE UPDATE ON posting_queue 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
