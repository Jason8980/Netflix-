import os
import random
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------------- CONFIG ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Set this in Render
CHANNEL_USERNAME = "@freemovieappp"       # Your channel username (with @)
APK_MESSAGE_ID = 2                        # Message ID of your APK in the channel
REF_TARGET = 3                             # Number of referrals required
# ----------------------------------------

# ----------- DATABASE SETUP ------------
conn = sqlite3.connect("referrals.db", check_same_thread=False)
c = conn.cursor()

# Users table
c.execute('''CREATE TABLE IF NOT EXISTS users
             (user_id INTEGER PRIMARY KEY,
              ref_code TEXT,
              referrals INTEGER,
              referred_by TEXT)''')

# Referral history table
c.execute('''CREATE TABLE IF NOT EXISTS referrals
             (referrer_id INTEGER,
              referee_id INTEGER,
              PRIMARY KEY (referrer_id, referee_id))''')
conn.commit()

# ----------- HELPER FUNCTIONS -----------
def get_or_create_user(user_id, ref_by=None):
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if not user:
        ref_code = str(random.randint(100000, 999999))
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user_id, ref_code, 0, ref_by))
        conn.commit()
        return user_id, ref_code, 0
    else:
        return user[0], user[1], user[2]

async def process_referral(update: Update, context: ContextTypes.DEFAULT_TYPE, ref_by_code):
    if not ref_by_code:
        return
    c.execute("SELECT * FROM users WHERE ref_code=?", (ref_by_code,))
    ref_user = c.fetchone()
    if not ref_user or ref_user[0] == update.message.from_user.id:
        return
    # Check if already counted
    c.execute("SELECT * FROM referrals WHERE referrer_id=? AND referee_id=?",
              (ref_user[0], update.message.from_user.id))
    if c.fetchone():
        return
    # Count referral
    new_count = ref_user[2] + 1
    c.execute("UPDATE users SET referrals=? WHERE user_id=?", (new_count, ref_user[0]))
    c.execute("INSERT INTO referrals VALUES (?, ?)", (ref_user[0], update.message.from_user.id))
    conn.commit()
    # Send progress or APK
    if new_count >= REF_TARGET:
        try:
            await context.bot.forward_message(chat_id=ref_user[0],
                                              from_chat_id=CHANNEL_USERNAME,
                                              message_id=APK_MESSAGE_ID)
            await context.bot.send_message(ref_user[0], "🎉 Congrats! You unlocked your APK after 3 referrals.")
        except:
            await context.bot.send_message(ref_user[0], "❌ Could not send APK. Make sure your bot is admin in the channel.")
    else:
        await context.bot.send_message(ref_user[0], f"🔔 Progress: {new_count}/{REF_TARGET} referrals done.")

# ----------- /START COMMAND -----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args
    ref_by = args[0] if args else None

    # Step 1: Ask user to join private channel
    await update.message.reply_text(f"🚫 You must join the private channel first!\nJoin here: {CHANNEL_USERNAME}")
    
    # Step 2: Process referral (counts only if user returns after joining)
    await process_referral(update, context, ref_by)

    # Step 3: Create/get user referral code
    user_id, ref_code, referrals = get_or_create_user(user_id, ref_by)
    await update.message.reply_text(
        f"👋 Welcome!\n\nYour referral link:\n"
        f"https://t.me/{context.bot.username}?start={ref_code}\n\n"
        f"Share with 3 friends. Once 3 people start using your link, you'll get your APK!"
    )

# ----------- RUN BOT -----------
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Bot is running...")
    app.run_polling()
