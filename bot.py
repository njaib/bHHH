import os
import io
import threading
import logging
from flask import Flask
import telebot
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ─────────────────────────────────────────────
#  Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("bot")

# ─────────────────────────────────────────────
#  Config
# ─────────────────────────────────────────────
BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_TOKEN_HERE")
TARGET_URL = os.environ.get(
    "TARGET_URL",
    "https://khorasantelecom.co/transactions/receipts?tab=all",
)
PORT = int(os.environ.get("PORT", 10000))

# ─────────────────────────────────────────────
#  Flask  — زنده نگه‌داشتن Render
# ─────────────────────────────────────────────
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running.", 200

@app.route("/health")
def health():
    return {"status": "ok"}, 200

def start_flask():
    log.info("Flask starting on 0.0.0.0:%d", PORT)
    app.run(host="0.0.0.0", port=PORT, use_reloader=False, threaded=True)

# ─────────────────────────────────────────────
#  Screenshot
# ─────────────────────────────────────────────
LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-software-rasterizer",
    "--no-zygote",
    "--single-process",
]

def capture_screenshot(url: str) -> bytes:
    """باز کردن URL و برگرداندن PNG — بدون ذخیره فایل روی دیسک."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=LAUNCH_ARGS)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            ignore_https_errors=True,
            java_script_enabled=True,
        )
        page = ctx.new_page()
        log.info("Navigating -> %s", url)
        page.goto(url, timeout=60_000, wait_until="networkidle")
        page.wait_for_timeout(2500)
        png = page.screenshot(full_page=True, type="png")
        browser.close()
    log.info("Screenshot captured — %d bytes", len(png))
    return png

# ─────────────────────────────────────────────
#  Telegram Bot
# ─────────────────────────────────────────────
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

@bot.message_handler(commands=["start", "screenshot"])
def cmd_start(message):
    chat_id = message.chat.id
    log.info("/start from chat_id=%s", chat_id)

    wait_msg = bot.send_message(
        chat_id,
        "📸 در حال گرفتن اسکرین‌شات...\n⏳ لطفاً چند ثانیه صبر کنید.",
    )

    try:
        png_bytes = capture_screenshot(TARGET_URL)
        bot.send_photo(
            chat_id,
            photo=io.BytesIO(png_bytes),
            caption=f"✅ اسکرین‌شات از:\n{TARGET_URL}",
        )
        bot.delete_message(chat_id, wait_msg.message_id)

    except PlaywrightTimeout:
        log.warning("Timeout for chat_id=%s", chat_id)
        bot.edit_message_text(
            "⏰ سایت در زمان مقرر پاسخ نداد. دوباره امتحان کنید.",
            chat_id, wait_msg.message_id,
        )
    except Exception as exc:
        log.exception("Screenshot failed for chat_id=%s", chat_id)
        bot.edit_message_text(
            f"❌ خطا:\n{exc}",
            chat_id, wait_msg.message_id,
        )

@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.reply_to(message, "برای اسکرین‌شات دستور /start را بفرستید.")

# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=start_flask, daemon=True).start()
    log.info("Bot polling started ...")
    bot.infinity_polling(timeout=30, long_polling_timeout=30, none_stop=True, interval=1)
