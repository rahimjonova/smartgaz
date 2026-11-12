# SmartGaz — MVP

Qishloq hududlarida maishiy gaz balonlari (suyultirilgan gaz) ta'minotini **shaffof navbat**,
**antifrod** va **mashina GPS monitoringi** orqali tartibga soluvchi tizim.

- **Aholi** — Telegram-bot orqali ro'yxatdan o'tadi, navbat oladi, navbat holati va mashina joylashuvini ko'radi.
- **Haydovchi** — FastAPI orqali bugungi marshrutini (FIFO) oladi, har 30 soniyada GPS yuboradi, balon topshirilganini qayd etadi.
- **Admin / dispecher** — haydovchi va marshrutlarni boshqaradi, mahalla/tuman kesimida statistikani ko'radi.

## Bulutli (SaaS) xizmatlar bilan bog'liqligi

| Ehtiyoj | Bulutli xizmat |
|---|---|
| Ma'lumotlar bazasi | **Supabase** (boshqariladigan PostgreSQL) — `.env` da `DATABASE_URL` ni ko'rsatish kifoya |
| Foydalanuvchi interfeysi | **Telegram** platformasi (ilova o'rnatish shart emas) |
| Backend va botni joylash | Render / Railway / Fly.io (Docker image tayyor) |
| Xarita | Google Maps havolasi (`map_url`) |

> Supabase uchun to'g'ridan-to'g'ri ulanish yoki **session pooler** (port 5432) dan foydalaning,
> URL oxiriga `?ssl=require` qo'shing.

## Arxitektura (modulli monolit)

```
app/
├── core/       # config, enumlar, vaqt, xatoliklar, normallashtirish
├── db/         # Base (naming convention), async engine/sessiya
├── models/     # User, Driver, DriverLocation, Order, DeliveryRoute
├── schemas/    # Pydantic v2 DTO'lar
├── services/   # biznes-mantiq (API va bot uchun umumiy)
├── api/        # FastAPI: deps (API-kalit rollari) + v1 endpointlar
└── bot/        # Aiogram 3: FSM, klaviaturalar, handlerlar, DB middleware
alembic/        # async migratsiyalar (0001_initial)
```

API ham, bot ham **bir xil servis qatlamidan** foydalanadi — biznes qoidalari bir joyda.

## Ishga tushirish

### Docker bilan (eng oson)

```bash
cp .env.example .env          # BOT_TOKEN va API kalitlarini to'ldiring
docker compose up --build
```

API: http://localhost:8000/docs (Swagger).

### Lokal

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload       # 1-terminal: API
python -m app.bot.main              # 2-terminal: Telegram-bot
```

## Biznes qoidalari

1. **Xonadon** = viloyat + tuman + mahalla + ko'cha + uy raqami (normallashtirilgan: `G'ishtli`, `Gʻishtli`, `G’ishtli` bir xil hisoblanadi).
2. **Antifrod:** xonadonda faol navbat bo'lsa yoki oxirgi **20 kun** ichida balon olingan bo'lsa — yangi navbat berilmaydi:
   *«Siz yaqinda gaz olgansiz yoki navbatdasiz»*. Bu qoida bitta xonadondagi barcha Telegram akkauntlarga tegishli.
3. **Poyga holatlari:** bir mahalla bo'yicha navbat yaratish va marshrutga band qilish PostgreSQL `pg_advisory_xact_lock` bilan ketma-ket bajariladi; qo'shimcha ravishda `uq_orders_user_active` partial unique index bor.
4. **FIFO:** navbat raqami (`queue_number`) har mahalla uchun alohida o'sadi. Marshrut yaratilganda eng oldingi `PENDING` buyurtmalar band qilinadi.
5. **Taxminiy sana:** marshrutga kiritilgan bo'lsa — marshrut sanasi; aks holda `DAILY_CAPACITY_PER_MAHALLA` (kunlik quvvat) bo'yicha hisoblanadi.

### Buyurtma holatlari

```
PENDING ──(admin marshrut yaratadi)──▶ APPROVED ──(haydovchi marshrutni boshlaydi)──▶ ON_WAY ──▶ DELIVERED
   │                                       │                                            │
   └──────── CANCELLED (foydalanuvchi) ◀───┘        marshrut yakunlansa, topshirilmaganlar ─┘──▶ PENDING
                                                     (navbatdagi o'rni saqlanadi)
```

## API endpointlari

Barcha so'rovlarda `X-API-Key` sarlavhasi kerak. Admin kaliti hamma joyga kiradi.

| Metod | Yo'l | Rol | Vazifa |
|---|---|---|---|
| POST | `/api/v1/orders/create` | service | Navbat olish |
| GET | `/api/v1/orders/queue-status/{user_id}` | service | Navbatdagi o'rin, taxminiy sana |
| POST | `/api/v1/orders/cancel` | service | Navbatni bekor qilish |
| POST | `/api/v1/orders/{order_id}/complete` | driver | Balon topshirildi (ID bo'yicha) |
| POST | `/api/v1/orders/complete-by-address` | driver | Balon topshirildi (manzil bo'yicha) |
| POST | `/api/v1/tracking/update-location` | driver | GPS koordinata (har 30 s) |
| GET | `/api/v1/tracking/driver/{driver_id}` | service, driver | Haydovchi joylashuvi |
| GET | `/api/v1/tracking/user/{user_id}` | service | Foydalanuvchiga kelayotgan mashina |
| GET | `/api/v1/routes/today/{driver_id}` | driver | Bugungi marshrut va xonadonlar (FIFO) |
| POST | `/api/v1/routes/{route_id}/start` | driver | Marshrutni boshlash (aholiga xabar ketadi) |
| POST | `/api/v1/routes/{route_id}/finish` | driver | Marshrutni yakunlash |
| POST/GET/PATCH | `/api/v1/admin/drivers` | admin | Haydovchilar |
| POST | `/api/v1/admin/routes` | admin | Marshrut yaratish |
| GET | `/api/v1/admin/stats?region=&district=` | admin | Statistika |
| POST | `/api/v1/users/register` | service | Ro'yxatdan o'tish (botdan tashqari mijozlar) |

### Demo ssenariy (curl)

```bash
A="X-API-Key: change-me-admin-key-0000"
# 1) Haydovchi qo'shish
curl -X POST localhost:8000/api/v1/admin/drivers -H "$A" -H 'Content-Type: application/json' \
  -d '{"full_name":"Karimov Anvar","phone_number":"+998901112233","car_number":"40 A 123 BC","capacity":60}'

# 2) Aholi botda ro'yxatdan o'tib "🔥 Gazga navbatga turish" ni bosadi

# 3) Marshrut yaratish (mahalladagi navbat FIFO bo'yicha band qilinadi)
curl -X POST localhost:8000/api/v1/admin/routes -H "$A" -H 'Content-Type: application/json' \
  -d '{"driver_id":1,"region":"Farg'"'"'ona viloyati","district":"Oltiariq","mahalla_name":"Navbahor","allocated_cylinders":40}'

# 4) Haydovchi: marshrutni boshlash, GPS, topshirish
D="X-API-Key: change-me-driver-key-000"
curl -X POST localhost:8000/api/v1/routes/1/start -H "$D" -H 'Content-Type: application/json' -d '{"driver_id":1}'
curl -X POST localhost:8000/api/v1/tracking/update-location -H "$D" -H 'Content-Type: application/json' \
  -d '{"driver_id":1,"lat":40.3891,"lon":71.4792}'
curl -X POST localhost:8000/api/v1/orders/1/complete -H "$D" -H 'Content-Type: application/json' \
  -d '{"driver_id":1,"payment_type":"CASH"}'

# 5) Statistika
curl localhost:8000/api/v1/admin/stats -H "$A"
```

## Productionga o'tishda

- Haydovchilar uchun umumiy `DRIVER_API_KEY` o'rniga har bir haydovchiga alohida JWT.
- Bot FSM uchun `MemoryStorage` o'rniga `RedisStorage`.
- `driver_locations` jadvali tez o'sadi — eski nuqtalarni davriy tozalash yoki partitsiyalash.
- Onlayn to'lov (Click/Payme) integratsiyasi — `payment_type=ONLINE` uchun.
