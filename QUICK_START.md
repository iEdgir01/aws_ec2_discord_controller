# Quick Start Guide - EC2 Discord Bot v2.0

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Python 3.10+
- Discord bot token
- AWS credentials
- EC2 instance with `guild` tag

### Step 1: Install Dependencies

```bash
cd d:\Nextcloud\Dev\pythoncode\aws_ec2_discord_controller
pip install -r requirements.txt
```

### Step 2: Verify Configuration

Your [.env](.env) file should have:
```bash
AWSDISCORDTOKEN=your_discord_bot_token_here
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_DEFAULT_REGION=af-south-1
guild_id='your_discord_guild_id_here'
DB_PATH='/data/ec2bot.db'
```

✅ **Make sure your .env file has real values (see .env.example for format)**

### Step 3: Enable Discord Intents

⚠️ **IMPORTANT:** Discord.py 2.x requires Message Content Intent

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your bot application
3. Click "Bot" in the left sidebar
4. Scroll to "Privileged Gateway Intents"
5. ✅ Enable "Message Content Intent"
6. Click "Save Changes"

### Step 4: Run the Bot

```bash
# Run new enhanced bot
python bot_new.py
```

Or use Docker:
```bash
# Update docker-compose.yml to use bot_new.py
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Step 5: Test in Discord

```
.menu
```

You should see an interactive menu with buttons! 🎉

## 🎮 Using the Interactive UI

### Main Menu
Type `.menu` to open the control panel:

```
┌─────────────────────────────────┐
│  EC2 Controller Main Menu       │
├─────────────────────────────────┤
│ 🖥️  Control Instances            │
│ 📊 View Reports                 │
│ 💰 View Costs                   │
│ 📈 Cache Stats                  │
└─────────────────────────────────┘
```

### Control Instances
Click "Control Instances" to see:
```
┌─────────────────────────────────┐
│ 🟢 EC2 Instance: i-xxxxx        │
├─────────────────────────────────┤
│ State: RUNNING                  │
│ Type: t3.small                  │
│ Zone: af-south-1a               │
│ Public IP: 54.123.45.67         │
│ Uptime: 2h 34m                  │
├─────────────────────────────────┤
│ [▶️ Start] [⏹️ Stop] [🔄 Reboot] │
│ [🔄 Refresh]                    │
│ [Previous] [Next] [Main Menu]   │
└─────────────────────────────────┘
```

### View Reports
Click "View Reports" to see:
- **Today's Report** - Daily uptime
- **Weekly Report** - 7-day summary
- **Monthly Report** - Full month with costs

### View Costs
See estimated costs from AWS Cost Explorer or local estimates.

## 📝 Quick Commands

Even with the interactive UI, commands still work:

```bash
.menu          # Open interactive menu
.ping          # Check bot latency
.state         # Quick state check
.start         # Start first instance
.stop          # Stop first instance
.help          # Show help
```

## 🔄 Migrating from Old Bot

Your old `bot.py` still works! New features are in `bot_new.py`.

**Side-by-side testing:**
```bash
# Terminal 1 - Old bot
python bot.py

# Terminal 2 - New bot
python bot_new.py
```

Both can run simultaneously for testing.

**When ready to switch:**
```bash
# Stop old bot (Ctrl+C)
# Run new bot
python bot_new.py
```

## ✅ Verify Everything Works

### 1. Bot Online?
```
.ping
```
Expected: `🏓 Pong! Latency: XXms`

### 2. Instances Found?
```
.state
```
Expected: List of instances with states

### 3. Interactive UI?
```
.menu
```
Expected: Menu with clickable buttons

### 4. Instance Control?
1. Click "Control Instances"
2. See your instance info
3. Try "Refresh" button
4. Navigate with Previous/Next if multiple instances

### 5. Reports Working?
1. Click "View Reports"
2. Click "Today's Report"
3. See uptime data

## 🐛 Troubleshooting

### Bot won't start

**Error:** `ImportError: No module named 'ec2bot'`

**Fix:**
```bash
pip install -r requirements.txt
```

---

**Error:** `discord.errors.PrivilegedIntentsRequired`

**Fix:** Enable "Message Content Intent" in Discord Developer Portal (Step 3 above)

---

**Error:** `No module named 'discord'`

**Fix:**
```bash
pip install --upgrade discord.py
```

### No instances found

**Check guild tag:**
```bash
aws ec2 describe-instances \
  --region af-south-1 \
  --filters "Name=tag:guild,Values=466315445905915915"
```

Should return your instance(s).

**Fix:** Add guild tag to instance:
```bash
aws ec2 create-tags \
  --resources i-YOUR-INSTANCE-ID \
  --tags Key=guild,Value=466315445905915915 \
  --region af-south-1
```

### Menu buttons not working

**Issue:** Buttons don't respond

**Fix:** Check Discord Developer Portal → Bot → Message Content Intent is enabled

### Old commands not working

**Fix:** Old commands still work! Try:
- `.state` instead of `.info`
- `.menu` for new interactive interface

## 📊 What's Different?

| Old Way | New Way |
|---------|---------|
| `.info` | `.menu` → "Control Instances" |
| `.totaluptime` | `.menu` → "View Reports" → "Monthly Report" |
| Type commands | Click buttons |
| Wait for responses | Instant updates in same message |
| No cost tracking | `.menu` → "View Costs" |

## 🎯 Key Features

✅ **Interactive buttons** - No more typing!
✅ **Real-time updates** - UI updates in place
✅ **Cost tracking** - See your AWS spending
✅ **Caching** - 70% fewer API calls
✅ **Reports** - Daily/Monthly summaries
✅ **Audit log** - Track who did what
✅ **Better errors** - Clear error messages

## 📚 Learn More

- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - Detailed migration steps
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Technical details
- [README.md](README.md) - Full documentation

## 🆘 Need Help?

1. **Check logs:**
   ```bash
   tail -f /data/ec2bot.log
   ```

2. **Enable debug mode:**
   Edit `bot_new.py` line 32:
   ```python
   logger = setup_logging(log_file=DB_PATH.replace('.db', '.log'), level="DEBUG")
   ```

3. **GitHub Issues:**
   https://github.com/iEdgir01/aws_ec2_discord_controller/issues

---

**Ready to go?** Run `python bot_new.py` and type `.menu` in Discord! 🚀
