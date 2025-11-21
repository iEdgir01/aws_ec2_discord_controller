# Pterodactyl Panel Connection Troubleshooting Guide

This guide helps you troubleshoot connection issues between the Discord bot container and the Pterodactyl panel.

## Quick Diagnosis

Run these commands to quickly identify the issue:

### 1. Check if the container is running
```bash
docker ps | grep ec2-discord
```

### 2. View container logs
```bash
docker logs ec2-discord-controller --tail 50
```

### 3. Access the container shell
```bash
docker exec -it ec2-discord-controller /bin/bash
```

---

## Common Issues and Solutions

### Issue 1: Cannot Connect to Panel (Connection Refused)

**Symptoms:**
- "Panel Connection Error" in logs
- Panel servers showing as unavailable
- Timeout errors when clicking "Panel Servers"

**Diagnosis Steps:**

#### Step 1: Verify Network Configuration

```bash
# From your host machine
docker inspect ec2-discord-controller | grep -A 5 "Networks"
```

**Expected output:**
```json
"Networks": {
    "docker-bridge": {
        "IPAddress": "172.18.0.x",
        ...
    }
}
```

#### Step 2: Test Panel Connectivity from Container

```bash
# Enter the container
docker exec -it ec2-discord-controller /bin/bash

# Test connection to panel using internal IP
curl -v http://192.168.88.210:5080/api/client

# Test DNS resolution (if using domain)
nslookup panel.fixetics.co.za

# Test connection using domain
curl -v https://panel.fixetics.co.za/api/client
```

#### Step 3: Check Environment Variables

```bash
# Inside the container
docker exec -it ec2-discord-controller env | grep -i panel
```

**Expected output:**
```
panel_url=http://192.168.88.210:5080
get_server_url=http://192.168.88.210:5080/api/client
api=ptla_98LIFX9G5poivX2shMashnpfC4FnvRoKif3IcqbKwP4
accept_type=application/json
content_type=application/json
```

**Solutions:**

**Solution A: Network Not Connected**
```bash
# Reconnect container to docker-bridge network
docker network connect docker-bridge ec2-discord-controller

# Restart the container
docker restart ec2-discord-controller
```

**Solution B: Wrong Panel URL**

Update your [.env](.env) file:
```env
# Use internal IP instead of domain
panel_url=http://192.168.88.210:5080
get_server_url=http://192.168.88.210:5080/api/client
```

Then rebuild and restart:
```bash
docker-compose -f docker-compose.portainer.yml down
docker-compose -f docker-compose.portainer.yml up -d
```

---

### Issue 2: API Authentication Failed

**Symptoms:**
- HTTP 401 or 403 errors in logs
- "Unauthorized" or "Forbidden" messages

**Diagnosis:**

```bash
# Check if API key is set correctly
docker exec -it ec2-discord-controller env | grep ^api=
```

**Solutions:**

1. Verify your Pterodactyl API key is correct
2. Generate a new API key from Pterodactyl panel:
   - Go to Account Settings → API Credentials
   - Create a new client API key
   - Copy the key

3. Update [.env](.env):
```env
api=YOUR_NEW_API_KEY_HERE
PTERODACTYL_API_KEY=YOUR_NEW_API_KEY_HERE
```

4. Restart container:
```bash
docker restart ec2-discord-controller
```

---

### Issue 3: Panel Container Not Running

**Symptoms:**
- Connection refused even from host
- Panel not accessible in browser

**Diagnosis:**

```bash
# Check if panel container is running
docker ps -a | grep pterodactyl

# Check panel container logs
docker logs <pterodactyl-container-name>
```

**Solutions:**

1. Start the panel container:
```bash
docker start <pterodactyl-container-name>
```

2. If panel won't start, check docker-compose file and restart:
```bash
cd /path/to/pterodactyl
docker-compose up -d
```

---

### Issue 4: Network Isolation

**Symptoms:**
- Containers on different networks
- Can't ping between containers

**Diagnosis:**

```bash
# Check which network the panel is on
docker inspect <pterodactyl-container-name> | grep -A 10 "Networks"

# Check which network the bot is on
docker inspect ec2-discord-controller | grep -A 10 "Networks"
```

**Solution:**

Both containers must be on the same network. If they're not:

```bash
# Create docker-bridge network if it doesn't exist
docker network create docker-bridge

# Connect panel to docker-bridge
docker network connect docker-bridge <pterodactyl-container-name>

# Connect bot to docker-bridge (if not already)
docker network connect docker-bridge ec2-discord-controller

# Restart both containers
docker restart <pterodactyl-container-name>
docker restart ec2-discord-controller
```

---

## Detailed Debugging Session

For comprehensive troubleshooting, run this complete diagnostic:

```bash
echo "=== EC2 Bot Container Status ==="
docker ps -a | grep ec2-discord

echo -e "\n=== Network Configuration ==="
docker inspect ec2-discord-controller | grep -A 10 "Networks"

echo -e "\n=== Environment Variables ==="
docker exec -it ec2-discord-controller env | grep -E "(panel|api|PANEL|API)"

echo -e "\n=== Panel Connectivity Test (Internal IP) ==="
docker exec -it ec2-discord-controller curl -v -m 5 http://192.168.88.210:5080/api/client

echo -e "\n=== Container Logs (Last 20 lines) ==="
docker logs ec2-discord-controller --tail 20

echo -e "\n=== Testing Panel from Host ==="
curl -v http://192.168.88.210:5080/api/client
```

Copy all output and review for errors.

---

## Testing Panel Connection Manually

### From Inside the Container

```bash
# Enter container
docker exec -it ec2-discord-controller /bin/bash

# Install curl if needed (shouldn't be necessary)
# apt-get update && apt-get install -y curl

# Test API connection
curl -H "Authorization: Bearer ptla_YOUR_API_KEY" \
     -H "Accept: application/json" \
     -H "Content-Type: application/json" \
     http://192.168.88.210:5080/api/client

# Expected response: JSON with server list or user info
```

### Testing with Python

Create a test script in the container:

```bash
docker exec -it ec2-discord-controller /bin/bash
```

Then inside the container:

```bash
cat > /tmp/test_panel.py << 'EOF'
#!/usr/bin/env python3
import requests
import os

panel_url = "http://192.168.88.210:5080/api/client"
api_key = os.environ.get('api', 'YOUR_API_KEY_HERE')

headers = {
    'Authorization': f'Bearer {api_key}',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

try:
    response = requests.get(panel_url, headers=headers, timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
EOF

python3 /tmp/test_panel.py
```

**Expected output:**
```
Status Code: 200
Response: {"object":"list","data":[...]}
```

---

## Environment Variable Checklist

Ensure these variables are set correctly:

### In [.env](.env) file:
```env
# Pterodactyl Panel - NEW VARIABLES
PTERODACTYL_API_KEY=ptla_YOUR_KEY_HERE
PTERODACTYL_PANEL_URL=https://panel.fixetics.co.za
PTERODACTYL_API_URL=https://panel.fixetics.co.za/api/client

# Pterodactyl Panel - LEGACY VARIABLES (for api.py)
api=ptla_YOUR_KEY_HERE
accept_type=application/json
content_type=application/json
panel_url=http://192.168.88.210:5080
get_server_url=http://192.168.88.210:5080/api/client
```

### Verify in Container:
```bash
docker exec -it ec2-discord-controller env | grep -E "panel|api|PANEL|API" | sort
```

---

## Network Architecture

Your setup:
```
External Users
     ↓
Nginx Proxy Manager (panel.fixetics.co.za)
     ↓
192.168.88.210:5080 (Pterodactyl Panel Container)
     ↑
docker-bridge network
     ↑
EC2 Discord Bot Container
```

**Key Points:**
- Bot should connect using internal IP: `192.168.88.210:5080`
- Both containers must be on `docker-bridge` network
- Nginx proxy is only for external access
- Internal container-to-container communication bypasses the proxy

---

## Logs to Check

### Bot Logs
```bash
# Real-time logs
docker logs -f ec2-discord-controller

# Last 100 lines
docker logs ec2-discord-controller --tail 100

# Logs with timestamps
docker logs ec2-discord-controller --timestamps

# Search for panel-related errors
docker logs ec2-discord-controller 2>&1 | grep -i "panel\|connection\|error"
```

### Panel Logs
```bash
# Replace with your panel container name
docker logs -f <pterodactyl-panel-container>
```

---

## Common Error Messages and Meanings

| Error Message | Meaning | Solution |
|---------------|---------|----------|
| `Connection refused` | Panel container not running or wrong port | Check panel container status |
| `Name or service not known` | DNS resolution failed | Use IP address instead of domain |
| `Network is unreachable` | Not on same network | Connect both to docker-bridge |
| `401 Unauthorized` | Invalid API key | Generate new API key |
| `403 Forbidden` | API key lacks permissions | Use client API key, not application key |
| `Timeout` | Panel taking too long to respond | Check panel container resources |
| `SSL certificate problem` | HTTPS/TLS issue | Use HTTP for internal connections |

---

## Quick Fixes

### Fix 1: Restart Everything
```bash
docker restart ec2-discord-controller
docker restart <pterodactyl-panel-container>
```

### Fix 2: Reconnect to Network
```bash
docker network disconnect docker-bridge ec2-discord-controller
docker network connect docker-bridge ec2-discord-controller
docker restart ec2-discord-controller
```

### Fix 3: Rebuild Bot Container
```bash
docker-compose -f docker-compose.portainer.yml down
docker-compose -f docker-compose.portainer.yml pull
docker-compose -f docker-compose.portainer.yml up -d
```

### Fix 4: Use Internal IP
Edit [.env](.env) to use internal IP:
```env
panel_url=http://192.168.88.210:5080
get_server_url=http://192.168.88.210:5080/api/client
```

---

## Still Not Working?

If you've tried all the above and it's still not working:

1. **Capture full diagnostic output:**
```bash
bash -c "$(cat <<'EOF'
echo "=== System Info ===" > /tmp/panel-debug.log
date >> /tmp/panel-debug.log
echo -e "\n=== Docker Version ===" >> /tmp/panel-debug.log
docker version >> /tmp/panel-debug.log 2>&1
echo -e "\n=== Bot Container Status ===" >> /tmp/panel-debug.log
docker ps -a | grep ec2 >> /tmp/panel-debug.log
echo -e "\n=== Panel Container Status ===" >> /tmp/panel-debug.log
docker ps -a | grep pterodactyl >> /tmp/panel-debug.log
echo -e "\n=== Networks ===" >> /tmp/panel-debug.log
docker network ls >> /tmp/panel-debug.log
echo -e "\n=== Bot Network Details ===" >> /tmp/panel-debug.log
docker inspect ec2-discord-controller 2>&1 | grep -A 15 "Networks" >> /tmp/panel-debug.log
echo -e "\n=== Environment ===" >> /tmp/panel-debug.log
docker exec ec2-discord-controller env | grep -i panel >> /tmp/panel-debug.log 2>&1
echo -e "\n=== Recent Logs ===" >> /tmp/panel-debug.log
docker logs ec2-discord-controller --tail 50 >> /tmp/panel-debug.log 2>&1
cat /tmp/panel-debug.log
EOF
)"
```

2. Review the `/tmp/panel-debug.log` file

3. Check the [api.py](api.py) file is using the correct environment variables

---

## Prevention

To avoid future connection issues:

1. **Always use internal IPs** for container-to-container communication
2. **Keep both containers on the same network**
3. **Use docker-compose** for easier management
4. **Document your network setup**
5. **Test panel connection after any changes**

---

## Additional Resources

- [Docker Networking Documentation](https://docs.docker.com/network/)
- [Pterodactyl API Documentation](https://dashflo.net/docs/api/pterodactyl/v1/)
- [Discord Bot Logs](./bot.py) - Check logging configuration

## Support

For additional help, check the bot logs and compare with this guide to identify the specific issue.
