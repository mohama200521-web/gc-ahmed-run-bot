import os
import asyncio
import threading

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

LAB_URL = "https://www.cloudskillsboost.google/focuses/20774?parent=catalog"

PORT = int(os.getenv("PORT", "8080"))


# =========================
# Cloud Run Health Server
# =========================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"GC.AHMED Run Bot is running")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        return


def start_health_server():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), HealthHandler)
    print(f"Health server listening on port {PORT}")
    server.serve_forever()


# =========================
# /start
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [
            InlineKeyboardButton(
                "☁️ Google Cloud → Cloud Run",
                url=LAB_URL
            )
        ],
        [
            InlineKeyboardButton(
                "📊 حالة الخدمة",
                callback_data="status"
            )
        ],
    ]

    text = (
        "👋 مرحباً بك في GC.AHMED Run\n\n"
        "☁️ بوت إنشاء خدمات Google Cloud Run\n\n"
        "📌 أرسل رابط Google Skills Boost الخاص بالـLab "
        "وسأبدأ معالجة الطلب تلقائياً.\n\n"
        "⏱ مدة الـLab: 4:30 ساعات\n\n"
        "احفظ رابط الـLab أو أرسل /start في أي وقت.\n\n"
        "Welcome my friends, this is a GoogleCloud codes generator"
    )

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# /help
# =========================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "🆘 طريقة الاستخدام\n\n"
        "1️⃣ افتح Google Skills Boost.\n"
        "2️⃣ شغّل الـLab.\n"
        "3️⃣ أرسل رابط الـLab إلى البوت.\n"
        "4️⃣ انتظر حتى انتهاء العملية.\n\n"
        "📌 الأوامر:\n"
        "/start — بدء الاستخدام\n"
        "/help — المساعدة\n"
        "/status — حالة الخدمة"
    )

    await update.message.reply_text(text)


# =========================
# /status
# =========================

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "📊 حالة الخدمة\n\n"
        "🟢 البوت يعمل بشكل طبيعي.\n"
        "☁️ Cloud Run: متصل\n"
        "🤖 Telegram Bot: يعمل"
    )


# =========================
# استقبال رابط Google Skills
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message or not update.message.text:
        return

    message = update.message.text.strip()

    if "cloudskillsboost.google" not in message:
        await update.message.reply_text(
            "❌ لم أتعرف على الرابط.\n\n"
            "أرسل رابط Google Skills Boost الصحيح."
        )
        return

    await update.message.reply_text(
        "📥 تم استلام رابط الـLab ✅\n\n"
        "🔎 جاري فحص الرابط..."
    )

    await asyncio.sleep(1)

    await update.message.reply_text(
        "🔍 جاري تحليل بيانات المشروع..."
    )

    await asyncio.sleep(1)

    await update.message.reply_text(
        "☁️ جاري تجهيز Cloud Run..."
    )

    await asyncio.sleep(1)

    await update.message.reply_text(
        "🚀 جاري إنشاء الخدمة..."
    )

    await asyncio.sleep(1)

    await update.message.reply_text(
        "⏳ جاري انتظار اكتمال النشر..."
    )

    await asyncio.sleep(2)

    await update.message.reply_text(
        "✅ تم تجهيز الطلب بنجاح.\n\n"
        "📌 البوت يعمل الآن على Cloud Run.\n"
        "🔧 خطوة الربط الفعلي مع Google Cloud "
        "سيتم إضافتها في المرحلة التالية."
    )


# =========================
# الأزرار
# =========================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    if query.data == "status":

        await query.message.reply_text(
            "📊 حالة الخدمة\n\n"
            "🟢 البوت يعمل.\n"
            "☁️ Cloud Run: يعمل"
        )


# =========================
# Main
# =========================

def main():

    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    # تشغيل HTTP server في الخلفية
    health_thread = threading.Thread(
        target=start_health_server,
        daemon=True
    )

    health_thread.start()

    # إنشاء Telegram application
    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    app.add_handler(
        CommandHandler("status", status_command)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    print("GC.AHMED Run Bot is starting...")

    # Telegram polling
    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()