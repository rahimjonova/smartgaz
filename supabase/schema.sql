-- =====================================================================
-- SmartGaz — Supabase ma'lumotlar bazasi sxemasi
-- Supabase → SQL Editor → New query → shu faylni to'liq joylab "Run" bosing.
-- =====================================================================

-- 1. Profillar (auth.users bilan 1:1)
create table if not exists public.profiles (
  id            uuid primary key references auth.users(id) on delete cascade,
  full_name     text not null check (char_length(full_name) between 3 and 150),
  phone         text not null check (phone ~ '^\+998[0-9]{9}$'),
  region        text not null,
  district      text not null,
  mahalla       text not null,
  street        text not null,
  house_number  text not null,
  -- Navbat va antifrod shu kalitlar bo'yicha ishlaydi
  mahalla_key   text generated always as (
                  lower(trim(region)) || '|' || lower(trim(district)) || '|' || lower(trim(mahalla))
                ) stored,
  household_key text generated always as (
                  lower(trim(region)) || '|' || lower(trim(district)) || '|' || lower(trim(mahalla))
                  || '|' || lower(trim(street)) || '|' || lower(replace(house_number, ' ', ''))
                ) stored,
  role          text not null default 'user' check (role in ('user', 'admin')),
  created_at    timestamptz not null default now()
);
create index if not exists profiles_mahalla_key_idx on public.profiles (mahalla_key);
create index if not exists profiles_household_key_idx on public.profiles (household_key);

-- 2. Buyurtmalar (navbat)
create table if not exists public.orders (
  id            bigint generated always as identity primary key,
  user_id       uuid not null references public.profiles(id) on delete cascade,
  status        text not null default 'PENDING'
                check (status in ('PENDING', 'ON_WAY', 'DELIVERED', 'CANCELLED')),
  queue_number  integer not null check (queue_number > 0),
  price         numeric(12, 2) not null default 65000,
  requested_at  timestamptz not null default now(),
  delivered_at  timestamptz
);
create index if not exists orders_user_id_idx on public.orders (user_id);
create index if not exists orders_status_idx on public.orders (status, requested_at);
-- Bitta foydalanuvchida faqat bitta faol navbat
create unique index if not exists orders_one_active_per_user
  on public.orders (user_id) where status in ('PENDING', 'ON_WAY');

-- 3. Yordamchi: joriy foydalanuvchi adminmi?
create or replace function public.is_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles where id = auth.uid() and role = 'admin');
$$;

-- 4. Row Level Security (har kim faqat o'z ma'lumotini ko'radi, admin — hammasini)
alter table public.profiles enable row level security;
alter table public.orders   enable row level security;

drop policy if exists profiles_select on public.profiles;
create policy profiles_select on public.profiles for select to authenticated
  using (id = auth.uid() or public.is_admin());

drop policy if exists profiles_insert on public.profiles;
create policy profiles_insert on public.profiles for insert to authenticated
  with check (id = auth.uid() and role = 'user');

drop policy if exists profiles_update on public.profiles;
create policy profiles_update on public.profiles for update to authenticated
  using (id = auth.uid()) with check (id = auth.uid());

-- Foydalanuvchi o'z rolini (role) o'zgartira olmasin
revoke update on public.profiles from anon, authenticated;
grant update (full_name, phone, region, district, mahalla, street, house_number)
  on public.profiles to authenticated;

drop policy if exists orders_select on public.orders;
create policy orders_select on public.orders for select to authenticated
  using (user_id = auth.uid() or public.is_admin());

-- Buyurtmani faqat quyidagi funksiyalar orqali yaratish/o'zgartirish mumkin
revoke insert, update, delete on public.orders from anon, authenticated;

-- 5. Navbatga turish (antifrod: faol navbat yoki 20 kun ichida olingan bo'lsa — rad)
create or replace function public.create_order()
returns public.orders language plpgsql security definer set search_path = public as $$
declare
  p public.profiles;
  new_order public.orders;
  last_at timestamptz;
begin
  select * into p from public.profiles where id = auth.uid();
  if not found then
    raise exception 'Avval profilingizni to''ldiring';
  end if;

  -- Bir mahalla bo'yicha parallel so'rovlar ketma-ket bajarilsin
  perform pg_advisory_xact_lock(hashtext(p.mahalla_key));

  if exists (
    select 1 from public.orders o join public.profiles pr on pr.id = o.user_id
    where pr.household_key = p.household_key and o.status in ('PENDING', 'ON_WAY')
  ) then
    raise exception 'Siz yaqinda gaz olgansiz yoki navbatdasiz: xonadoningiz allaqachon navbatda.';
  end if;

  select max(o.delivered_at) into last_at
  from public.orders o join public.profiles pr on pr.id = o.user_id
  where pr.household_key = p.household_key and o.status = 'DELIVERED';

  if last_at is not null and last_at > now() - interval '20 days' then
    raise exception 'Siz yaqinda gaz olgansiz yoki navbatdasiz. Keyingi navbat % dan ochiladi.',
      to_char((last_at + interval '20 days') at time zone 'Asia/Tashkent', 'DD.MM.YYYY');
  end if;

  insert into public.orders (user_id, queue_number)
  values (
    p.id,
    (select coalesce(max(o.queue_number), 0) + 1
       from public.orders o join public.profiles pr on pr.id = o.user_id
      where pr.mahalla_key = p.mahalla_key)
  )
  returning * into new_order;
  return new_order;
end $$;

-- 6. Navbat holati: mahalladagi o'rin, jami navbat, taxminiy sana
create or replace function public.queue_status()
returns json language plpgsql stable security definer set search_path = public as $$
declare
  p public.profiles;
  cur public.orders;
  pos integer;
  total integer;
  last_at timestamptz;
  today date := (now() at time zone 'Asia/Tashkent')::date;
begin
  select * into p from public.profiles where id = auth.uid();
  if not found then
    return json_build_object('has_profile', false);
  end if;

  select count(*) into total
  from public.orders o join public.profiles pr on pr.id = o.user_id
  where pr.mahalla_key = p.mahalla_key and o.status in ('PENDING', 'ON_WAY');

  select max(o.delivered_at) into last_at
  from public.orders o join public.profiles pr on pr.id = o.user_id
  where pr.household_key = p.household_key and o.status = 'DELIVERED';

  select o.* into cur
  from public.orders o join public.profiles pr on pr.id = o.user_id
  where pr.household_key = p.household_key and o.status in ('PENDING', 'ON_WAY')
  order by o.queue_number limit 1;

  if not found then
    return json_build_object(
      'has_profile', true, 'has_active', false, 'total', total,
      'last_delivered_at', last_at,
      'next_allowed_at', case when last_at > now() - interval '20 days'
                              then last_at + interval '20 days' end
    );
  end if;

  select count(*) + 1 into pos
  from public.orders o join public.profiles pr on pr.id = o.user_id
  where pr.mahalla_key = p.mahalla_key and o.status in ('PENDING', 'ON_WAY')
    and o.queue_number < cur.queue_number;

  return json_build_object(
    'has_profile', true, 'has_active', true, 'order', row_to_json(cur),
    'position', pos, 'total', total, 'last_delivered_at', last_at,
    -- Kuniga mahallaga 20 ta balon yetkaziladi deb hisoblaymiz
    'estimated_date', case when cur.status = 'ON_WAY' then today
                           else today + 1 + (pos - 1) / 20 end
  );
end $$;

-- 7. Navbatni bekor qilish (faqat mashina yo'lga chiqmagan bo'lsa)
create or replace function public.cancel_order()
returns public.orders language plpgsql security definer set search_path = public as $$
declare o public.orders;
begin
  update public.orders set status = 'CANCELLED'
  where user_id = auth.uid() and status = 'PENDING'
  returning * into o;
  if not found then
    raise exception 'Bekor qilinadigan navbat yo''q (yoki mashina yo''lga chiqqan).';
  end if;
  return o;
end $$;

-- 8. Dispecher: mashina yo'lga chiqdi / balon topshirildi
create or replace function public.set_on_way(p_order_id bigint)
returns public.orders language plpgsql security definer set search_path = public as $$
declare o public.orders;
begin
  if not public.is_admin() then raise exception 'Ruxsat yo''q'; end if;
  update public.orders set status = 'ON_WAY'
  where id = p_order_id and status = 'PENDING' returning * into o;
  if not found then raise exception 'Buyurtma topilmadi yoki holati mos emas'; end if;
  return o;
end $$;

create or replace function public.deliver_order(p_order_id bigint)
returns public.orders language plpgsql security definer set search_path = public as $$
declare o public.orders;
begin
  if not public.is_admin() then raise exception 'Ruxsat yo''q'; end if;
  update public.orders set status = 'DELIVERED', delivered_at = now()
  where id = p_order_id and status in ('PENDING', 'ON_WAY') returning * into o;
  if not found then raise exception 'Buyurtma topilmadi yoki allaqachon topshirilgan'; end if;
  return o;
end $$;

-- 9. Dispecher statistikasi: mahallalar kesimida
create or replace function public.mahalla_stats()
returns table (
  region text, district text, mahalla text,
  households bigint, waiting bigint, on_way bigint,
  delivered_total bigint, delivered_today bigint
) language plpgsql stable security definer set search_path = public as $$
#variable_conflict use_column
begin
  if not public.is_admin() then raise exception 'Ruxsat yo''q'; end if;
  return query
  select min(p.region), min(p.district), min(p.mahalla),
         count(distinct p.household_key),
         count(o.id) filter (where o.status = 'PENDING'),
         count(o.id) filter (where o.status = 'ON_WAY'),
         count(o.id) filter (where o.status = 'DELIVERED'),
         count(o.id) filter (where o.status = 'DELIVERED'
           and (o.delivered_at at time zone 'Asia/Tashkent')::date
               = (now() at time zone 'Asia/Tashkent')::date)
  from public.profiles p
  left join public.orders o on o.user_id = p.id
  where p.role = 'user'
  group by p.mahalla_key
  order by 1, 2, 3;
end $$;

-- 10. Funksiyalarni faqat tizimga kirgan foydalanuvchilar chaqira olsin
revoke execute on function public.create_order(), public.queue_status(), public.cancel_order(),
  public.set_on_way(bigint), public.deliver_order(bigint), public.mahalla_stats()
  from public, anon;
grant execute on function public.create_order(), public.queue_status(), public.cancel_order(),
  public.set_on_way(bigint), public.deliver_order(bigint), public.mahalla_stats(), public.is_admin()
  to authenticated;

-- 11. Dispecher (admin) tayinlash — o'z emailingizni yozing:
-- update public.profiles set role = 'admin'
-- where id = (select id from auth.users where email = 'admin@example.com');
