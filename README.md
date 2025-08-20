## Birthday Bot - Apprise Notifications for Configured Birthdays

<img align="left" width="100" height="100" src="https://raw.githubusercontent.com/driftywinds/birthday-bot/a4bbf916bbd13aae26a8fe6dce739f66d17a27d0/icons/birthday-gift-svgrepo-less-pad.svg"> Get notified for each and every birthday on multiple platforms!

<br>

[![Pulls](https://img.shields.io/docker/pulls/driftywinds/birthday-bot.svg?style=for-the-badge)](https://img.shields.io/docker/pulls/driftywinds/birthday-bot.svg?style=for-the-badge)

Also available on Docker Hub - [```driftywinds/birthday-bot:latest```](https://hub.docker.com/repository/docker/driftywinds/birthday-bot/general)

Commands this bot supports for each user: -

**Birthday Management:**
- `/add_birthday` - Add a new birthday
- `/list_birthdays` - View all birthdays
- `/remove_birthday` - Remove a birthday

**Notification Endpoints:**
- `/add_endpoint` - Add Apprise notification endpoint
- `/list_endpoints` - View all endpoints
- `/remove_endpoint` - Remove an endpoint

**Reminders:**
- `/add_reminder` - Add reminder schedule
- `/list_reminders` - View all reminders
- `/remove_reminder` - Remove a reminder

**Settings:**
- `/set_timezone` - Set your timezone
- `/test_notifications` - Test your notification setup

**Birthday Format:** Use MM-DD format (e.g., 03-15 for March 15)
**Apprise Format:** Any valid Apprise URL (telegram, discord, email, etc.) [(Check available endpoints and formats here)](https://github.com/caronc/apprise?tab=readme-ov-file#supported-notifications)

Examples:
- Telegram: `tgram://bot_token/chat_id`
- Discord: `discord://webhook_id/webhook_token`
- Email: `mailto://user:pass@smtp.gmail.com`

### How to use: - 

1. Download the ```compose.yml``` and ```.env``` files from the repo [here](https://github.com/driftywinds/birthday-bot).
2. Customise the ```.env``` file and use your BotFather token.
3. Run ```docker compose up -d```.

<br>

You can check logs live with this command: - 
```
docker compose logs -f
```
### For dev testing: -
- have python3 installed on your machine
- clone the repo
- go into the directory and run these commands: -
```
python3 -m venv .venv
source .venv/bin/activate
pip install --no-cache-dir -r requirements.txt
```  
- configure ```.env``` variable.
- then run ```python3 bot.py```
