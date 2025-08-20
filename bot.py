import json
import os
import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional
import apprise
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import pytz
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class BirthdayBot:
    def __init__(self, token: str):
        self.token = token
        self.data_file = 'birthdays.json'
        self.users_data = self.load_data()
        self.pending_endpoints = {}  # Store pending endpoints for confirmation
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
        
    def load_data(self) -> Dict:
        """Load user data from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error("Error reading JSON file, starting with empty data")
                return {}
        return {}
    
    def save_data(self):
        """Save user data to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.users_data, f, indent=2, default=str)
    
    def get_user_data(self, user_id: str) -> Dict:
        """Get or create user data"""
        if user_id not in self.users_data:
            self.users_data[user_id] = {
                'birthdays': {},
                'apprise_endpoints': [],
                'reminders': [],
                'timezone': 'UTC'
            }
        return self.users_data[user_id]
    
    def setup_handlers(self):
        """Setup command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("add_birthday", self.add_birthday))
        self.application.add_handler(CommandHandler("list_birthdays", self.list_birthdays))
        self.application.add_handler(CommandHandler("remove_birthday", self.remove_birthday))
        self.application.add_handler(CommandHandler("add_endpoint", self.add_endpoint))
        self.application.add_handler(CommandHandler("list_endpoints", self.list_endpoints))
        self.application.add_handler(CommandHandler("remove_endpoint", self.remove_endpoint))
        self.application.add_handler(CommandHandler("add_reminder", self.add_reminder))
        self.application.add_handler(CommandHandler("list_reminders", self.list_reminders))
        self.application.add_handler(CommandHandler("remove_reminder", self.remove_reminder))
        self.application.add_handler(CommandHandler("set_timezone", self.set_timezone))
        self.application.add_handler(CommandHandler("test_notifications", self.test_notifications))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        welcome_message = """
🎉 Welcome to Birthday Reminder Bot! 🎉

I'll help you remember all the important birthdays and send notifications through various channels.

Use /help to see all available commands.
        """
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command handler"""
        help_text = """
📋 **Available Commands:**

**Birthday Management:**
• `/add_birthday` - Add a new birthday
• `/list_birthdays` - View all birthdays
• `/remove_birthday` - Remove a birthday

**Notification Endpoints:**
• `/add_endpoint` - Add Apprise notification endpoint
• `/list_endpoints` - View all endpoints
• `/remove_endpoint` - Remove an endpoint

**Reminders:**
• `/add_reminder` - Add reminder schedule
• `/list_reminders` - View all reminders
• `/remove_reminder` - Remove a reminder

**Settings:**
• `/set_timezone` - Set your timezone
• `/test_notifications` - Test your notification setup

**Birthday Format:** Use MM-DD format (e.g., 03-15 for March 15)
**Apprise Format:** Any valid Apprise URL (telegram, discord, email, etc.)

Examples:
- Telegram: `tgram://bot_token/chat_id`
- Discord: `discord://webhook_id/webhook_token`
- Email: `mailto://user:pass@smtp.gmail.com`
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def add_birthday(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add birthday command handler"""
        if len(context.args) < 2:
            await update.message.reply_text(
                "Usage: /add_birthday <name> <date>\n"
                "Example: /add_birthday John 03-15\n"
                "Date format: MM-DD (March 15)"
            )
            return
        
        user_id = str(update.effective_user.id)
        user_data = self.get_user_data(user_id)
        
        name = context.args[0]
        date_str = context.args[1]
        
        try:
            # Validate date format
            datetime.strptime(date_str, '%m-%d')
            user_data['birthdays'][name] = date_str
            self.save_data()
            
            await update.message.reply_text(f"✅ Birthday added: {name} on {date_str}")
        except ValueError:
            await update.message.reply_text("❌ Invalid date format. Use MM-DD (e.g., 03-15)")
    
    async def list_birthdays(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all birthdays"""
        user_id = str(update.effective_user.id)
        user_data = self.get_user_data(user_id)
        
        if not user_data['birthdays']:
            await update.message.reply_text("📅 No birthdays stored yet.")
            return
        
        message = "📅 **Your Birthdays:**\n\n"
        for name, date in user_data['birthdays'].items():
            next_birthday = self.get_next_birthday_date(date)
            days_until = (next_birthday - datetime.now().date()).days
            message += f"• {name}: {date} ({days_until} days until next birthday)\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def remove_birthday(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove birthday command handler"""
        if len(context.args) < 1:
            await update.message.reply_text("Usage: /remove_birthday <name>")
            return
        
        user_id = str(update.effective_user.id)
        user_data = self.get_user_data(user_id)
        
        name = context.args[0]
        if name in user_data['birthdays']:
            del user_data['birthdays'][name]
            self.save_data()
            await update.message.reply_text(f"✅ Removed birthday for {name}")
        else:
            await update.message.reply_text(f"❌ No birthday found for {name}")
    
    async def add_endpoint(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add Apprise endpoint with confirmation"""
        if len(context.args) < 1:
            await update.message.reply_text(
                "Usage: /add_endpoint <apprise_url>\n"
                "Example: /add_endpoint mailto://user:pass@smtp.gmail.com"
            )
            return
        
        user_id = str(update.effective_user.id)
        user_data = self.get_user_data(user_id)
        
        endpoint = ' '.join(context.args)
        
        # Test the endpoint first
        apobj = apprise.Apprise()
        if not apobj.add(endpoint):
            await update.message.reply_text("❌ Invalid Apprise endpoint format")
            return
        
        # Send test notification
        test_title = "🧪 Birthday Bot Test"
        test_message = "This is a test notification to verify your endpoint is working correctly. Please confirm if you received this message."
        
        try:
            success = apobj.notify(body=test_message, title=test_title)
            if not success:
                await update.message.reply_text("❌ Failed to send test notification to this endpoint")
                return
        except Exception as e:
            await update.message.reply_text(f"❌ Error testing endpoint: {str(e)}")
            return
        
        # Store endpoint temporarily for confirmation
        self.pending_endpoints[user_id] = endpoint
        
        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, I received it", callback_data="confirm_endpoint_yes"),
                InlineKeyboardButton("❌ No, I didn't receive it", callback_data="confirm_endpoint_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📡 Test notification sent to:\n`{self.mask_sensitive_info(endpoint)}`\n\n"
            "Did you receive the test notification?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def list_endpoints(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all notification endpoints"""
        user_id = str(update.effective_user.id)
        user_data = self.get_user_data(user_id)
        
        if not user_data['apprise_endpoints']:
            await update.message.reply_text("📡 No notification endpoints configured.")
            return
        
        message = "📡 **Notification Endpoints:**\n\n"
        for i, endpoint in enumerate(user_data['apprise_endpoints'], 1):
            # Hide sensitive information in display
            display_endpoint = self.mask_sensitive_info(endpoint)
            message += f"{i}. {display_endpoint}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    def mask_sensitive_info(self, endpoint: str) -> str:
        """Mask sensitive information in endpoints for display"""
        # Basic masking for common patterns
        if 'mailto://' in endpoint:
            parts = endpoint.split('@')
            if len(parts) > 1:
                return f"mailto://***@{parts[-1]}"
        elif 'tgram://' in endpoint:
            return "tgram://*** (Telegram)"
        elif 'discord://' in endpoint:
            return "discord://*** (Discord Webhook)"
        return endpoint[:20] + "..." if len(endpoint) > 20 else endpoint
    
    async def remove_endpoint(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove notification endpoint"""
        user_id = str(update.effective_user.id)
        user_data = self.get_user_data(user_id)
        
        if not user_data['apprise_endpoints']:
            await update.message.reply_text("📡 No endpoints to remove.")
            return
        
        # Create inline keyboard with endpoints
        keyboard = []
        for i, endpoint in enumerate(user_data['apprise_endpoints']):
            display_endpoint = self.mask_sensitive_info(endpoint)
            keyboard.append([InlineKeyboardButton(
                f"{i+1}. {display_endpoint}", 
                callback_data=f"remove_endpoint_{i}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Select endpoint to remove:", 
            reply_markup=reply_markup
        )
    
    async def add_reminder(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add reminder schedule"""
        if len(context.args) < 2:
            await update.message.reply_text(
                "Usage: /add_reminder <type> <value>\n\n"
                "Types:\n"
                "• `minutes_before` - Minutes before birthday (e.g., 15)\n"
                "• `hours_before` - Hours before birthday (e.g., 24)\n"
                "• `days_before` - Days before birthday (e.g., 1)\n"
                "• `time_on_day` - Specific time on birthday (e.g., 09:00)\n"
                "• `time_before` - Specific time before birthday (e.g., 1:18:00 = 1 day, 18:00)"
            )
            return
        
        user_id = str(update.effective_user.id)
        user_data = self.get_user_data(user_id)
        
        reminder_type = context.args[0]
        value = context.args[1]
        
        reminder = {'type': reminder_type, 'value': value}
        
        try:
            # Validate reminder format
            self.validate_reminder(reminder)
            user_data['reminders'].append(reminder)
            self.save_data()
            
            await update.message.reply_text(f"✅ Reminder added: {reminder_type} = {value}")
        except ValueError as e:
            await update.message.reply_text(f"❌ Invalid reminder format: {str(e)}")
    
    def validate_reminder(self, reminder: Dict):
        """Validate reminder format"""
        reminder_type = reminder['type']
        value = reminder['value']
        
        if reminder_type in ['minutes_before', 'hours_before', 'days_before']:
            int(value)  # Will raise ValueError if not a valid integer
        elif reminder_type == 'time_on_day':
            datetime.strptime(value, '%H:%M')  # Will raise ValueError if not HH:MM
        elif reminder_type == 'time_before':
            # Format: D:HH:MM (days:hours:minutes)
            parts = value.split(':')
            if len(parts) != 3:
                raise ValueError("time_before format should be D:HH:MM")
            int(parts[0])  # days
            datetime.strptime(f"{parts[1]}:{parts[2]}", '%H:%M')  # time
        else:
            raise ValueError(f"Unknown reminder type: {reminder_type}")
    
    async def list_reminders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all reminders"""
        user_id = str(update.effective_user.id)
        user_data = self.get_user_data(user_id)
        
        if not user_data['reminders']:
            await update.message.reply_text("⏰ No reminders configured.")
            return
        
        message = "⏰ **Your Reminders:**\n\n"
        for i, reminder in enumerate(user_data['reminders'], 1):
            message += f"{i}. {reminder['type']}: {reminder['value']}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def remove_reminder(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove reminder"""
        if len(context.args) < 1:
            await update.message.reply_text("Usage: /remove_reminder <number>")
            return
        
        user_id = str(update.effective_user.id)
        user_data = self.get_user_data(user_id)
        
        try:
            index = int(context.args[0]) - 1
            if 0 <= index < len(user_data['reminders']):
                removed = user_data['reminders'].pop(index)
                self.save_data()
                await update.message.reply_text(
                    f"✅ Removed reminder: {removed['type']} = {removed['value']}"
                )
            else:
                await update.message.reply_text("❌ Invalid reminder number")
        except ValueError:
            await update.message.reply_text("❌ Please provide a valid number")
    
    async def set_timezone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set user timezone"""
        if len(context.args) < 1:
            await update.message.reply_text(
                "Usage: /set_timezone <timezone>\n"
                "Example: /set_timezone America/New_York\n"
                "Common timezones: UTC, US/Eastern, US/Pacific, Europe/London, Asia/Tokyo"
            )
            return
        
        user_id = str(update.effective_user.id)
        user_data = self.get_user_data(user_id)
        
        timezone = context.args[0]
        try:
            pytz.timezone(timezone)  # Validate timezone
            user_data['timezone'] = timezone
            self.save_data()
            await update.message.reply_text(f"✅ Timezone set to {timezone}")
        except pytz.exceptions.UnknownTimeZoneError:
            await update.message.reply_text("❌ Invalid timezone")
    
    async def test_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test notification setup"""
        user_id = str(update.effective_user.id)
        user_data = self.get_user_data(user_id)
        
        if not user_data['apprise_endpoints']:
            await update.message.reply_text("❌ No notification endpoints configured")
            return
        
        success_count = await self.send_notification(
            user_id, 
            "🧪 Test Notification", 
            "This is a test message from Birthday Bot!"
        )
        
        total_endpoints = len(user_data['apprise_endpoints'])
        await update.message.reply_text(
            f"📡 Test complete: {success_count}/{total_endpoints} endpoints successful"
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(query.from_user.id)
        
        if query.data.startswith("remove_endpoint_"):
            index = int(query.data.split("_")[-1])
            user_data = self.get_user_data(user_id)
            
            if 0 <= index < len(user_data['apprise_endpoints']):
                removed = user_data['apprise_endpoints'].pop(index)
                self.save_data()
                await query.edit_message_text(
                    f"✅ Removed endpoint: {self.mask_sensitive_info(removed)}"
                )
            else:
                await query.edit_message_text("❌ Invalid endpoint selection")
        
        elif query.data == "confirm_endpoint_yes":
            # User confirmed they received the test notification
            if user_id in self.pending_endpoints:
                endpoint = self.pending_endpoints[user_id]
                user_data = self.get_user_data(user_id)
                
                user_data['apprise_endpoints'].append(endpoint)
                
                # Always ensure telegram endpoint is included
                telegram_endpoint = f"tgram://{self.token}/{query.message.chat.id}"
                if telegram_endpoint not in user_data['apprise_endpoints']:
                    user_data['apprise_endpoints'].append(telegram_endpoint)
                
                self.save_data()
                del self.pending_endpoints[user_id]
                
                await query.edit_message_text(
                    f"✅ Endpoint added successfully!\n"
                    f"📡 {self.mask_sensitive_info(endpoint)}\n\n"
                    f"You now have {len(user_data['apprise_endpoints'])} notification endpoint(s) configured."
                )
            else:
                await query.edit_message_text("❌ No pending endpoint to confirm")
        
        elif query.data == "confirm_endpoint_no":
            # User didn't receive the test notification
            if user_id in self.pending_endpoints:
                endpoint = self.pending_endpoints[user_id]
                del self.pending_endpoints[user_id]
                
                await query.edit_message_text(
                    f"❌ Endpoint not added due to failed test:\n"
                    f"📡 {self.mask_sensitive_info(endpoint)}\n\n"
                    "Please check your endpoint configuration and try again. "
                    "Make sure the URL format is correct and the service is accessible."
                )
            else:
                await query.edit_message_text("❌ No pending endpoint to cancel")
    
    def get_next_birthday_date(self, birthday_str: str) -> datetime.date:
        """Get next occurrence of birthday"""
        current_year = datetime.now().year
        month, day = map(int, birthday_str.split('-'))
        
        next_birthday = datetime(current_year, month, day).date()
        
        # If birthday already passed this year, use next year
        if next_birthday < datetime.now().date():
            next_birthday = datetime(current_year + 1, month, day).date()
        
        return next_birthday
    
    def calculate_reminder_time(self, birthday_date: datetime.date, reminder: Dict, timezone_str: str) -> datetime:
        """Calculate when to send reminder based on birthday and reminder settings"""
        tz = pytz.timezone(timezone_str)
        
        reminder_type = reminder['type']
        value = reminder['value']
        
        if reminder_type == 'minutes_before':
            reminder_datetime = datetime.combine(birthday_date, time(0, 0))
            reminder_datetime -= timedelta(minutes=int(value))
        elif reminder_type == 'hours_before':
            reminder_datetime = datetime.combine(birthday_date, time(0, 0))
            reminder_datetime -= timedelta(hours=int(value))
        elif reminder_type == 'days_before':
            reminder_datetime = datetime.combine(birthday_date - timedelta(days=int(value)), time(9, 0))
        elif reminder_type == 'time_on_day':
            reminder_time = datetime.strptime(value, '%H:%M').time()
            reminder_datetime = datetime.combine(birthday_date, reminder_time)
        elif reminder_type == 'time_before':
            days, time_str = value.split(':', 1)
            reminder_time = datetime.strptime(time_str, '%H:%M').time()
            target_date = birthday_date - timedelta(days=int(days))
            reminder_datetime = datetime.combine(target_date, reminder_time)
        
        # Localize to user's timezone then convert to UTC
        reminder_datetime = tz.localize(reminder_datetime).astimezone(pytz.UTC)
        return reminder_datetime
    
    async def send_notification(self, user_id: str, title: str, message: str) -> int:
        """Send notification to all configured endpoints"""
        user_data = self.get_user_data(user_id)
        
        if not user_data['apprise_endpoints']:
            return 0
        
        apobj = apprise.Apprise()
        
        # Add all endpoints
        for endpoint in user_data['apprise_endpoints']:
            apobj.add(endpoint)
        
        # Send notification
        try:
            success = apobj.notify(body=message, title=title)
            return len(user_data['apprise_endpoints']) if success else 0
        except Exception as e:
            logger.error(f"Notification error for user {user_id}: {str(e)}")
            return 0
    
    async def check_birthdays(self):
        """Check for upcoming birthdays and send reminders"""
        logger.info("Checking birthdays...")
        current_time = datetime.now(pytz.UTC)
        
        for user_id, user_data in self.users_data.items():
            if not user_data['birthdays'] or not user_data['reminders']:
                continue
            
            timezone_str = user_data.get('timezone', 'UTC')
            
            for name, birthday_str in user_data['birthdays'].items():
                next_birthday = self.get_next_birthday_date(birthday_str)
                
                for reminder in user_data['reminders']:
                    try:
                        reminder_time = self.calculate_reminder_time(
                            next_birthday, reminder, timezone_str
                        )
                        
                        # Check if it's time to send reminder (within 1 minute window)
                        time_diff = abs((current_time - reminder_time).total_seconds())
                        
                        if time_diff <= 60:  # Within 1 minute
                            age = datetime.now().year - 2000  # Approximate age calculation
                            title = f"🎂 Birthday Reminder: {name}"
                            message = f"Don't forget! {name}'s birthday is coming up on {birthday_str}!"
                            
                            if reminder['type'] == 'time_on_day':
                                message = f"🎉 It's {name}'s birthday today! 🎉"
                            
                            await self.send_notification(user_id, title, message)
                            logger.info(f"Sent reminder for {name} to user {user_id}")
                            
                    except Exception as e:
                        logger.error(f"Error processing reminder for {name}: {str(e)}")
    
    async def run_birthday_checker(self):
        """Run periodic birthday checker"""
        while True:
            try:
                await self.check_birthdays()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in birthday checker: {str(e)}")
                await asyncio.sleep(60)
    
    async def post_init(self, application):
        """Initialize background tasks after the application starts"""
        asyncio.create_task(self.run_birthday_checker())
    
    def run(self):
        """Run the bot"""
        # Set up post-init callback to start background tasks
        self.application.post_init = self.post_init
        
        # Run the bot
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN not found in environment variables")
        print("Please create a .env file with your bot token:")
        print("BOT_TOKEN=your_bot_token_here")
        exit(1)
    
    bot = BirthdayBot(BOT_TOKEN)
    bot.run()
