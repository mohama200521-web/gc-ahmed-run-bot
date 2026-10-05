import os
import asyncio
import threading
import re

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

from google.api_core.exceptions import AlreadyExists, GoogleAPICallError
from google.cloud import run_v2


# ============================================================
# Environment
# ============================================================

TOKEN = os.getenv("BOT_TOKEN")

PORT = int(os.getenv("PORT", "8080"))

REGION = os.getenv("CLOUD_RUN_REGION", "us-central1")

# صورة Docker التي سيتم نشرها في Cloud Run
DEPLOY_IMAGE = os.getenv(
    "DEPLOY_IMAGE",
    "us-docker.pkg.dev/cloudrun/container/hello:latest"
)

# اسم الخدمة التي سينشئها البوت
DEFAULT_SERVICE_NAME = os.getenv(
    "CLOUD_RUN_SERVICE",
    "gc-ahmed-service"
)

LAB_URL = (
    "https://www.cloudskillsboost.google/"
    "focuses/20774?parent=catalog"
)


# ============================================================
# Cloud Run health server
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(
            b"GC.AHMED Run Bot is running"
        )

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        return


def start_health_server():
    server = ThreadingHTTPServer(
        ("0.0.0.0", PORT),
        HealthHandler
    )

    print(
        f"Health server listening on 0.0.0.0:{PORT}"
    )

    server.serve_forever()


# ============================================================
# Helpers
# ============================================================

def valid_project_id(project_id: str) -> bool:
    """
    Google Cloud project IDs normally contain:
    lowercase letters, numbers and hyphens.
    """

    return bool(
        re.fullmatch(
            r"[a-z][a-z0-9-]{4,28}[a-z0-9]",
            project_id
        )
    )


def valid_service_name(name: str) -> bool:
    return bool(
        re.fullmatch(
            r"[a-z0-9]([-a-z0-9]*[a-z0-9])?",
            name
        )
    )


# ============================================================
# /start
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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
        "📌 أرسل رابط Google Skills Boost.\n\n"
        "ثم أرسل Project ID الخاص بالمشروع "
        "إذا لم يكن معروفًا للبوت.\n\n"
        "⏱ مدة الـLab: 4:30 ساعات\n\n"
        "Welcome my friends, this is a "
        "GoogleCloud codes generator"
    )

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
# /help
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = (
        "🆘 طريقة الاستخدام\n\n"
        "1️⃣ شغّل Google Skills Boost.\n"
        "2️⃣ أرسل رابط الـLab.\n"
        "3️⃣ أرسل Project ID.\n"
        "4️⃣ سيبدأ البوت إنشاء خدمة Cloud Run.\n"
        "5️⃣ عند النجاح سيُرسل رابط الخدمة.\n\n"
        "📌 الأوامر:\n"
        "/start — بدء الاستخدام\n"
        "/help — المساعدة\n"
        "/status — حالة البوت"
    )

    await update.message.reply_text(text)


# ============================================================
# /status
# ============================================================

async def status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "📊 حالة الخدمة\n\n"
        "🟢 Telegram Bot: يعمل\n"
        "☁️ Cloud Run API: جاهز للاستخدام\n"
        f"🌍 Region: {REGION}\n"
        f"🐳 Image: {DEPLOY_IMAGE}"
    )


# ============================================================
# Deploy Cloud Run
# ============================================================

def deploy_cloud_run(
    project_id: str,
    service_name: str
):
    """
    Creates a real Cloud Run service using
    the Cloud Run v2 Python client.
    """

    client = run_v2.ServicesClient()

    parent = (
        f"projects/{project_id}"
        f"/locations/{REGION}"
    )

    service = run_v2.Service(
        name=(
            f"{parent}/services/"
            f"{service_name}"
        ),

        ingress=run_v2.IngressTraffic.INGRESS_TRAFFIC_ALL,

        template=run_v2.RevisionTemplate(
            containers=[
                run_v2.Container(
                    image=DEPLOY_IMAGE
                )
            ]
        )
    )

    request = run_v2.CreateServiceRequest(
        parent=parent,
        service=service,
        service_id=service_name
    )

    operation = client.create_service(
        request=request
    )

    print(
        f"Creating Cloud Run service: "
        f"{service_name}"
    )

    result = operation.result(
        timeout=1200
    )

    return result.uri


# ============================================================
# Receive messages
# ============================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    message = update.message.text.strip()

    # --------------------------------------------------------
    # Step 1: Google Skills URL
    # --------------------------------------------------------

    if (
        "cloudskillsboost.google" in message
        or "skillsboost.google" in message
    ):

        context.user_data["lab_url"] = message
        context.user_data["waiting_project"] = True

        await update.message.reply_text(
            "✅ تم استلام رابط الـLab.\n\n"
            "🔎 جاري تجهيز الطلب...\n\n"
            "📌 الآن أرسل Project ID الخاص بالمشروع.\n\n"
            "مثال:\n"
            "qwiklabs-gcp-01-xxxxxxxxxxxx"
        )

        return

    # --------------------------------------------------------
    # Step 2: Project ID
    # --------------------------------------------------------

    if context.user_data.get("waiting_project"):

        project_id = message

        if not valid_project_id(project_id):

            await update.message.reply_text(
                "❌ Project ID غير صحيح.\n\n"
                "أرسله بهذا الشكل:\n"
                "qwiklabs-gcp-01-xxxxxxxxxxxx"
            )

            return

        context.user_data["project_id"] = project_id
        context.user_data["waiting_project"] = False

        await update.message.reply_text(
            "✅ تم استلام Project ID.\n\n"
            "🔎 جاري فحص المشروع..."
        )

        await asyncio.sleep(1)

        await update.message.reply_text(
            "☁️ جاري الاتصال بـ Cloud Run API..."
        )

        await asyncio.sleep(1)

        service_name = (
            f"{DEFAULT_SERVICE_NAME}-"
            f"{update.effective_user.id}"
        )

        # Cloud Run service names have length limits
        service_name = service_name[:49]

        await update.message.reply_text(
            "🚀 جاري إنشاء خدمة Cloud Run...\n\n"
            f"📦 Service: {service_name}\n"
            f"🌍 Region: {REGION}"
        )

        try:

            # Run blocking Google API operation
            # outside Telegram event loop
            url = await asyncio.to_thread(
                deploy_cloud_run,
                project_id,
                service_name
            )

            await update.message.reply_text(
                "🎉 تم إنشاء خدمة Cloud Run بنجاح!\n\n"
                f"☁️ المشروع:\n{project_id}\n\n"
                f"📦 الخدمة:\n{service_name}\n\n"
                f"🔗 رابط الخدمة:\n{url}"
            )

        except AlreadyExists:

            await update.message.reply_text(
                "⚠️ الخدمة موجودة مسبقًا.\n\n"
                "غيّر اسم الخدمة أو أرسل الطلب مرة أخرى."
            )

        except GoogleAPICallError as e:

            await update.message.reply_text(
                "❌ حدث خطأ من Google Cloud.\n\n"
                f"التفاصيل:\n{str(e)[:1500]}"
            )

        except Exception as e:

            await update.message.reply_text(
                "❌ فشل إنشاء Cloud Run.\n\n"
                f"الخطأ:\n{str(e)[:1500]}"
            )

        return

    # --------------------------------------------------------
    # Unknown message
    # --------------------------------------------------------

    await update.message.reply_text(
        "📌 أرسل رابط Google Skills Boost أولاً.\n\n"
        "استخدم /start للبدء."
    )


# ============================================================
# Buttons
# ============================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    if query.data == "status":

        await query.message.reply_text(
            "📊 حالة البوت\n\n"
            "🟢 Telegram: يعمل\n"
            "☁️ Cloud Run API: متاح"
        )


# ============================================================
# Main
# ============================================================

def main():

    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is not set"
        )

    # Cloud Run health server
    health_thread = threading.Thread(
        target=start_health_server,
        daemon=True
    )

    health_thread.start()

    # Telegram application
    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    app.add_handler(
        CommandHandler(
            "status",
            status_command
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    print(
        "GC.AHMED Run Bot started."
    )

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()