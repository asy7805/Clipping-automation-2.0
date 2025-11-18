# 🔐 Supabase Setup Guide for Tone Sorter

This guide shows you exactly what Supabase credentials you need and how to get them.

## 📋 Required Environment Variables

Add these to your `.env` file:

```bash
# Required for all Supabase operations
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here

# Required for storage operations (downloads/uploads)
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# Optional: Storage bucket name (defaults to "raw")
STORAGE_BUCKET=raw
```

## 🎯 What You Need

### 1. **SUPABASE_URL** ✅
Your Supabase project URL

**Where to find it:**
1. Go to https://app.supabase.com
2. Select your project
3. Go to **Settings** → **API**
4. Copy the **Project URL**
   - Example: `https://abcdefgh12345678.supabase.co`

### 2. **SUPABASE_ANON_KEY** ✅
Public anonymous key (safe to use in client apps)

**Where to find it:**
1. Same location: **Settings** → **API**
2. Copy the **anon public** key
3. This is safe to expose in client apps

### 3. **SUPABASE_SERVICE_ROLE_KEY** 🔑 **IMPORTANT!**
Admin key with full access (keep this secret!)

**Where to find it:**
1. Same location: **Settings** → **API**
2. Scroll down to **service_role** key
3. Click **Reveal** and copy it
4. ⚠️ **NEVER commit this to Git or share publicly!**

**Why you need it:**
- Required for reading/downloading from Storage buckets
- Bypasses Row Level Security (RLS)
- Full admin access to your database

### 4. **STORAGE_BUCKET** (Optional)
Name of your storage bucket

**Default:** `raw`
**Where to find it:**
1. Go to **Storage** in Supabase dashboard
2. See list of buckets
3. Use the name of the bucket containing your clips

## 🔧 Setup Steps

### Step 1: Check if you have .env file

```bash
# Windows PowerShell
Test-Path .env

# Linux/Mac
ls -la .env
```

If it doesn't exist, create it:
```bash
# Windows
New-Item .env -ItemType File

# Linux/Mac
touch .env
```

### Step 2: Add Supabase credentials

Edit `.env` and add (replace with your actual values):

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Storage Configuration
STORAGE_BUCKET=raw
```

### Step 3: Verify your setup

```bash
# Test Supabase connection and storage access
python scripts/check_storage.py
```

This will tell you if:
- ✅ Can connect to Supabase
- ✅ Bucket exists
- ✅ Can read/write to storage
- ❌ Any issues with permissions

### Step 4: Test the tone sorter

```bash
# Test with a few clips first
python scripts/sort_clips_from_supabase.py --max-clips 5
```

## 🔍 Troubleshooting

### ❌ "Missing required env vars"

**Problem:** Environment variables not set
```bash
# Check what's in your .env
cat .env | grep SUPABASE
```

**Solution:** Make sure all three variables are set (URL, ANON_KEY, SERVICE_ROLE_KEY)

### ❌ "Permission denied" or "Access denied"

**Problem:** Using wrong key or missing service role key
```bash
# Make sure you have the SERVICE_ROLE_KEY, not just the ANON_KEY
cat .env | grep SERVICE_ROLE_KEY
```

**Solution:** Add the service role key from Supabase dashboard

### ❌ "Bucket not found"

**Problem:** Wrong bucket name
```bash
# Check available buckets
python scripts/check_storage.py
```

**Solution:** Update STORAGE_BUCKET in .env with correct name

### ❌ "Could not connect to Supabase"

**Problem:** Wrong URL or network issue

**Solution:**
1. Verify SUPABASE_URL is correct (should end in .supabase.co)
2. Check your internet connection
3. Verify project is not paused in Supabase dashboard

## 📝 Complete .env Template

Here's a complete template for your `.env` file:

```bash
# ============================================
# Supabase Configuration
# ============================================

# Project URL (from Supabase Dashboard → Settings → API)
SUPABASE_URL=https://your-project-id.supabase.co

# Anon Key (public, safe for client apps)
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.your-anon-key-here

# Service Role Key (SECRET! Never commit to Git)
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.your-service-role-key-here

# Optional: Alternative key names (some scripts may use these)
SUPABASE_KEY=your-anon-key-here
SUPABASE_ANON_KEY=your-anon-key-here

# ============================================
# Storage Configuration
# ============================================

# Storage bucket name (where clips are stored)
STORAGE_BUCKET=raw

# Storage prefix (optional, for organizing clips)
# STORAGE_PREFIX=channel_name/

# ============================================
# Other Settings
# ============================================

# Use service role for privileged operations
USE_SERVICE_ROLE=true

# Model data directory (for ML training)
MODEL_DATA_DIR=data/
```

## 🔒 Security Best Practices

### ✅ DO:
- Keep `.env` file in `.gitignore`
- Use service role key only in server/local scripts
- Rotate keys if accidentally exposed
- Use different projects for dev/prod

### ❌ DON'T:
- Commit `.env` to Git
- Share service role key publicly
- Use service role key in client apps
- Hard-code credentials in scripts

## 🎯 Quick Reference

| Variable | Required? | Where Used | Get From |
|----------|-----------|------------|----------|
| `SUPABASE_URL` | ✅ Yes | All scripts | Settings → API → Project URL |
| `SUPABASE_ANON_KEY` | ✅ Yes | Client operations | Settings → API → anon public |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ For Storage | Storage access | Settings → API → service_role |
| `STORAGE_BUCKET` | Optional | Storage operations | Storage → bucket list |

## 🚀 Quick Start Checklist

- [ ] Get Supabase project URL
- [ ] Get anon key from Supabase dashboard
- [ ] Get service role key from Supabase dashboard
- [ ] Create/edit `.env` file
- [ ] Add all three credentials
- [ ] Run `python scripts/check_storage.py` to verify
- [ ] Test with `python scripts/sort_clips_from_supabase.py --max-clips 5`
- [ ] Review results and run on full dataset

## 📚 Related Documentation

- **Supabase Dashboard**: https://app.supabase.com
- **Supabase Storage Docs**: https://supabase.com/docs/guides/storage
- **API Keys Guide**: https://supabase.com/docs/guides/api/api-keys

## 🆘 Still Having Issues?

Run the diagnostic script:

```bash
python scripts/check_storage.py
```

This will check:
- ✅ Supabase connection
- ✅ Bucket existence
- ✅ Upload/download permissions
- ✅ File listing access

If all checks pass, you're ready to sort clips! 🎉

```bash
python scripts/sort_clips_from_supabase.py
```

---

**Need help?** Check the error messages from `check_storage.py` - they'll tell you exactly what's missing or misconfigured.




