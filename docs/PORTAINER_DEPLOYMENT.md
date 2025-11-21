# Portainer Deployment Guide

Deploy EC2 Discord Bot v2.0 using Portainer with GitHub integration and environment variables.

## 📋 Prerequisites

- Portainer installed and running
- Access to Portainer web UI
- GitHub repository: https://github.com/iEdgir01/aws_ec2_discord_controller

## 🚀 Step-by-Step Deployment

### Step 1: Create Stack in Portainer

1. **Open Portainer** → Navigate to your Portainer instance
2. **Select Environment** → Choose your Docker environment (local or edge)
3. **Click "Stacks"** in the left sidebar
4. **Click "+ Add stack"** button

### Step 2: Configure Stack Settings

**Stack Name:**
```
ec2-discord-bot
```

**Build method:** Select **"Repository"**

### Step 3: GitHub Integration

**Repository URL:**
```
https://github.com/iEdgir01/aws_ec2_discord_controller
```

**Repository reference:** `refs/heads/master`

**Compose path:** `docker-compose.portainer.yml`

**Authentication:**
- If public repo: Leave unchecked
- If private: Check "Use authentication" and add GitHub token

### Step 4: Configure Environment Variables

Click **"Add an environment variable"** for each of the following:

#### Required Variables

| Name | Value | Notes |
|------|-------|-------|
| `AWSDISCORDTOKEN` | `your_discord_bot_token_here` | Your Discord bot token |
| `AWS_ACCESS_KEY_ID` | `your_aws_access_key_here` | Your AWS access key |
| `AWS_SECRET_ACCESS_KEY` | `your_aws_secret_key_here` | Your AWS secret key |
| `AWS_DEFAULT_REGION` | `af-south-1` | Your AWS region |
| `GUILD_ID` | `your_discord_guild_id_here` | Your Discord server ID |

#### Optional Variables (Pterodactyl)

| Name | Value | Notes |
|------|-------|-------|
| `PTERODACTYL_API_KEY` | `your_pterodactyl_api_key_here` | Panel API key |
| `PTERODACTYL_PANEL_URL` | `https://panel.fixetics.co.za` | Panel URL |
| `PTERODACTYL_API_URL` | `https://panel.fixetics.co.za/api/client` | API endpoint |

**Note:** If you don't use Pterodactyl, you can skip the optional variables.

### Step 5: Deploy Stack

1. **Review your settings:**
   - Stack name: `ec2-discord-bot`
   - Repository: GitHub URL
   - Compose file: `docker-compose.portainer.yml`
   - Environment variables: All set

2. **Enable Auto-update** (Optional but recommended):
   - Check "Enable GitOps updates"
   - Set polling interval: `5m` (checks GitHub every 5 minutes)
   - Check "Re-pull image" to get latest builds

3. **Click "Deploy the stack"**

### Step 6: Monitor Deployment

1. **Go to "Stacks"** → Click `ec2-discord-bot`
2. **Check container status:**
   - Should show `ec2-discord-controller` as **Running** (green)
3. **View logs:**
   - Click the container name
   - Click "Logs" tab
   - Look for: `"message": "EC2 Discord Bot is ready!"`

Expected log output:
```json
{"timestamp": "2025-11-21T...", "level": "INFO", "message": "Bot logged in as YourBot#1234"}
{"timestamp": "2025-11-21T...", "level": "INFO", "message": "Database initialized successfully"}
{"timestamp": "2025-11-21T...", "level": "INFO", "message": "EC2 Discord Bot is ready!"}
```

### Step 7: Test in Discord

```
.ping
.menu
```

You should see the interactive menu with buttons! 🎉

---

## 🔄 Updating the Bot

### Automatic Updates (Recommended)

If you enabled GitOps:
1. Push changes to GitHub
2. Wait 5 minutes (or your polling interval)
3. Portainer automatically pulls and redeploys

### Manual Updates

1. **Go to Stacks** → `ec2-discord-bot`
2. **Click "Pull and redeploy"**
3. Portainer will:
   - Pull latest from GitHub
   - Rebuild container
   - Restart with new code

---

## 📊 Portainer UI Walkthrough

### Creating the Stack

```
Portainer UI
├─ Stacks
│  └─ + Add stack
│     ├─ Name: ec2-discord-bot
│     ├─ Build method: ⚪ Web editor  ⚪ Upload  🔘 Repository
│     ├─ Repository URL: https://github.com/...
│     ├─ Repository reference: refs/heads/master
│     ├─ Compose path: docker-compose.portainer.yml
│     ├─ GitOps updates: ✅ Enabled (5m interval)
│     ├─ Environment variables:
│     │  ├─ AWSDISCORDTOKEN = your_token
│     │  ├─ AWS_ACCESS_KEY_ID = your_key
│     │  ├─ AWS_SECRET_ACCESS_KEY = your_secret
│     │  ├─ AWS_DEFAULT_REGION = af-south-1
│     │  └─ GUILD_ID = 466315445905915915
│     └─ [Deploy the stack]
```

### Adding Environment Variables

For each variable:
```
1. Click "+ Add an environment variable"
2. Name: AWSDISCORDTOKEN
3. Value: your_discord_bot_token_here
4. Repeat for all variables
```

---

## 🔧 Advanced Configuration

### Using Portainer Secrets (More Secure)

Instead of environment variables, use Docker secrets:

1. **Create secrets in Portainer:**
   - Secrets → + Add secret
   - Name: `discord_bot_token`
   - Secret: Your token value

2. **Modify docker-compose.portainer.yml:**
```yaml
version: '3.8'

services:
  ec2-discord-bot:
    # ... other config ...
    secrets:
      - discord_bot_token
      - aws_access_key
      - aws_secret_key

    environment:
      # Reference secrets as files
      - AWSDISCORDTOKEN_FILE=/run/secrets/discord_bot_token
      # ... other vars ...

secrets:
  discord_bot_token:
    external: true
  aws_access_key:
    external: true
  aws_secret_key:
    external: true
```

**Note:** This requires code changes to read from files instead of env vars.

### Using Portainer Templates

Create a template for easy redeployment:

1. **Stacks** → `ec2-discord-bot` → **"Export as template"**
2. Give it a name: `EC2 Discord Bot v2.0`
3. Next time: **App Templates** → Deploy from template

---

## 🐛 Troubleshooting

### Stack fails to deploy

**Error:** `repository not found` or `authentication failed`

**Fix:**
- Verify GitHub URL is correct
- If private repo, add GitHub Personal Access Token:
  1. GitHub → Settings → Developer settings → Personal access tokens
  2. Generate token with `repo` scope
  3. In Portainer: Check "Use authentication" → Add token

---

**Error:** `file not found: docker-compose.portainer.yml`

**Fix:**
- Verify compose path is exactly: `docker-compose.portainer.yml`
- Ensure file exists in repository root
- Check branch is `master` or `main`

---

**Error:** `Missing environment variable: AWSDISCORDTOKEN`

**Fix:**
- Ensure all required environment variables are set
- Check for typos in variable names
- Don't include quotes around values in Portainer

---

### Container keeps restarting

**Check logs:**
```
Portainer → Containers → ec2-discord-controller → Logs
```

**Common issues:**
1. **Invalid Discord token** → `discord.errors.LoginFailure`
   - Verify token in Portainer environment variables
   - Generate new token if needed

2. **Missing Message Content Intent** → `PrivilegedIntentsRequired`
   - Go to Discord Developer Portal
   - Enable "Message Content Intent"

3. **Invalid AWS credentials** → `botocore.exceptions.NoCredentialsError`
   - Verify AWS keys in Portainer
   - Test with: `aws sts get-caller-identity`

4. **No instances found** → `ValueError`
   - Verify EC2 instance has `guild` tag
   - Check guild ID matches in Portainer env vars

---

### GitOps not updating

**Issue:** Pushed to GitHub but Portainer not updating

**Fix:**
1. **Check polling:**
   - Stacks → ec2-discord-bot → Edit
   - Verify "GitOps updates" is enabled
   - Check polling interval

2. **Manual trigger:**
   - Stacks → ec2-discord-bot
   - Click "Pull and redeploy"

3. **Check webhook** (Advanced):
   - Enable webhook in Portainer
   - Add webhook to GitHub Actions

---

### Database persistence issues

**Issue:** Uptime data lost after redeploy

**Fix:**
- Verify volume is created: `Volumes` → `ec2-discord-bot_bot-data`
- Volume should persist across deployments
- To backup:
  ```bash
  docker cp ec2-discord-controller:/data/ec2bot.db ./backup.db
  ```

---

## 📱 Portainer Mobile App

You can manage the bot from Portainer mobile app:

1. **Install:** Portainer app (iOS/Android)
2. **Connect:** Add your Portainer server
3. **Manage:**
   - View container status
   - Check logs
   - Restart container
   - Update environment variables

---

## 🔐 Security Best Practices

### 1. Use Secrets Instead of Environment Variables

For production, use Docker secrets:
- More secure (encrypted at rest)
- Not visible in `docker inspect`
- Centralized management

### 2. Restrict Portainer Access

- Enable authentication
- Use role-based access control (RBAC)
- Limit who can view environment variables

### 3. Use Private GitHub Repository

- Keep your deployment config private
- Use deploy keys instead of personal tokens
- Enable branch protection

### 4. Rotate Credentials Regularly

- Discord token: Regenerate monthly
- AWS credentials: Rotate every 90 days
- Update in Portainer environment variables

---

## 📊 Monitoring in Portainer

### View Container Metrics

1. **Containers** → `ec2-discord-controller`
2. **Stats** tab shows:
   - CPU usage
   - Memory usage
   - Network I/O
   - Block I/O

### Set up Alerts (Portainer Business)

If you have Portainer Business Edition:
- Set CPU/memory thresholds
- Email notifications on container failures
- Webhook to Discord on issues

---

## 🚀 Production Checklist

Before going to production:

- [ ] All environment variables set in Portainer
- [ ] GitOps updates enabled
- [ ] Discord "Message Content Intent" enabled
- [ ] AWS credentials have least-privilege IAM policy
- [ ] EC2 instance has `guild` tag
- [ ] Volume `bot-data` is created and persistent
- [ ] Logs show "Bot is ready!"
- [ ] Tested `.menu` command in Discord
- [ ] Verified instance controls work (Start/Stop/Reboot)
- [ ] Set up monitoring/alerts
- [ ] Documented deployment for team

---

## 🎯 Quick Reference

### Portainer Stack Settings

```yaml
Name: ec2-discord-bot
Repository: https://github.com/iEdgir01/aws_ec2_discord_controller
Branch: master
Compose: docker-compose.portainer.yml
GitOps: ✅ Enabled (5m)
```

### Required Environment Variables

```bash
AWSDISCORDTOKEN=<your_discord_token>
AWS_ACCESS_KEY_ID=<your_aws_key>
AWS_SECRET_ACCESS_KEY=<your_aws_secret>
AWS_DEFAULT_REGION=af-south-1
GUILD_ID=<your_discord_guild_id>
```

### Useful Commands

```bash
# View logs
Containers → ec2-discord-controller → Logs

# Restart container
Containers → ec2-discord-controller → ⟳ Restart

# Update stack
Stacks → ec2-discord-bot → Pull and redeploy

# Backup database
docker cp ec2-discord-controller:/data/ec2bot.db ./backup.db
```

---

## 🆘 Getting Help

1. **Check logs first:**
   - Portainer → Containers → ec2-discord-controller → Logs

2. **Verify environment:**
   - Stacks → ec2-discord-bot → Editor tab
   - Check all environment variables

3. **Test components:**
   - Discord: Try `.ping` command
   - AWS: Check IAM permissions
   - Network: Ensure Portainer can reach GitHub

4. **GitHub Issues:**
   - https://github.com/iEdgir01/aws_ec2_discord_controller/issues

---

## 🎉 Success!

Once deployed, you should see:

```
✅ Stack: ec2-discord-bot (Running)
✅ Container: ec2-discord-controller (Running)
✅ Volume: ec2-discord-bot_bot-data (Mounted)
✅ Discord: Bot online and responding
✅ GitOps: Auto-updating from GitHub
```

Type `.menu` in Discord and enjoy your new interactive EC2 controller! 🚀
