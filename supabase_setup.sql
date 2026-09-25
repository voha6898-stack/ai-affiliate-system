-- affiliate-ai click tracking — chạy 1 lần trong Supabase SQL Editor
-- (project đang dùng chung với ha-tinh-website, bảng này độc lập, không đụng bảng khác)

create table if not exists affiliate_clicks (
  id bigint generated always as identity primary key,
  article_id integer not null,
  niche text default '',
  dest_url text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_affiliate_clicks_article on affiliate_clicks(article_id);
create index if not exists idx_affiliate_clicks_created on affiliate_clicks(created_at);

alter table affiliate_clicks enable row level security;

-- Khách vãng lai (anon key, chạy trong trình duyệt) chỉ được INSERT — không đọc/sửa/xoá được.
drop policy if exists "anon can insert clicks" on affiliate_clicks;
create policy "anon can insert clicks"
  on affiliate_clicks for insert
  to anon
  with check (true);

-- Không tạo policy SELECT cho anon => chỉ service_role (dashboard.py, server-side) đọc được số liệu.
