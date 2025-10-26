-- Temporary RLS Bypass for MVP Testing
-- WARNING: This disables row-level security for social media tables
-- Only use this for local development/testing
-- Re-enable RLS before production deployment

-- Disable RLS on social_accounts table
ALTER TABLE social_accounts DISABLE ROW LEVEL SECURITY;

-- Disable RLS on posting_queue table
ALTER TABLE posting_queue DISABLE ROW LEVEL SECURITY;

-- To re-enable later, run:
-- ALTER TABLE social_accounts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE posting_queue ENABLE ROW LEVEL SECURITY;

