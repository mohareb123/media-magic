import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

type TelegramHeaders = Record<string, string>;
type BotSettings = {
  daily_download_limit?: number;
  forced_channel?: string | null;
  forced_channel_name?: string | null;
  is_forced_subscription_enabled?: boolean;
} | null;

type DownloadResult = {
  url: string;
  type: 'video' | 'photo' | 'audio' | 'document';
  quality?: string;
};

declare global {
  var EdgeRuntime:
    | {
        waitUntil?: (promise: Promise<unknown>) => void;
      }
    | undefined;
}

const GATEWAY_URL = 'https://connector-gateway.lovable.dev/telegram';
const MAX_RUNTIME_MS = 25_000;
const LONG_POLL_TIMEOUT_SECONDS = 20;
const DEVELOPER_CHAT_ID = Number(Deno.env.get('DEVELOPER_CHAT_ID') || '0');
const BOT_USERNAME = Deno.env.get('BOT_USERNAME') || 'Sarhny01bot';

Deno.serve(async () => {
  try {
    const startTime = Date.now();
    const LOVABLE_API_KEY = Deno.env.get('LOVABLE_API_KEY');
    const TELEGRAM_API_KEY = Deno.env.get('TELEGRAM_API_KEY');
    const supabaseUrl = Deno.env.get('SUPABASE_URL');
    const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');

    if (!LOVABLE_API_KEY || !TELEGRAM_API_KEY || !supabaseUrl || !serviceRoleKey) {
      return jsonResponse({ error: 'Missing required backend secrets' }, 500);
    }

    const supabase = createClient(supabaseUrl, serviceRoleKey);
    const tgHeaders: TelegramHeaders = {
      Authorization: `Bearer ${LOVABLE_API_KEY}`,
      'X-Connection-Api-Key': TELEGRAM_API_KEY,
      'Content-Type': 'application/json',
    };

    const [settingsResult, stateResult] = await Promise.all([
      supabase.from('bot_settings').select('*').eq('id', 1).single(),
      supabase.from('telegram_bot_state').select('update_offset').eq('id', 1).single(),
    ]);

    if (stateResult.error) {
      return jsonResponse({ error: stateResult.error.message }, 500);
    }

    const settings = settingsResult.data ?? null;
    let currentOffset = Number(stateResult.data?.update_offset ?? 0);
    let processed = 0;

    while (Date.now() - startTime < MAX_RUNTIME_MS) {
      const telegramData = await fetchTelegram(tgHeaders, 'getUpdates', {
        offset: currentOffset,
        timeout: LONG_POLL_TIMEOUT_SECONDS,
        limit: 50,
        allowed_updates: ['message'],
      });

      if (!telegramData.ok) {
        if (telegramData.error_code === 409) {
          return jsonResponse({ ok: true, skipped: 'another poller is active' }, 200);
        }
        return jsonResponse({ error: `Telegram error: ${telegramData.description || 'unknown'}` }, 502);
      }

      const updates = Array.isArray(telegramData.result) ? telegramData.result : [];
      if (updates.length === 0) break;

      for (const update of updates) {
        try {
          if (update?.message) {
            await processIncomingMessage(supabase, tgHeaders, settings, update);
            processed += 1;
          }
        } catch (error) {
          console.error('Failed to process update', update?.update_id, error);
        }
      }

      currentOffset = Math.max(...updates.map((item: any) => Number(item.update_id))) + 1;
      await supabase
        .from('telegram_bot_state')
        .update({ update_offset: currentOffset, updated_at: new Date().toISOString() })
        .eq('id', 1);
    }

    return jsonResponse({ ok: true, processed, finalOffset: currentOffset }, 200);
  } catch (error) {
    console.error('telegram-poll fatal error', error);
    return jsonResponse({ error: 'Internal server error' }, 500);
  }
});

async function processIncomingMessage(
  supabase: any,
  headers: TelegramHeaders,
  settings: BotSettings,
  update: any,
) {
  const msg = update.message;
  const chatId = Number(msg.chat.id);
  const userId = Number(msg.from?.id ?? msg.sender_chat?.id ?? 0);
  const rawText = getMessageText(msg);
  const normalizedText = normalizeCommand(rawText).trim();

  await storeUserAndMessage(supabase, update, msg, rawText);

  if (!shouldHandleMessage(msg, rawText)) return;
  if (!userId) return;

  const { data: userRow } = await supabase
    .from('telegram_users')
    .select('is_blocked')
    .eq('telegram_id', userId)
    .maybeSingle();

  if (userRow?.is_blocked) {
    await sendMessage(headers, chatId, '⛔ تم حظر استخدامك للبوت من قبل الإدارة.');
    return;
  }

  if (settings?.is_forced_subscription_enabled && settings?.forced_channel && userId !== DEVELOPER_CHAT_ID) {
    const isMember = await checkChannelMembership(headers, settings.forced_channel, userId);
    if (!isMember) {
      const channelName = settings.forced_channel_name || settings.forced_channel;
      await sendMessage(
        headers,
        chatId,
        `⚠️ يجب الاشتراك أولاً في ${channelName}\nhttps://t.me/${String(settings.forced_channel).replace('@', '')}`,
      );
      return;
    }
  }

  if (normalizedText === '/start') {
    await sendMessage(
      headers,
      chatId,
      `🎬 أهلاً بك في ABU ALAZ PLATFORM\n\nأرسل رابط فيديو أو صورة أو صوت لأبدأ التحميل.\n\nفي المجموعات: أرسل الرابط مع منشن @${BOT_USERNAME} أو عطّل Privacy Mode من BotFather ليقرأ الروابط مباشرة.`,
    );

    if (DEVELOPER_CHAT_ID && userId !== DEVELOPER_CHAT_ID && msg.chat.type === 'private') {
      const fullName = [msg.from?.first_name, msg.from?.last_name].filter(Boolean).join(' ') || 'بدون اسم';
      const username = msg.from?.username ? `@${msg.from.username}` : 'بدون يوزرنيم';
      await sendMessage(headers, DEVELOPER_CHAT_ID, `🆕 مستخدم جديد\n👤 ${fullName}\n🔗 ${username}\n🆔 ${userId}`);
    }
    return;
  }

  if (normalizedText === '/help') {
    await sendMessage(
      headers,
      chatId,
      `📖 طريقة الاستخدام\n1) أرسل الرابط مباشرة\n2) انتظر تجهيز الملف\n3) سيصلك الفيديو أو الصوت أو الصورة\n\nفي المجموعات استخدم منشن @${BOT_USERNAME} مع الرابط، أو أوقف Privacy Mode من BotFather.`,
    );
    return;
  }

  if (normalizedText === '/platforms') {
    await sendMessage(headers, chatId, '📱 المدعوم حالياً: TikTok, Instagram, YouTube, Facebook, Twitter/X, Pinterest وروابط الوسائط المباشرة.');
    return;
  }

  if (normalizedText === '/stats') {
    const today = new Date().toISOString().split('T')[0];
    const [{ count: totalCount }, { count: todayCount }] = await Promise.all([
      supabase.from('bot_downloads').select('*', { count: 'exact', head: true }).eq('telegram_user_id', userId),
      supabase
        .from('bot_downloads')
        .select('*', { count: 'exact', head: true })
        .eq('telegram_user_id', userId)
        .gte('created_at', today),
    ]);

    await sendMessage(
      headers,
      chatId,
      `📊 إحصائياتك\nإجمالي التحميلات: ${totalCount ?? 0}\nتحميلات اليوم: ${todayCount ?? 0}/${settings?.daily_download_limit ?? 10}`,
    );
    return;
  }

  const url = extractUrl(rawText);
  if (!url) {
    if (msg.chat.type === 'private' || normalizedText.startsWith('/')) {
      await sendMessage(headers, chatId, `🤖 أرسل رابطاً صالحاً، وفي المجموعات استخدم منشن @${BOT_USERNAME} مع الرابط.`);
    }
    return;
  }

  const platform = detectPlatform(url);
  if (!platform) {
    await sendMessage(headers, chatId, '❌ هذه المنصة غير مدعومة حالياً.');
    return;
  }

  const today = new Date().toISOString().split('T')[0];
  const { count: todayCount } = await supabase
    .from('bot_downloads')
    .select('*', { count: 'exact', head: true })
    .eq('telegram_user_id', userId)
    .gte('created_at', today);

  const dailyLimit = settings?.daily_download_limit ?? 10;
  if ((todayCount ?? 0) >= dailyLimit && userId !== DEVELOPER_CHAT_ID) {
    await sendMessage(headers, chatId, `⚠️ وصلت للحد اليومي (${dailyLimit}).`);
    return;
  }

  const { data: downloadRow } = await supabase
    .from('bot_downloads')
    .insert({
      telegram_user_id: userId,
      chat_id: chatId,
      url,
      platform: platform.name,
      status: 'processing',
      metadata: { chat_type: msg.chat.type, message_id: msg.message_id },
    })
    .select('id')
    .single();

  await sendMessage(headers, chatId, `🔍 جاري تجهيز ${platform.emoji} ${platform.name} ...`);

  if (DEVELOPER_CHAT_ID && userId !== DEVELOPER_CHAT_ID) {
    await sendMessage(headers, DEVELOPER_CHAT_ID, `📥 طلب تحميل جديد\n👤 ${userId}\n📌 ${platform.name}\n🔗 ${url}`);
  }

  const job = attemptDownload(supabase, headers, chatId, userId, url, platform, downloadRow?.id);
  if (globalThis.EdgeRuntime?.waitUntil) {
    globalThis.EdgeRuntime.waitUntil(job);
  } else {
    await job;
  }
}

async function storeUserAndMessage(supabase: any, update: any, msg: any, rawText: string) {
  if (msg.from) {
    await supabase.from('telegram_users').upsert(
      {
        telegram_id: Number(msg.from.id),
        username: msg.from.username ?? null,
        first_name: msg.from.first_name ?? null,
        last_name: msg.from.last_name ?? null,
        language_code: msg.from.language_code ?? null,
        is_premium: Boolean(msg.from.is_premium ?? false),
      },
      { onConflict: 'telegram_id' },
    );
  }

  await supabase.from('telegram_messages').upsert(
    {
      update_id: Number(update.update_id),
      chat_id: Number(msg.chat.id),
      telegram_user_id: msg.from?.id ? Number(msg.from.id) : null,
      text: rawText || null,
      message_type: msg.caption ? 'caption' : 'text',
      raw_update: update,
      processed: true,
    },
    { onConflict: 'update_id' },
  );
}

function shouldHandleMessage(msg: any, rawText: string) {
  if (!rawText) return false;
  if (msg.chat?.type === 'private') return true;
  if (extractCommand(rawText)) return true;
  if (extractUrl(rawText)) return true;
  if (rawText.includes(`@${BOT_USERNAME}`)) return true;
  const repliedUser = msg.reply_to_message?.from?.username;
  return repliedUser === BOT_USERNAME;
}

function getMessageText(msg: any) {
  return String(msg.text ?? msg.caption ?? '').trim();
}

function extractCommand(text: string) {
  const match = text.trim().match(/^\/(start|help|stats|platforms)(?:@([A-Za-z0-9_]+))?/i);
  if (!match) return null;
  const botMention = match[2];
  if (botMention && botMention.toLowerCase() !== BOT_USERNAME.toLowerCase()) return null;
  return `/${match[1].toLowerCase()}`;
}

function normalizeCommand(text: string) {
  return extractCommand(text) ?? text.replace(new RegExp(`@${BOT_USERNAME}`, 'ig'), '').trim();
}

function extractUrl(text: string) {
  const match = text.match(/https?:\/\/[^\s]+/i);
  const url = match?.[0] ?? null;
  if (url && !isSafeUrl(url)) return null;
  return url;
}

async function attemptDownload(
  supabase: any,
  headers: TelegramHeaders,
  chatId: number,
  userId: number,
  url: string,
  platform: { name: string; emoji: string },
  downloadId?: string,
) {
  try {
    const result =
      (await tryTikTokDownload(url, platform)) ||
      (await tryInstagramDownload(url, platform)) ||
      (await tryYoutubeDownload(url, platform)) ||
      (await tryDownloadWithCobalt(url)) ||
      (await tryGenericDownload(url));

    if (!result) {
      await supabase
        .from('bot_downloads')
        .update({ status: 'failed', error_message: `No download provider succeeded for ${platform.name}` })
        .eq('id', downloadId ?? '');

      const groupHint = chatId < 0
        ? `\n\nمهم للمجموعات: إذا كان البوت لا يرى كل الرسائل فعطّل Privacy Mode من BotFather أو أرسل الرابط مع @${BOT_USERNAME}.`
        : '';
      await sendMessage(headers, chatId, `❌ لم أستطع تحميل هذا الرابط حالياً.${groupHint}`);
      return;
    }

    await sendMediaToChat(headers, chatId, result, platform);
    await supabase
      .from('bot_downloads')
      .update({
        status: 'completed',
        media_type: result.type,
        quality: result.quality ?? 'auto',
        error_message: null,
      })
      .eq('id', downloadId ?? '');
  } catch (error) {
    console.error('attemptDownload failed', error);
    await supabase
      .from('bot_downloads')
      .update({ status: 'failed', error_message: String(error) })
      .eq('id', downloadId ?? '');
    await sendMessage(headers, chatId, '❌ حدث خطأ أثناء التحميل.');
  }

  if (DEVELOPER_CHAT_ID && userId !== DEVELOPER_CHAT_ID) {
    await sendMessage(headers, DEVELOPER_CHAT_ID, `✅ انتهت معالجة طلب ${userId}`);
  }
}

async function tryDownloadWithCobalt(url: string): Promise<DownloadResult | null> {
  const instances = ['https://api.cobalt.tools/api/json', 'https://cobalt-api.kwiatekmiki.com/api/json'];

  for (const endpoint of instances) {
    try {
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          'User-Agent': 'Mozilla/5.0',
          Referer: 'https://cobalt.tools/',
        },
        body: JSON.stringify({
          url,
          vCodec: 'h264',
          vQuality: '720',
          aFormat: 'mp3',
          isAudioOnly: false,
          isNoTTWatermark: true,
          isTTFullAudio: true,
        }),
      });

      if (!resp.ok) continue;
      const data = await resp.json();
      if (data?.status === 'stream' || data?.status === 'redirect') {
        return { url: data.url, type: 'video', quality: '720p' };
      }
      if (data?.status === 'picker' && Array.isArray(data.picker) && data.picker[0]?.url) {
        return {
          url: data.picker[0].url,
          type: data.picker[0].type === 'photo' ? 'photo' : 'video',
          quality: 'auto',
        };
      }
    } catch (error) {
      console.error('Cobalt provider failed', endpoint, error);
    }
  }

  return null;
}

async function tryTikTokDownload(url: string, platform: { name: string }): Promise<DownloadResult | null> {
  if (platform.name !== 'TikTok') return null;
  try {
    const resp = await fetch(`https://www.tikwm.com/api/?url=${encodeURIComponent(url)}&hd=1`, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        Accept: 'application/json,text/plain,*/*',
        Referer: 'https://www.tikwm.com/',
      },
    });
    if (!resp.ok) return null;
    const data = await resp.json();
    if (data?.code !== 0 || !data?.data) return null;
    if (Array.isArray(data.data.images) && data.data.images.length > 0) {
      return { url: data.data.images[0], type: 'photo' as const, quality: 'HD' };
    }
    const videoUrl = data.data.hdplay || data.data.play || data.data.wmplay;
    if (videoUrl) {
      return { url: videoUrl, type: 'video' as const, quality: 'HD' };
    }
  } catch (error) {
    console.error('TikTok download failed', error);
  }
  return null;
}

async function tryInstagramDownload(url: string, platform: { name: string }): Promise<DownloadResult | null> {
  if (platform.name !== 'Instagram') return null;
  try {
    const resp = await fetch(`https://api.saveig.app/api/v1/get-media?url=${encodeURIComponent(url)}`, {
      headers: { 'User-Agent': 'Mozilla/5.0', Accept: 'application/json' },
    });
    if (!resp.ok) return null;
    const data = await resp.json();
    const item = Array.isArray(data?.data) ? data.data[0] : null;
    if (!item?.url) return null;
    return {
      url: item.url,
      type: item.type === 'image' ? 'photo' : 'video',
      quality: 'auto',
    };
  } catch (error) {
    console.error('Instagram download failed', error);
  }
  return null;
}

async function tryYoutubeDownload(url: string, platform: { name: string }): Promise<DownloadResult | null> {
  if (platform.name !== 'YouTube') return null;
  try {
    const resp = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0',
        'Accept-Language': 'en-US,en;q=0.9',
      },
    });
    if (!resp.ok) return null;
    const html = await resp.text();
    const match = html.match(/ytInitialPlayerResponse\s*=\s*(\{.+?\});/s);
    if (!match) return null;
    const player = JSON.parse(match[1]);
    const streamingData = player?.streamingData;
    const progressive = Array.isArray(streamingData?.formats)
      ? streamingData.formats.find((item: any) => typeof item?.url === 'string')
      : null;
    if (progressive?.url) {
      return {
        url: progressive.url,
        type: 'video',
        quality: progressive.qualityLabel ?? 'auto',
      };
    }
  } catch (error) {
    console.error('YouTube direct extraction failed', error);
  }
  return null;
}

async function tryGenericDownload(url: string): Promise<DownloadResult | null> {
  try {
    const response = await fetch(url, { method: 'HEAD', redirect: 'follow' });
    const contentType = response.headers.get('content-type') || '';
    if (contentType.startsWith('video/')) return { url, type: 'video', quality: 'auto' };
    if (contentType.startsWith('image/')) return { url, type: 'photo', quality: 'auto' };
    if (contentType.startsWith('audio/')) return { url, type: 'audio', quality: 'auto' };
  } catch (error) {
    console.error('Generic direct media detection failed', error);
  }
  return null;
}

async function sendMediaToChat(headers: TelegramHeaders, chatId: number, result: DownloadResult, platform: { name: string; emoji: string }) {
  const caption = `✅ تم التحميل\n${platform.emoji} ${platform.name}\nالجودة: ${result.quality ?? 'auto'}`;

  const primaryMethod =
    result.type === 'video'
      ? 'sendVideo'
      : result.type === 'photo'
        ? 'sendPhoto'
        : result.type === 'audio'
          ? 'sendAudio'
          : 'sendDocument';

  const primaryKey =
    result.type === 'video'
      ? 'video'
      : result.type === 'photo'
        ? 'photo'
        : result.type === 'audio'
          ? 'audio'
          : 'document';

  const sendPrimary = await fetchTelegram(headers, primaryMethod, {
    chat_id: chatId,
    [primaryKey]: result.url,
    caption,
    supports_streaming: result.type === 'video',
  });

  if (sendPrimary.ok) return;

  const fallback = await fetchTelegram(headers, 'sendDocument', {
    chat_id: chatId,
    document: result.url,
    caption,
  });

  if (!fallback.ok) {
    console.error('Failed to send media via Telegram', sendPrimary, fallback);
    await sendMessage(headers, chatId, `✅ تم إيجاد الملف، لكن تيليجرام رفض الإرسال المباشر:\n${result.url}`);
  }
}

async function sendMessage(headers: TelegramHeaders, chatId: number, text: string) {
  const response = await fetchTelegram(headers, 'sendMessage', {
    chat_id: chatId,
    text,
    disable_web_page_preview: true,
  });
  if (!response.ok) {
    console.error('sendMessage failed', response);
  }
}

async function checkChannelMembership(headers: TelegramHeaders, channel: string, userId: number) {
  try {
    const response = await fetchTelegram(headers, 'getChatMember', {
      chat_id: channel,
      user_id: userId,
    });
    if (!response.ok) return true;
    return ['member', 'administrator', 'creator'].includes(String(response.result?.status ?? 'member'));
  } catch (error) {
    console.error('checkChannelMembership failed', error);
    return true;
  }
}

async function fetchTelegram(headers: TelegramHeaders, method: string, body: Record<string, unknown>) {
  const response = await fetch(`${GATEWAY_URL}/${method}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  let data: any = null;
  try {
    data = await response.json();
  } catch {
    data = { ok: false, description: await response.text() };
  }

  if (!response.ok && data?.ok !== false) {
    return { ok: false, description: data?.message || 'Telegram request failed', status: response.status };
  }

  return data;
}

function detectPlatform(url: string): { name: string; emoji: string } | null {
  const platforms = [
    { pattern: /youtube\.com|youtu\.be/i, name: 'YouTube', emoji: '🎥' },
    { pattern: /tiktok\.com/i, name: 'TikTok', emoji: '🎵' },
    { pattern: /instagram\.com/i, name: 'Instagram', emoji: '📸' },
    { pattern: /facebook\.com|fb\.watch/i, name: 'Facebook', emoji: '📘' },
    { pattern: /twitter\.com|x\.com/i, name: 'Twitter/X', emoji: '🐦' },
    { pattern: /pinterest\.com|pin\.it/i, name: 'Pinterest', emoji: '📌' },
  ];

  for (const platform of platforms) {
    if (platform.pattern.test(url)) return { name: platform.name, emoji: platform.emoji };
  }

  if (/\.(mp4|mov|mp3|m4a|jpg|jpeg|png|webp|gif)(\?|$)/i.test(url)) {
    return { name: 'Direct Media', emoji: '📎' };
  }

  return null;
}

function isSafeUrl(urlString: string): boolean {
  try {
    const parsed = new URL(urlString);
    // Only allow http and https
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return false;
    const hostname = parsed.hostname;
    // Block private/internal IP ranges and metadata endpoints
    if (
      hostname === 'localhost' ||
      hostname === '127.0.0.1' ||
      hostname === '0.0.0.0' ||
      hostname === '::1' ||
      hostname === '[::1]' ||
      hostname.startsWith('10.') ||
      hostname.startsWith('192.168.') ||
      hostname.startsWith('169.254.') ||
      hostname.endsWith('.internal') ||
      hostname.endsWith('.local') ||
      /^172\.(1[6-9]|2\d|3[01])\./.test(hostname)
    ) {
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

function jsonResponse(data: Record<string, unknown>, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}
