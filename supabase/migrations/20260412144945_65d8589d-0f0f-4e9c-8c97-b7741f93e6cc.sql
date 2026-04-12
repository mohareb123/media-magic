
CREATE TABLE public.bot_settings (
  id integer PRIMARY KEY CHECK (id = 1),
  forced_channel text,
  forced_channel_name text,
  is_forced_subscription_enabled boolean NOT NULL DEFAULT false,
  daily_download_limit integer NOT NULL DEFAULT 10,
  admin_password text NOT NULL DEFAULT 'admin123',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.bot_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "No public access to bot settings"
  ON public.bot_settings FOR ALL
  USING (false);

INSERT INTO public.bot_settings (id) VALUES (1);

CREATE TRIGGER update_bot_settings_updated_at
  BEFORE UPDATE ON public.bot_settings
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();
