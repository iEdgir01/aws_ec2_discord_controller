# AWS EC2 Discord Controller

A Discord bot that controls AWS EC2 instances and manages game servers via a Pterodactyl panel. Users can start/stop EC2 instances, check status, and monitor server uptime through Discord commands.

## Features

- Start/stop AWS EC2 instances via Discord commands
- Monitor instance status and uptime
- Track daily and total uptime statistics
- Integration with Pterodactyl panel for game server management
- Persistent SQLite database for uptime tracking
- Docker support with data persistence

## Quick Start Checklist

**Starting from zero? Follow these steps in order:**

1. ☐ **AWS Account Setup** (see detailed instructions below)
   - Create AWS account
   - Create IAM user with limited permissions
   - Save Access Key ID and Secret Access Key

2. ☐ **EC2 Instance Setup**
   - Launch EC2 instance in your preferred region
   - Tag instance with key=`guild`, value=`YOUR_DISCORD_GUILD_ID`
   - Note the Instance ID
   - Update IAM policy with Instance ID

3. ☐ **Discord Bot Setup**
   - Create Discord application & bot user
   - Save bot token
   - Enable required intents
   - Invite bot to your Discord server
   - Get your Discord Guild ID (Server ID)

4. ☐ **Deploy Bot**
   - Clone this repository
   - Copy `.env.example` to `.env`
   - Fill in all credentials in `.env`
   - Run `docker-compose up -d`

5. ☐ **Test**
   - Type `.ping` in Discord
   - Type `.state` to check instance state
   - Type `.start` to start your instance

**Estimated Setup Time:** 30-45 minutes for first-time setup

## Prerequisites

- Docker and Docker Compose (for containerized deployment)
- OR Python 3.10+ (for local deployment)
- AWS Account (instructions below for complete setup)
- Discord Bot Token (instructions below)
- Pterodactyl Panel (optional, for game server management)

## AWS Setup from Scratch

This section guides you through setting up AWS from nothing to having a controllable EC2 instance.

### Step 1: Create an AWS Account

1. Go to [https://aws.amazon.com](https://aws.amazon.com)
2. Click "Create an AWS Account"
3. Follow the registration process (requires credit card, but Free Tier available)
4. Sign in to the AWS Management Console

### Step 2: Create an IAM User for the Bot

For security, create a dedicated IAM user with restricted permissions instead of using root credentials.

1. **Navigate to IAM Console**
   - Go to [IAM Console](https://console.aws.amazon.com/iam/)
   - Click "Users" in the left sidebar
   - Click "Add users"

2. **Configure User**
   - User name: `ec2-discord-bot` (or your preferred name)
   - Select "Access key - Programmatic access"
   - Click "Next: Permissions"

3. **Create Custom Policy**
   - Click "Attach policies directly"
   - Click "Create policy"
   - Click the "JSON" tab
   - Paste the following policy (replace `YOUR_REGION` and `YOUR_INSTANCE_ID` after creating the instance):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "EC2InstanceControl",
            "Effect": "Allow",
            "Action": [
                "ec2:StartInstances",
                "ec2:StopInstances",
                "ec2:RebootInstances"
            ],
            "Resource": "arn:aws:ec2:YOUR_REGION:*:instance/YOUR_INSTANCE_ID"
        },
        {
            "Sid": "EC2DescribeAll",
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeInstanceStatus",
                "ec2:DescribeTags"
            ],
            "Resource": "*"
        }
    ]
}
```

4. **Name and Create Policy**
   - Click "Next: Tags" (skip tags)
   - Click "Next: Review"
   - Name: `EC2DiscordBotPolicy`
   - Description: "Allows Discord bot to control specific EC2 instance"
   - Click "Create policy"

5. **Attach Policy to User**
   - Go back to the user creation tab
   - Refresh the policy list
   - Search for `EC2DiscordBotPolicy`
   - Check the box next to it
   - Click "Next: Tags" (optional)
   - Click "Next: Review"
   - Click "Create user"

6. **Save Credentials**
   - **IMPORTANT**: Copy the Access Key ID and Secret Access Key
   - Download the CSV or save them securely
   - You won't be able to see the secret key again!

### Step 3: Create an EC2 Instance

1. **Navigate to EC2 Console**
   - Go to [EC2 Console](https://console.aws.amazon.com/ec2/)
   - Select your preferred region (top-right dropdown)
   - Click "Launch Instance"

2. **Configure Instance**

   **Name and Tags:**
   - Name: `minecraft-server` (or your preferred name)
   - Click "Add additional tags"
   - Add tag: Key = `guild`, Value = `YOUR_DISCORD_GUILD_ID`
     - ⚠️ **CRITICAL**: This tag must match your Discord Guild ID exactly
     - To find your Guild ID: Enable Developer Mode in Discord (User Settings > Advanced), right-click your server, "Copy ID"

   **Application and OS Images (AMI):**
   - Choose "Amazon Linux 2023" or "Ubuntu Server 22.04 LTS"
   - Both are Free Tier eligible

   **Instance Type:**
   - Select `t2.micro` (Free Tier) or `t3a.small` (better performance, ~$15/month)
   - For game servers: Minimum `t3.small` recommended

   **Key Pair (login):**
   - Click "Create new key pair"
   - Name: `ec2-discord-bot-key`
   - Type: RSA
   - Format: `.pem` (Linux/Mac) or `.ppk` (Windows/PuTTY)
   - Click "Create key pair" and save the file securely

   **Network Settings:**
   - Click "Edit"
   - Auto-assign public IP: Enable
   - Firewall (security group): Create new
   - Security group name: `ec2-discord-bot-sg`
   - Description: "Security group for Discord bot controlled instance"

   **Security Group Rules:**
   - SSH (22): Your IP (for administration)
   - Custom TCP (25565): 0.0.0.0/0 (for Minecraft, if applicable)
   - Add rules for your specific game server ports
   - Click "Add security group rule" for each port needed

   **Storage:**
   - 8 GB gp3 (Free Tier) or increase for game servers (20-30 GB recommended)

3. **Review and Launch**
   - Review all settings
   - Click "Launch Instance"
   - Wait for instance to start (2-3 minutes)
   - Note the Instance ID (e.g., `i-1234567890abcdef0`)

### Step 4: Update IAM Policy with Instance ID

Now that you have an Instance ID, update the IAM policy:

1. Go back to [IAM Console](https://console.aws.amazon.com/iam/)
2. Click "Policies" in the left sidebar
3. Search for `EC2DiscordBotPolicy`
4. Click the policy name
5. Click "Edit policy"
6. Click "JSON" tab
7. Replace `YOUR_REGION` with your region (e.g., `us-east-1`)
8. Replace `YOUR_INSTANCE_ID` with your actual instance ID
9. Click "Next: Review"
10. Click "Save changes"

### Step 5: Verify Instance Tag

Critical: Ensure your instance has the correct tag!

```bash
# Using AWS CLI (if installed)
aws ec2 describe-instances --instance-ids YOUR_INSTANCE_ID --query 'Reservations[0].Instances[0].Tags'

# Expected output should include:
# {
#     "Key": "guild",
#     "Value": "YOUR_DISCORD_GUILD_ID"
# }
```

Or via Console:
1. Go to EC2 Console
2. Click "Instances"
3. Select your instance
4. Check the "Tags" tab
5. Verify `guild` tag exists with correct Guild ID

### Step 6: Test AWS Credentials

Before proceeding, verify your IAM credentials work:

```bash
# Set credentials temporarily
export AWS_ACCESS_KEY_ID=your_access_key_here
export AWS_SECRET_ACCESS_KEY=your_secret_key_here
export AWS_DEFAULT_REGION=your_region_here

# Test credentials
aws sts get-caller-identity

# Test instance access
aws ec2 describe-instances --instance-ids YOUR_INSTANCE_ID

# Test start/stop (optional)
aws ec2 stop-instances --instance-ids YOUR_INSTANCE_ID
aws ec2 start-instances --instance-ids YOUR_INSTANCE_ID
```

### Step 7: Get Your Discord Guild ID

1. Open Discord
2. Go to User Settings (⚙️ icon)
3. Go to "Advanced"
4. Enable "Developer Mode"
5. Close settings
6. Right-click your Discord server icon
7. Click "Copy ID"
8. This is your Guild ID - save it for configuration

### AWS Setup Complete! ✅

You now have:
- ✅ IAM user with programmatic access
- ✅ Restricted IAM policy for security
- ✅ EC2 instance tagged with your Guild ID
- ✅ Security group configured
- ✅ Access credentials ready

**Next Steps:** Set up your Discord bot below.

## Discord Bot Setup

### Step 1: Create Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Name your application (e.g., "EC2 Controller Bot")
4. Click "Create"

### Step 2: Create Bot User

1. In your application, click "Bot" in the left sidebar
2. Click "Add Bot"
3. Confirm by clicking "Yes, do it!"
4. Under "Token", click "Copy" to copy your bot token
   - ⚠️ **IMPORTANT**: Save this token securely - you'll need it for configuration
   - Never share this token publicly!

### Step 3: Configure Bot Permissions

1. Scroll down to "Privileged Gateway Intents"
2. Enable the following (optional, but recommended):
   - "Server Members Intent" (for member verification)
   - "Message Content Intent" (to read commands)

### Step 4: Invite Bot to Your Server

1. Click "OAuth2" > "URL Generator" in the left sidebar
2. In "Scopes", check:
   - `bot`
   - `applications.commands`
3. In "Bot Permissions", check:
   - `Read Messages/View Channels`
   - `Send Messages`
   - `Embed Links`
   - `Read Message History`
4. Copy the generated URL at the bottom
5. Open the URL in a browser
6. Select your Discord server
7. Click "Authorize"
8. Complete the CAPTCHA

### Discord Bot Setup Complete! ✅

Your bot is now in your Discord server and ready to be configured.

## Quick Start with Docker (Recommended)

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd aws_ec2_discord_controller
```

### 2. Configure environment variables

Copy the example environment file and edit it with your credentials:

```bash
cp .env.example .env
nano .env  # or use your preferred editor
```

Edit `.env` and fill in ALL the following values with credentials from the setup steps above:

```bash
# ===== REQUIRED: Discord Bot Configuration =====
# Get this from Discord Developer Portal (Step 2 of Discord Bot Setup)
AWSDISCORDTOKEN=your_discord_bot_token_here

# ===== REQUIRED: AWS Configuration =====
# Get these from IAM User creation (Step 2 of AWS Setup)
AWS_ACCESS_KEY_ID=your_aws_access_key_id_from_iam
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key_from_iam
AWS_DEFAULT_REGION=us-east-1  # Use the region where you created your EC2 instance

# ===== REQUIRED: Discord Guild Configuration =====
# Get this from Discord (Step 7 of AWS Setup)
guild_id=your_discord_guild_id_here

# ===== OPTIONAL: Pterodactyl Panel Configuration =====
# Only needed if you're managing game servers via Pterodactyl
# Leave as defaults if not using Pterodactyl
api=your_pterodactyl_api_key_here
accept_type=application/json
content_type=application/json
panel_url=https://your-panel-domain.com
get_server_url=https://your-panel-domain.com/api/client

# ===== Database Configuration (leave as default for Docker) =====
DB_PATH=/data/ec2bot.db
```

**Example filled out `.env` (with dummy values):**
```bash
AWSDISCORDTOKEN=YOUR_BOT_TOKEN_GOES_HERE_FROM_DISCORD_DEVELOPER_PORTAL
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_DEFAULT_REGION=us-east-1
guild_id=123456789012345678
api=ptla_exampleapikeyhere123456789
accept_type=application/json
content_type=application/json
panel_url=https://panel.example.com
get_server_url=https://panel.example.com/api/client
DB_PATH=/data/ec2bot.db
```

### 3. Verify EC2 Instance Tag

⚠️ **CRITICAL**: Your EC2 instance MUST be tagged correctly or the bot won't find it!

If you followed "Step 3: Create an EC2 Instance" above, this should already be done. Verify:

```bash
# Check your instance has the guild tag
aws ec2 describe-instances \
  --region YOUR_REGION \
  --filters "Name=tag:guild,Values=YOUR_GUILD_ID" \
  --query 'Reservations[*].Instances[*].[InstanceId,State.Name,Tags]'
```

Expected output should show your instance ID with "running" or "stopped" state.

### 4. Build and run with Docker Compose

```bash
docker-compose up -d
```

### 6. View logs

```bash
docker-compose logs -f ec2-discord-bot
```

## Discord Bot Commands

| Command | Description |
|---------|-------------|
| `.info` | Display EC2 instance status, IP, uptime, and server status |
| `.ping` | Check bot latency |
| `.start` | Start the EC2 instance |
| `.stop` | Stop the EC2 instance and log uptime |
| `.state` | Check current EC2 instance state |
| `.totaluptime` | Display total uptime for the current day |
| `.lrs` | List running servers on the panel |

## How It Works: Discord to EC2 Flow

Understanding the complete interaction flow:

### Architecture Overview

```
Discord User → Discord Bot (Docker Container) → AWS EC2 API → EC2 Instance
                          ↓
                    SQLite Database (uptime tracking)
                          ↓
                    Pterodactyl Panel (optional game server management)
```

### Command Flow Example: Starting an Instance

1. **User sends command in Discord**
   ```
   User types: .start
   ```

2. **Bot receives message**
   - Bot is listening to messages in the Discord guild (server)
   - Validates the message is from the configured guild ID
   - Parses the command (`.start`)

3. **Bot queries EC2 for tagged instances**
   ```python
   instances = ec2.instances.filter(
       Filters=[{'Name':'tag:guild', 'Values': [guild_id]}]
   )
   ```
   - Uses boto3 SDK to connect to AWS EC2 API
   - Authenticates using IAM credentials from `.env`
   - Filters instances by the `guild` tag matching your Guild ID
   - Returns list of matching instances (bot uses first one)

4. **Bot checks current instance state**
   ```python
   current_state = instance.state['Name']  # 'stopped', 'running', etc.
   ```

5. **Bot sends start command to AWS**
   ```python
   instance.start()
   ```
   - Calls AWS EC2 API: `StartInstances`
   - AWS begins instance startup sequence
   - Takes 30-60 seconds for instance to fully start

6. **Bot monitors and responds**
   - Sends "Starting EC2 instance..." message to Discord
   - Enters hourly countdown loop
   - Checks instance state every hour
   - Sends status updates to Discord

7. **User retrieves instance information**
   ```
   User types: .info
   Bot responds with: Instance IP, state, uptime, etc.
   ```

### Security & Authentication

**IAM Policy Enforcement:**
- The bot's IAM user can ONLY control instances you specified
- Policy restricts actions to `StartInstances`, `StopInstances`, `RebootInstances`
- Even if someone gains access to the bot, they can't:
  - Delete instances
  - Create new instances
  - Access other AWS resources
  - Control instances without the guild tag

**Guild ID Filtering:**
- Bot only responds to commands from YOUR Discord server
- `guild_id` environment variable restricts access
- Even if bot is in multiple servers, it only works in one

**Tag-Based Instance Selection:**
- Bot finds instances using `guild` tag
- Tag value must exactly match your Discord Guild ID
- No tag = bot won't see the instance
- Wrong tag value = bot won't control it

### Data Persistence

**Uptime Tracking:**
- When you `.stop` the instance, bot calculates session duration
- Stores uptime in SQLite database: `/data/ec2bot.db`
- Database persists in Docker volume
- `.totaluptime` command queries database for daily totals

**Docker Volume:**
```yaml
volumes:
  - bot-data:/data  # Named volume for persistence
```
- Database survives container restarts
- Data remains even if container is recreated
- Backup-friendly (just copy the volume)

### Optional: Pterodactyl Integration

If you're running game servers (Minecraft, etc.) via Pterodactyl panel:

1. Bot can query server status via Pterodactyl API
2. Shows running servers in `.info` command
3. Lists active servers with `.lrs` command
4. Requires `api`, `panel_url`, and `get_server_url` configuration

**Not using Pterodactyl?** The bot works fine without it - just leave default values in `.env`.

## Local Development (without Docker)

### 1. Create virtual environment

```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Follow steps 2-4 from the Docker setup above.

For local development, change `DB_PATH` in `.env`:
```bash
DB_PATH=./ec2bot.db
```

### 4. Run the bot

```bash
python bot.py
```

## Project Structure

```
aws_ec2_discord_controller/
├── api.py              # Pterodactyl panel API integration
├── bot.py              # Discord bot main file
├── functions.py        # Utility functions for EC2 and panel
├── requirements.txt    # Python dependencies
├── Dockerfile         # Docker container definition
├── docker-compose.yml # Docker Compose configuration
├── .env.example       # Example environment variables
├── .gitignore        # Git ignore rules
└── README.md         # This file
```

## Docker Management

### Start the bot
```bash
docker-compose up -d
```

### Stop the bot
```bash
docker-compose down
```

### View logs
```bash
docker-compose logs -f
```

### Rebuild after code changes
```bash
docker-compose up -d --build
```

### Access the database
```bash
docker-compose exec ec2-discord-bot sqlite3 /data/ec2bot.db
```

## Data Persistence

The bot uses a named Docker volume (`bot-data`) to persist the SQLite database across container restarts. The database is stored at `/data/ec2bot.db` inside the container.

To backup the database:
```bash
docker-compose exec ec2-discord-bot cat /data/ec2bot.db > backup.db
```

To restore the database:
```bash
cat backup.db | docker-compose exec -T ec2-discord-bot tee /data/ec2bot.db > /dev/null
```

## Security Notes

⚠️ **IMPORTANT**: Never commit the `.env` file to version control. It contains sensitive credentials.

- The `.env` file is already excluded in `.gitignore`
- Rotate all credentials if they are accidentally exposed
- Use IAM roles when running on EC2 instead of hardcoded AWS credentials
- Consider using AWS Secrets Manager or similar for production deployments
- The Docker container runs as a non-root user for security

## Troubleshooting

### Bot doesn't start
- Check logs: `docker-compose logs -f`
- Verify all environment variables in `.env` are set correctly
- Ensure EC2 instances are tagged with the correct guild ID

### Database errors
- Ensure the `/data` volume is properly mounted
- Check file permissions on the database file

### AWS credential errors
- Verify AWS credentials are correctly configured
- Test with: `docker-compose exec ec2-discord-bot aws sts get-caller-identity`
- Ensure IAM permissions include EC2 read/write access

### Discord bot not responding
- Verify the bot token is correct
- Check bot has proper permissions in your Discord server
- Ensure bot is online in Discord

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

See [LICENSE](LICENSE) file for details.

## TODO

- [ ] Implement server start/stop functions for Pterodactyl integration
- [ ] Add Discord UI components (buttons) for commands
- [ ] Add command permissions/role checks
- [ ] Migrate to discord.py v2.x
- [ ] Add unit tests
- [ ] Implement proper logging system
- [ ] Add support for multiple EC2 instances
