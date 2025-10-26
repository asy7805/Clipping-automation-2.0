# How to Connect Multiple YouTube Channels

## ✅ What Just Changed

You now have a **"Connect Another Channel"** button on the Social Accounts page when you have at least one YouTube channel connected!

## Current Behavior (Simple)

When you click "Connect Another Channel":
1. OAuth popup opens
2. You authorize with Google
3. System connects your **YouTube default channel**
4. Done!

## How to Connect Different Channels (Current Method)

### Method 1: Switch Default Channel in YouTube
1. Go to YouTube.com
2. Switch to the channel you want to connect (top-right profile icon → Switch account)
3. Come back to your app
4. Click "Connect Another Channel"
5. Authorize
6. That channel will be connected!

### Method 2: Use Different Google Accounts
- Each Google account can have multiple YouTube channels
- Connect each Google account separately

## What You'll See

**Social Accounts Page:**
- YouTube card shows: "2 Channel(s) Connected" (or however many you have)
- "Connect Another Channel" button
- Info message: "You can connect multiple YouTube channels from the same Gmail account"

**Connected Accounts List:**
- Each channel shows separately
- Each has its own "Unlink" button
- Shows channel name (e.g., @YourChannelName)

## Database

Your channels are stored separately in the `social_accounts` table:
```
id  | platform | account_id (channel_id) | account_name    | is_active
----|----------|-------------------------|-----------------|----------
1   | youtube  | UCxxxxx...              | My Main Channel | true
2   | youtube  | UCyyyyy...              | My Alt Channel  | true
```

## Advanced: Channel Selector (Optional Enhancement)

The infrastructure exists to show a channel selector modal after OAuth, which would let you pick from ALL your channels at once. This would require wiring up the `ChannelSelectorModal` component in the `YouTubeCallback.tsx` flow.

**Steps to enable (if desired):**
1. After OAuth in `YouTubeCallback.tsx`, call `/api/v1/social/youtube/channels`
2. If multiple channels returned, show `ChannelSelectorModal`
3. User selects desired channel
4. Call OAuth callback with selected `channel_id`

This is already built but not yet wired up!

## Current Limitations

- Can only connect one TikTok account per user (TikTok limitation)
- Each YouTube channel needs separate OAuth authorization
- Must have manage YouTube channels access on your Google account

## Benefits of Multiple Channels

✅ **Different Content Strategies**: Different channels for different content types
✅ **Separate Analytics**: Track performance per channel
✅ **Quota Management**: Each channel has its own YouTube API quota
✅ **Brand Separation**: Keep personal and business content separate
✅ **Team Collaboration**: Different channels for different team members

---

**Your multi-channel support is now live!** 🎉

Just click "Connect Another Channel" and authorize to add more YouTube channels!

