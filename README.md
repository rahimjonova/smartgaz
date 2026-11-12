# SmartGaz — maishiy gaz ballonlari uchun elektron navbat platformasi

Qishloq hududlarida suyultirilgan gaz ballonlarini adolatli va shaffof taqsimlash uchun platforma.
Xonadon telefondan navbatga turadi, dispecher marshrutni navbat tartibida tuzadi, haydovchi
balonni topshirganini qayd etadi, mashina xaritada ko'rinadi.

## Rollar

| Rol | Imkoniyatlar |
|---|---|
| Fuqaro | Navbatga turish, mahalladagi o'rin va taxminiy sana, mashinani xaritada kuzatish, tarix, murojaat |
| Haydovchi | Bugungi marshrut (FIFO), GPS, ballon topshirish (kg, to'lov), "uyda yo'q", marshrutni yakunlash |
| Dispecher | Ko'rsatkichlar, marshrut yaratish, jonli xarita, murojaatlar, shubhali holatlar, hisobot |
| MFY vakili | Xonadonlarni tasdiqlash, bir uyda bir necha oila, ehtiyojmand oilalar |
| Administrator | Sozlamalar (20 kun, kunlik reja, narx), haydovchilar, mahallalar, audit jurnali |

Sinov akkauntlari (parol hammasida `demo123`): `jasur@mail.uz` (fuqaro),
`haydovchi2@smartgaz.uz` (haydovchi), `dispecher@smartgaz.uz`, `mfy@smartgaz.uz`, `admin@smartgaz.uz`.

## Asosiy qoidalar
- Bir xonadon 20 kunda bir marta ballon oladi; faol navbat bo'lsa, yangi navbat berilmaydi.
- Navbat har bir mahalla uchun alohida, "birinchi kelgan — birinchi oladi" (FIFO) tartibida.
- Marshrut yaratilganda navbatdagi xonadonlar avtomatik band qilinadi; topshirilmaganlar o'rnini yo'qotmaydi.

## Papkalar

```
index.html            — platforma (barcha rollar, bitta fayl)
supabase/schema.sql   — Supabase ma'lumotlar bazasi (jadvallar, RLS, antifrod funksiyalari)
backend/              — FastAPI + PostgreSQL + Aiogram (Telegram-bot) MVP
docs/                 — texnik topshiriq
```

Hozirgi `index.html` sinov rejimida ishlaydi: ma'lumotlar foydalanuvchi brauzerida saqlanadi.
Bir nechta foydalanuvchi umumiy bazada ishlashi uchun `backend/` dagi API ulanadi
(`backend/README.md` ga qarang).

---

## GitHub va Vercel'ga joylash (yo'riqnoma)

### 1. GitHub'da repozitoriy ochish
1. github.com saytiga kiring → o'ng yuqorida **+** → **New repository**.
2. Repository name: `smartgaz`. **Public** ni tanlang. Boshqa belgilarni qo'ymang.
3. **Create repository** tugmasini bosing.

### 2. Fayllarni yuklash
1. Ochilgan sahifada **uploading an existing file** havolasini bosing
   (yoki keyinchalik: **Add file → Upload files**).
2. Kompyuteringizdagi `smartgaz` papkasini oching, ichidagi **hamma narsani belgilang**
   (`index.html`, `README.md`, `supabase`, `backend`, `docs` va hokazo) va brauzer oynasiga sudrab tashlang.
   Papkaning o'zini emas, uning **ichidagilarini** tashlang — shunda `index.html` repozitoriyning ildizida bo'ladi.
3. Pastda commit xabari: `SmartGaz platformasi` → **Commit changes**.
4. Tekshiring: repozitoriy bosh sahifasida `index.html` ro'yxatda ko'rinishi kerak.

> Nuqta bilan boshlanadigan fayllar (`.gitignore`, `.vercelignore`, `backend/.env.example`)
> Mac/Windows'da yashirin bo'lishi mumkin. Ular ko'rinmasa ham sayt ishlaydi.
> Mac'da yashirin fayllarni ko'rsatish: Finder'da `Cmd + Shift + .`

### 3. Vercel'ga joylash
1. vercel.com → **Sign Up / Log In** → **Continue with GitHub**.
2. **Add New… → Project** → ro'yxatdan `smartgaz` repozitoriyni topib **Import** bosing.
3. Sozlamalar:
   - Project Name: `smartgaz`
   - Framework Preset: **Other**
   - Root Directory: `./` (o'zgartirmang), Build Command bo'sh qoladi
4. **Deploy** → 20–40 soniyadan keyin "Congratulations!" chiqadi.
5. Sayt manzili: `https://smartgaz.vercel.app` (nom band bo'lsa, Vercel `smartgaz-xxxx.vercel.app` beradi;
   **Settings → Domains** bo'limida `smartgaz-uz.vercel.app` kabi boshqa nom qo'yishingiz mumkin).

### 4. Yangilash
Faylni o'zgartirsangiz, GitHub'da **Add file → Upload files** orqali yangisini yuklang —
Vercel saytni avtomatik qayta joylaydi (1 daqiqa ichida).
