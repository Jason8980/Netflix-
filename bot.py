import os
import random
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ========== CONFIG ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Set this in Render or Koyeb
CHANNEL_USERNAME = "@Elite_LearnersHub"  # Your public channel username
CHANNEL_ID = -1002547446027              # Channel chat ID
APK_MESSAGE_ID = 2                       # Message ID of your MovieBox APK in the channel
REF_TARGET = 3                           # Number of referrals required
# =============================

# ---------- DATABASE ----------
conn = sqlite3.connect("referrals.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    ref_code TEXT,
    referrals INTEGER DEFAULT 0,
    referred_by TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS referrals (
    referrer_id INTEGER,
    referee_id INTEGER,
    PRIMARY KEY (referrer_id, referee_id)
)
""")
conn.commit()

# ---------- HELPER FUNCTIONS ----------
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

async def is_user_in_channel(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def process_referral(update: Update, context: ContextTypes.DEFAULT_TYPE, ref_by_code):
    if not ref_by_code:
        return
    c.execute("SELECT * FROM users WHERE ref_code=?", (ref_by_code,))
    ref_user = c.fetchone()
    if not ref_user or ref_user[0] == update.message.from_user.id:
        return

    # Check if already referred
    c.execute("SELECT * FROM referrals WHERE referrer_id=? AND referee_id=?",
              (ref_user[0], update.message.from_user.id))
    if c.fetchone():
        return

    # Count referral
    new_count = ref_user[2] + 1
    c.execute("UPDATE users SET referrals=? WHERE user_id=?", (new_count, ref_user[0]))
    c.execute("INSERT INTO referrals VALUES (?, ?)", (ref_user[0], update.message.from_user.id))
    conn.commit()

    # Send progress / APK
    if new_count >= REF_TARGET:
        try:
            await context.bot.forward_message(
                chat_id=ref_user[0],
                from_chat_id=CHANNEL_USERNAME,
                message_id=APK_MESSAGE_ID
            )
            await context.bot.send_message(
                ref_user[0],
                "🎉 *Access Granted!*\n\nYou've unlocked your 🎬 MovieBox APK!\nEnjoy streaming Netflix 🍿, Prime 🎥, and Disney+ ✨ content for free!",
                parse_mode="Markdown"
            )
        except Exception as e:
            await context.bot.send_message(
                ref_user[0],
                f"⚠️ Could not send APK (check bot admin rights).\n\nError: {str(e)}"
            )
    else:
        await context.bot.send_message(
            ref_user[0],
            f"🔔 *Referral Progress:* {new_count}/{REF_TARGET}\n\nInvite more friends to unlock your 🎁 MovieBox APK!",
            parse_mode="Markdown"
        )

# ---------- COMMAND HANDLERS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args
    ref_by = args[0] if args else None

    # Check if user is in channel
    joined = await is_user_in_channel(context, user_id)
    if not joined:
        await update.message.reply_text(
            "🚫 **Access Denied!**\n\n"
            "🎬 To access *Netflix, Prime Video & Disney+ MovieBox APKs*, you must first join our VIP channel:\n\n"
            f"👉 {CHANNEL_USERNAME}\n\n"
            "After joining, tap /start again 🍿",
            parse_mode="Markdown"
        )
        return

    # Process referral
    await process_referral(update, context, ref_by)

    # Get or create user
    user_id, ref_code, referrals = get_or_create_user(user_id, ref_by)

    await update.message.reply_text(
        f"🎉 **Access Granted!**\n\n"
        f"Welcome to *Netflix 🍿 | Prime 🎥 | Disney+ ✨ Zone!*\n\n"
        f"Here’s your personal referral link:\n"
        f"🔗 https://t.me/{context.bot.username}?start={ref_code}\n\n"
        f"🎁 Share this with {REF_TARGET} friends — once they start the bot using your link, "
        f"you’ll automatically receive the 🎬 MovieBox APK directly in chat!"
        f"\n\n🔥 _Keep sharing and enjoy unlimited entertainment!_",
        parse_mode="Markdown"
    )

# ---------- RUN ----------
if __name__ == "__main__":
    print("🚀 Bot is running...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
