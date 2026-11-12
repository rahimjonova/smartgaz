from app.core.enums import OrderStatus

BTN_ORDER = "🔥 Gazga navbatga turish"
BTN_STATUS = "📋 Navbat holati"
BTN_LOCATION = "🚚 Mashina lokatsiyasi"
BTN_PROFILE = "👤 Profilim"
BTN_CANCEL_ORDER = "❌ Navbatni bekor qilish"
BTN_SEND_CONTACT = "📱 Telefon raqamni yuborish"
BTN_SKIP = "⏭ O'tkazib yuborish"

STATUS_LABELS: dict[OrderStatus, str] = {
    OrderStatus.PENDING: "⏳ Navbatda",
    OrderStatus.APPROVED: "✅ Marshrutga kiritildi",
    OrderStatus.ON_WAY: "🚚 Mashina yo'lda",
    OrderStatus.DELIVERED: "📦 Topshirildi",
    OrderStatus.CANCELLED: "❌ Bekor qilingan",
}

HELP_TEXT = (
    "<b>SmartGaz</b> — maishiy gaz balonlarini shaffof navbat asosida olish xizmati.\n\n"
    f"• {BTN_ORDER} — navbat olish\n"
    f"• {BTN_STATUS} — mahallangizdagi o'rningiz va taxminiy sana\n"
    f"• {BTN_LOCATION} — gaz mashinasi qayerda ekanini ko'rish\n"
    f"• {BTN_CANCEL_ORDER} — navbatdan chiqish\n\n"
    "Qoida: bitta xonadon 20 kunda bir marta navbatga tura oladi.\n"
    "Buyruqlar: /start, /cancel, /help"
)
