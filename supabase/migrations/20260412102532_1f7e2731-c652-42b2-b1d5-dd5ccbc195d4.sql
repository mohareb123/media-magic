
-- Bot state singleton
CREATE TABLE public.telegram_bot_state (
  id int PRIMARY KEY CHECK (id = 1),
  update_offset bigint NOT NULL DEFAULT 0,
  updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO public.telegram_bot_state (id, update_offset) VALUES (1, 0);
ALTER TABLE public.telegram_bot_state ENABLE ROW LEVEL SECURITY;

-- Telegram users
CREATE TABLE public.telegram_users (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  telegram_id bigint NOT NULL UNIQUE,
  username text,
  first_name text,
  last_name text,
  language_code text,
  is_premium boolean DEFAULT false,
  is_blocked boolean DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.telegram_users ENABLE ROW LEVEL SECURITY;

-- Telegram messages
CREATE TABLE public.telegram_messages (
  update_id bigint PRIMARY KEY,
  chat_id bigint NOT NULL,
  telegram_user_id bigint,
  text text,
  message_type text DEFAULT 'text',
  raw_update jsonb NOT NULL,
  processed boolean DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_telegram_messages_chat_id ON public.telegram_messages (chat_id);
CREATE INDEX idx_telegram_messages_processed ON public.telegram_messages (processed);
ALTER TABLE public.telegram_messages ENABLE ROW LEVEL SECURITY;

-- Bot downloads
CREATE TABLE public.bot_downloads (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  telegram_user_id bigint NOT NULL,
  chat_id bigint NOT NULL,
  url text NOT NULL,
  platform text,
  media_type text,
  quality text,
  status text DEFAULT 'pending',
  error_message text,
  metadata jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_bot_downloads_user ON public.bot_downloads (telegram_user_id);
CREATE INDEX idx_bot_downloads_status ON public.bot_downloads (status);
ALTER TABLE public.bot_downloads ENABLE ROW LEVEL SECURITY;

-- Update timestamp function
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public;

CREATE TRIGGER update_telegram_users_updated_at
  BEFORE UPDATE ON public.telegram_users
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_bot_downloads_updated_at
  BEFORE UPDATE ON public.bot_downloads
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
