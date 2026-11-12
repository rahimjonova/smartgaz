from html import escape

from app.bot.texts import BTN_ORDER, STATUS_LABELS
from app.core.time import fmt_date, fmt_dt
from app.models import User
from app.schemas.order import QueueStatusOut
from app.schemas.tracking import DriverLocationOut


def format_profile(user: User) -> str:
    card = escape(user.lpg_card_id) if user.lpg_card_id else "—"
    return (
        "👤 <b>Profilingiz</b>\n\n"
        f"Ism-familiya: <b>{escape(user.full_name)}</b>\n"
        f"Telefon: {escape(user.phone_number)}\n"
        f"Manzil: {escape(user.region)}, {escape(user.district)}, "
        f"{escape(user.mahalla)} MFY, {escape(user.street)}, {escape(user.house_number)}-uy\n"
        f"Gaz ID-karta: {card}"
    )


def format_registration_summary(data: dict[str, str | None]) -> str:
    card = data.get("lpg_card_id") or "—"
    return (
        "Ma'lumotlaringizni tekshiring:\n\n"
        f"👤 {escape(str(data.get('full_name')))}\n"
        f"📱 {escape(str(data.get('phone_number')))}\n"
        f"📍 {escape(str(data.get('region')))}, {escape(str(data.get('district')))}\n"
        f"🏘 {escape(str(data.get('mahalla')))} MFY\n"
        f"🏠 {escape(str(data.get('street')))}, {escape(str(data.get('house_number')))}-uy\n"
        f"💳 Gaz ID-karta: {escape(card)}"
    )


def format_queue_status(status: QueueStatusOut) -> str:
    if not status.has_active_order or status.order is None:
        lines = ["📋 Sizda faol navbat yo'q."]
        if status.last_delivered_at:
            lines.append(f"Oxirgi balon olingan: {fmt_dt(status.last_delivered_at)}")
        if status.next_order_allowed_at:
            lines.append(
                f"Keyingi navbatga {fmt_dt(status.next_order_allowed_at)} dan keyin turish mumkin."
            )
        else:
            lines.append(f"Navbat olish uchun «{BTN_ORDER}» tugmasini bosing.")
        lines.append(f"\nMahallangizda hozir navbatda: {status.total_in_queue} ta xonadon")
        return "\n".join(lines)

    order = status.order
    estimated = fmt_date(status.estimated_delivery_date) if status.estimated_delivery_date else "—"
    return (
        "📋 <b>Navbat holati</b>\n\n"
        f"Buyurtma: #{order.id}\n"
        f"Navbat raqami: <b>{order.queue_number}</b>\n"
        f"Mahallangizdagi o'rningiz: <b>{status.position}</b> / {status.total_in_queue}\n"
        f"Holat: {STATUS_LABELS[order.status]}\n"
        f"Taxminiy yetkazish sanasi: <b>{estimated}</b>\n"
        f"Navbatga turilgan: {fmt_dt(order.requested_at)}"
    )


def format_driver_location(location: DriverLocationOut) -> str:
    state = "🟢 onlayn" if location.is_online else "🔴 aloqa yo'q (oxirgi ma'lum joy)"
    updated = fmt_dt(location.updated_at) if location.updated_at else "—"
    text = (
        "🚚 <b>Gaz mashinasi</b>\n\n"
        f"Haydovchi: {escape(location.full_name)}\n"
        f"Avtomobil: {escape(location.car_number)}\n"
        f"Holat: {state}\n"
        f"Yangilangan: {updated}"
    )
    if location.map_url:
        text += f'\n\n<a href="{escape(location.map_url)}">🗺 Xaritada ochish</a>'
    return text
