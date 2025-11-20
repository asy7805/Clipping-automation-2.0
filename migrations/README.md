# Database Migrations

## Running Migrations

1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Copy and paste the contents of `001_subscription_credit_system.sql`
4. Execute the SQL

## Migration Files

### 001_subscription_credit_system.sql

Creates the subscription and credit system schema:

- `subscription_tier` enum type
- `user_profiles` table (extends auth.users with subscription info)
- `credit_transactions` table (tracks all credit operations)
- Adds `expires_at` and `has_watermark` columns to `clips_metadata`
- Adds `session_started_at` column to `monitors` table
- Sets up Row Level Security (RLS) policies

## Post-Migration Steps

After running the migration:

1. Grant trial credits to existing users (if needed):
   ```python
   from src.api.services.credit_service import grant_trial_credits
   grant_trial_credits(user_id)
   ```

2. Set up cron jobs for cleanup and renewal:
   - `scripts/cleanup_expired_clips.py` - Run daily at 2 AM
   - `scripts/process_pro_renewals.py` - Run daily at 1 AM

3. Test the subscription endpoints:
   - `GET /api/v1/subscription/status` - Get subscription status
   - `POST /api/v1/subscription/claim-trial` - Claim trial credits
   - `GET /api/v1/subscription/transactions` - View credit transactions

