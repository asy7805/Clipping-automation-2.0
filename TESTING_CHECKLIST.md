# Testing Checklist - Subscription & Credit System

## ✅ Completed Implementation

1. **Admin Infinite Credits** ✅
   - Added `is_admin_user()` helper function to `credit_service.py`
   - Updated `get_user_credits()` to return 999999 for admin users
   - Updated `check_has_credits()` to always return True for admin users
   - Updated `deduct_credits()` to bypass deduction for admin users (still logs transaction)

2. **Backend Restart** ✅
   - Backend server restarted successfully
   - Subscription router is properly included in `main.py`
   - Health endpoint responding: `/api/v1/health`

## 🧪 Testing Required

### Backend API Endpoints

All endpoints require authentication (Bearer token). Test with a valid JWT token from Supabase Auth.

#### 1. Check Trial Status
```bash
GET /api/v1/subscription/check-trial
Headers: Authorization: Bearer <token>
```
**Expected Response:**
```json
{
  "trial_used": false,
  "credits_remaining": 0,
  "tier": "free_trial",
  "can_grant_trial": true
}
```

#### 2. Claim Trial Credits
```bash
POST /api/v1/subscription/claim-trial
Headers: Authorization: Bearer <token>
```
**Expected Response:**
```json
{
  "message": "Trial credits granted successfully",
  "credits_remaining": 20,
  "tier": "free_trial",
  "trial_used": true
}
```

#### 3. Get Subscription Status
```bash
GET /api/v1/subscription/status
Headers: Authorization: Bearer <token>
```
**Expected Response:**
```json
{
  "tier": "free_trial",
  "credits_remaining": 20,
  "trial_used": true,
  "subscription_started_at": "2025-11-20T...",
  "subscription_expires_at": null,
  "cancelled_at": null,
  "is_cancelled": false
}
```

#### 4. Get Credit Transactions
```bash
GET /api/v1/subscription/transactions
Headers: Authorization: Bearer <token>
```
**Expected Response:** Array of transaction objects

### Admin Credit Bypass Testing

#### Test Admin User Credits
1. **Get Credits (Admin):**
   - Admin user should see `999999` credits (infinite)
   - Non-admin user should see actual credit balance

2. **Check Has Credits (Admin):**
   - Admin user should always pass credit checks
   - Non-admin user should fail if credits < required

3. **Deduct Credits (Admin):**
   - Admin user should bypass deduction (no credits removed)
   - Transaction should still be logged with `[ADMIN BYPASS]` tag
   - Non-admin user should have credits deducted normally

### Integration Testing

#### 1. Clip Creation
- **Free Trial User:**
  - Should deduct 1 credit per clip
  - Should fail if credits = 0
  - Clip should be watermarked
  - Clip should have `expires_at` set to 30 days

- **Admin User:**
  - Should bypass credit check (infinite credits)
  - Should not deduct credits
  - Clip should NOT be watermarked
  - Clip should NOT have expiration

#### 2. Monitor Starting
- **Free Trial User:**
  - Should check credits before starting
  - Should fail if credits = 0
  - Should set `session_started_at` for 1-hour limit tracking

- **Admin User:**
  - Should bypass credit check
  - Should be able to start unlimited monitors
  - Should NOT have session limit

#### 3. Social Posting
- **Free Trial User:**
  - Should receive 403 error when trying to connect accounts
  - Should receive 403 error when trying to schedule posts

- **Pro User:**
  - Should be able to connect accounts
  - Should be able to schedule posts

- **Admin User:**
  - Should bypass Pro tier check (can use social posting)

## 📋 Manual Testing Steps

1. **Create Test Users:**
   - Free trial user (via Supabase Auth)
   - Admin user (add to `admin_users` table)

2. **Test Trial Flow:**
   - Sign up new user
   - Check trial status (should be `trial_used: false`)
   - Claim trial credits
   - Verify credits = 20
   - Check trial status again (should be `trial_used: true`)

3. **Test Credit Deduction:**
   - Create a clip (should deduct 1 credit)
   - Verify credits = 19
   - Create 19 more clips (should deduct to 0)
   - Try to create another clip (should fail)

4. **Test Admin Bypass:**
   - Login as admin user
   - Check credits (should be 999999)
   - Create clips (should not deduct credits)
   - Check transaction log (should show `[ADMIN BYPASS]`)

5. **Test Monitor Limits:**
   - Free trial user: Start monitor (should check credits)
   - Admin user: Start multiple monitors (should bypass checks)

## 🔍 Verification Points

- [ ] Subscription endpoints return correct responses
- [ ] Admin users have infinite credits (999999)
- [ ] Admin users bypass credit deduction
- [ ] Admin transactions are logged with `[ADMIN BYPASS]` tag
- [ ] Free trial users have credit limits enforced
- [ ] Clip creation deducts credits correctly
- [ ] Monitor starting checks credits correctly
- [ ] Social posting is restricted to Pro/admin users

## 🐛 Known Issues

None currently. Report any issues found during testing.

