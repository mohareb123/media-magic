
-- These tables are only accessed via service_role in edge functions
-- Adding explicit deny-all policies for anon/authenticated roles

CREATE POLICY "No public access to bot state"
  ON public.telegram_bot_state FOR ALL
  USING (false);

CREATE POLICY "No public access to telegram users"
  ON public.telegram_users FOR ALL
  USING (false);

CREATE POLICY "No public access to telegram messages"
  ON public.telegram_messages FOR ALL
  USING (false);

CREATE POLICY "No public access to bot downloads"
  ON public.bot_downloads FOR ALL
  USING (false);
