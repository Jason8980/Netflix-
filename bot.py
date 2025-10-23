import os
import random
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------------- CONFIG ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Set this in Render/Koyeb
PRIVATE_CHANNEL_ID = -1002547446027       # Your private channel ID
PRIVATE_CHANNEL_LINK = "https://t.me/+LD4fserLHFMxMmQ1"  # Invite link to private channel
APK_CHANNEL_USERNAME = "@freemovieappp"   # Channel where MovieBox APK is posted
APK_MESSAGE_ID = 2                        # Message ID of your MovieBox APK
REF_TARGET = 3                            # Number of referrals needed
# ----------------------------------------

# ----------- DATABASE SETUP ------------
conn = sqlite3.connect("referrals.db", check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users
             (user_id INTEGER PRIMARY KEY,
              ref_code TEXT,
              referrals INTEGER,
              referred_by TEXT)''')

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

def make_progress_bar(current, total):
    filled = "🟥" * current
    empty = "⬜" * (total - current)
    return f"{filled}{empty}"

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
            await context.bot.forward_message(
                chat_id=ref_user[0],
                from_chat_id=APK_CHANNEL_USERNAME,
                message_id=APK_MESSAGE_ID
            )
            await context.bot.send_message(
                ref_user[0],
                "🎉 **Binge-Unlocked!**\n\n🍿 Congratulations, you’ve successfully referred 3 friends!\n\n🎬 Your MovieBox APK is now unlocked and sent below 👇"
            )
        except Exception as e:
            await context.bot.send_message(ref_user[0], f"❌ Oops! Couldn’t send the APK. Error: {e}")
    else:
        progress_bar = make_progress_bar(new_count, REF_TARGET)
        await context.bot.send_message(
            ref_user[0],
            f"🍿 *Referral Progress:*\n\n{progress_bar} {new_count}/{REF_TARGET}\n\n"
            "🎯 Keep sharing your link to unlock MovieBox APK!"
        )

# ----------- /START COMMAND -----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args
    ref_by = args[0] if args else None

    # Step 1: Verify channel membership
    try:
        member = await context.bot.get_chat_member(PRIVATE_CHANNEL_ID, user_id)
        if member.status not in ["member", "administrator", "creator"]:
            await update.message.reply_text(
                f"🚫 **Access Denied!**\n\n🎥 To access Netflix, Prime Video & Disney+ MovieBox APKs,\n"
                f"you must first join our private VIP channel:\n\n👉 {PRIVATE_CHANNEL_LINK}\n\n"
                "After joining, tap /start again 🍿"
            )
            return
    except Exception:
        await update.message.reply_text(
            f"🚫 **Access Denied!**\n\n🎥 To access Netflix, Prime Video & Disney+ MovieBox APKs,\n"
            f"you must first join our private VIP channel:\n\n👉 {PRIVATE_CHANNEL_LINK}\n\n"
            "After joining, tap /start again 🍿"
        )
        return

    # Step 2: Process referral
    await process_referral(update, context, ref_by)

    # Step 3: Generate referral link
    user_id, ref_code, referrals = get_or_create_user(user_id, ref_by)
    progress_bar = make_progress_bar(referrals, REF_TARGET)

    await update.message.reply_text(
        f"👋 **Welcome to MovieBox+!**\n\n"
        f"🎬 Stream your favorite shows from:\n"
        f"🍿 Netflix | 🎥 Prime Video | ✨ Disney+ Hotstar\n\n"
        f"🔗 *Your referral link:*\n"
        f"https://t.me/{context.bot.username}?start={ref_code}\n\n"
        f"📢 Share this link with your friends!\n"
        f"When 3 people join using it, your MovieBox APK will be unlocked! 🎁\n\n"
        f"📊 *Your current progress:*\n{progress_bar} {referrals}/{REF_TARGET}"
    )

# ----------- RUN BOT -----------
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("🚀 MovieBox+ Bot is now LIVE 🍿")
    app.run_polling()
