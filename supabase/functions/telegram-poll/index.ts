import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const GATEWAY_URL = 'https://connector-gateway.lovable.dev/telegram';
const MAX_RUNTIME_MS = 55_000;
const MIN_REMAINING_MS = 5_000;
const DEVELOPER_CHAT_ID = 6570434162;

// Free download APIs
const COBALT_API = 'https://api.cobalt.tools/api/json';
const COBALT_API_V2 = 'https://co.wuk.sh/api/json';

Deno.serve(async () => {
  const startTime = Date.now();

  const LOVABLE_API_KEY = Deno.env.get('LOVABLE_API_KEY');
  if (!LOVABLE_API_KEY) return errorResponse('LOVABLE_API_KEY is not configured');

  const TELEGRAM_API_KEY = Deno.env.get('TELEGRAM_API_KEY');
  if (!TELEGRAM_API_KEY) return errorResponse('TELEGRAM_API_KEY is not configured');

  const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
  const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
  const supabase = createClient(supabaseUrl, supabaseServiceKey);

  const tgHeaders = {
    'Authorization': `Bearer ${LOVABLE_API_KEY}`,
    'X-Connection-Api-Key': TELEGRAM_API_KEY,
    'Content-Type': 'application/json',
  };

  // Load bot settings
  const { data: settings } = await supabase
    .from('bot_settings')
    .select('*')
    .eq('id', 1)
    .single();

  let totalProcessed = 0;

  const { data: state, error: stateErr } = await supabase
    .from('telegram_bot_state')
    .select('update_offset')
    .eq('id', 1)
    .single();

  if (stateErr) return errorResponse(stateErr.message);
  let currentOffset = state.update_offset;

  while (true) {
    const elapsed = Date.now() - startTime;
    const remainingMs = MAX_RUNTIME_MS - elapsed;
    if (remainingMs < MIN_REMAINING_MS) break;

    const timeout = Math.min(50, Math.floor(remainingMs / 1000) - 5);
    if (timeout < 1) break;

    const response = await fetch(`${GATEWAY_URL}/getUpdates`, {
      method: 'POST',
      headers: tgHeaders,
      body: JSON.stringify({ offset: currentOffset, timeout, allowed_updates: ['message', 'callback_query'] }),
    });

    const data = await response.json();
    if (!response.ok) return errorResponse(`Telegram API error: ${JSON.stringify(data)}`);

    const updates = data.result ?? [];
    if (updates.length === 0) continue;

    for (const update of updates) {
      try {
        if (update.callback_query) {
          await handleCallbackQuery(supabase, tgHeaders, settings, update.callback_query);
        } else if (update.message) {
          const msg = update.message;
          const chatId = msg.chat.id;
          const userId = msg.from?.id;
          const text = msg.text ?? '';

          // Upsert user
          if (msg.from) {
            await supabase.from('telegram_users').upsert({
              telegram_id: userId,
              username: msg.from.username ?? null,
              first_name: msg.from.first_name ?? null,
              last_name: msg.from.last_name ?? null,
              language_code: msg.from.language_code ?? null,
              is_premium: msg.from.is_premium ?? false,
            }, { onConflict: 'telegram_id' });
          }

          // Store message
          await supabase.from('telegram_messages').upsert({
            update_id: update.update_id,
            chat_id: chatId,
            telegram_user_id: userId,
            text,
            raw_update: update,
          }, { onConflict: 'update_id' });

          // Check forced subscription
          if (settings?.is_forced_subscription_enabled && settings?.forced_channel && userId !== DEVELOPER_CHAT_ID) {
            const isMember = await checkChannelMembership(tgHeaders, settings.forced_channel, userId);
            if (!isMember) {
              const channelName = settings.forced_channel_name || settings.forced_channel;
              await sendMessage(tgHeaders, chatId, `⚠️ *يجب عليك الاشتراك في القناة أولاً!*\n\n📢 القناة: ${channelName}\n🔗 اشترك ثم أعد إرسال الرسالة\n\nرابط القناة: https://t.me/${settings.forced_channel.replace('@', '')}`, 'Markdown');
              continue;
            }
          }

          await handleMessage(supabase, tgHeaders, settings, chatId, userId, text, msg);
        }
        totalProcessed++;
      } catch (e) {
        console.error('Error processing update:', e);
      }
    }

    const newOffset = Math.max(...updates.map((u: any) => u.update_id)) + 1;
    await supabase
      .from('telegram_bot_state')
      .update({ update_offset: newOffset, updated_at: new Date().toISOString() })
      .eq('id', 1);
    currentOffset = newOffset;
  }

  return new Response(JSON.stringify({ ok: true, processed: totalProcessed }));
});

// ===================== HANDLERS =====================

async function handleCallbackQuery(supabase: any, headers: Record<string, string>, settings: any, query: any) {
  const chatId = query.message.chat.id;
  const userId = query.from.id;
  const data = query.data;

  // Answer callback to remove loading
  await fetch(`${GATEWAY_URL}/answerCallbackQuery`, {
    method: 'POST', headers,
    body: JSON.stringify({ callback_query_id: query.id }),
  });

  if (data.startsWith('dl:')) {
    const [, format, downloadId] = data.split(':');
    await processDownload(supabase, headers, chatId, userId, downloadId, format);
  }
}

async function handleMessage(supabase: any, headers: Record<string, string>, settings: any, chatId: number, userId: number, text: string, msg: any) {
  const lowerText = text.toLowerCase().trim();

  if (lowerText === '/start') {
    await sendMessage(headers, chatId, `🎬 *مرحباً بك في ABU ALAZ PLATFORM!*

أنا بوت تحميل الوسائط الذكي 🤖

*المنصات المدعومة:*
🎥 YouTube • TikTok • Instagram • Facebook
🐦 Twitter/X • Reddit • Snapchat
📌 Pinterest • Vimeo • Dailymotion
🎧 SoundCloud • Twitch

*كيف تستخدمني:*
📎 أرسل رابط أي فيديو/صورة/صوت
⬇️ سأحمله لك فوراً!

*الأوامر:*
/start - رسالة الترحيب
/help - المساعدة
/stats - إحصائياتك
/platforms - المنصات المدعومة

_Developed by HAMO ABU ALAZ • v3.0_`, 'Markdown');

    if (userId !== DEVELOPER_CHAT_ID) {
      const name = [msg.from?.first_name, msg.from?.last_name].filter(Boolean).join(' ');
      const username = msg.from?.username ? `@${msg.from.username}` : 'بدون';
      await sendMessage(headers, DEVELOPER_CHAT_ID,
        `🆕 *مستخدم جديد!*\n👤 ${name}\n🔗 ${username}\n🆔 \`${userId}\``, 'Markdown');
    }
    return;
  }

  if (lowerText === '/help') {
    await sendMessage(headers, chatId, `📖 *المساعدة*

1️⃣ انسخ رابط الفيديو من أي منصة
2️⃣ الصقه هنا
3️⃣ سأحمله لك تلقائياً!

*ملاحظات:*
• الحد اليومي: ${settings?.daily_download_limit ?? 10} تحميل
• بعض المنصات قد تحتاج وقت أطول`, 'Markdown');
    return;
  }

  if (lowerText === '/stats') {
    const today = new Date().toISOString().split('T')[0];
    const { count: totalCount } = await supabase
      .from('bot_downloads')
      .select('*', { count: 'exact', head: true })
      .eq('telegram_user_id', userId);
    const { count: todayCount } = await supabase
      .from('bot_downloads')
      .select('*', { count: 'exact', head: true })
      .eq('telegram_user_id', userId)
      .gte('created_at', today);

    await sendMessage(headers, chatId, `📊 *إحصائياتك*

📥 إجمالي التحميلات: ${totalCount ?? 0}
📅 تحميلات اليوم: ${todayCount ?? 0}/${settings?.daily_download_limit ?? 10}`, 'Markdown');
    return;
  }

  if (lowerText === '/platforms') {
    await sendMessage(headers, chatId, `📱 *المنصات المدعومة:*

🎥 YouTube • TikTok • Instagram • Facebook
🐦 Twitter/X • Reddit • Snapchat
📌 Pinterest • Imgur • Flickr
🎧 SoundCloud • Mixcloud
🎬 Vimeo • Dailymotion • Twitch • Streamable`, 'Markdown');
    return;
  }

  // Check URL
  const urlRegex = /https?:\/\/[^\s]+/gi;
  const urls = text.match(urlRegex);

  if (urls && urls.length > 0) {
    const url = urls[0];
    const platform = detectPlatform(url);

    if (!platform) {
      await sendMessage(headers, chatId, '❌ منصة غير مدعومة. استخدم /platforms');
      return;
    }

    // Check daily limit
    const today = new Date().toISOString().split('T')[0];
    const { count: todayCount } = await supabase
      .from('bot_downloads')
      .select('*', { count: 'exact', head: true })
      .eq('telegram_user_id', userId)
      .gte('created_at', today);

    const limit = settings?.daily_download_limit ?? 10;
    if ((todayCount ?? 0) >= limit && userId !== DEVELOPER_CHAT_ID) {
      await sendMessage(headers, chatId, `⚠️ وصلت للحد اليومي (${limit} تحميل).\nحاول غداً!`);
      return;
    }

    // Save download request
    const { data: dl } = await supabase.from('bot_downloads').insert({
      telegram_user_id: userId,
      chat_id: chatId,
      url,
      platform: platform.name,
      status: 'processing',
    }).select('id').single();

    await sendMessage(headers, chatId, `🔍 *جاري التحميل...*\n\n📌 ${platform.emoji} ${platform.name}\n⏳ يرجى الانتظار...`, 'Markdown');

    // Notify developer
    if (userId !== DEVELOPER_CHAT_ID) {
      await sendMessage(headers, DEVELOPER_CHAT_ID,
        `📥 *طلب تحميل*\n👤 \`${userId}\`\n📌 ${platform.name}\n🔗 \`${url}\``, 'Markdown');
    }

    // Try to download
    await attemptDownload(supabase, headers, chatId, userId, url, platform, dl?.id);
    return;
  }

  if (text && !text.startsWith('/')) {
    await sendMessage(headers, chatId, '🤖 أرسل لي رابط فيديو أو صورة لتحميلها!\n/help للمساعدة');
  }
}

// ===================== DOWNLOAD ENGINE =====================

async function attemptDownload(supabase: any, headers: Record<string, string>, chatId: number, userId: number, url: string, platform: any, downloadId: string) {
  try {
    // Method 1: Try cobalt.tools API
    const cobaltResult = await tryDownloadWithCobalt(url);
    if (cobaltResult) {
      await sendMediaToChat(headers, chatId, cobaltResult, platform);
      await supabase.from('bot_downloads').update({
        status: 'completed',
        media_type: cobaltResult.type,
        quality: cobaltResult.quality || 'auto',
      }).eq('id', downloadId);
      return;
    }

    // Method 2: Try alternative APIs
    const altResult = await tryAlternativeAPIs(url, platform);
    if (altResult) {
      await sendMediaToChat(headers, chatId, altResult, platform);
      await supabase.from('bot_downloads').update({
        status: 'completed',
        media_type: altResult.type,
        quality: altResult.quality || 'auto',
      }).eq('id', downloadId);
      return;
    }

    // If all methods fail
    await supabase.from('bot_downloads').update({
      status: 'failed',
      error_message: 'All download methods failed',
    }).eq('id', downloadId);

    await sendMessage(headers, chatId, `❌ *فشل التحميل*\n\nلم أتمكن من تحميل هذا المحتوى. قد يكون:\n• المحتوى خاص\n• المنصة تمنع التحميل\n• الرابط غير صالح\n\nحاول برابط آخر!`, 'Markdown');

  } catch (e) {
    console.error('Download error:', e);
    await supabase.from('bot_downloads').update({
      status: 'failed',
      error_message: String(e),
    }).eq('id', downloadId);

    await sendMessage(headers, chatId, '❌ حدث خطأ أثناء التحميل. حاول مرة أخرى.');
  }
}

async function tryDownloadWithCobalt(url: string): Promise<DownloadResult | null> {
  // Try multiple cobalt instances
  const instances = [
    'https://api.cobalt.tools',
    'https://cobalt-api.kwiatekmiki.com',
  ];

  for (const instance of instances) {
    try {
      const resp = await fetch(`${instance}/api/json`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          url,
          vCodec: 'h264',
          vQuality: '720',
          aFormat: 'mp3',
          isNoTTWatermark: true,
          isTTFullAudio: true,
        }),
      });

      if (!resp.ok) continue;
      const data = await resp.json();

      if (data.status === 'stream' || data.status === 'redirect') {
        return {
          url: data.url,
          type: 'video',
          quality: '720p',
        };
      }
      if (data.status === 'picker' && data.picker?.length > 0) {
        return {
          url: data.picker[0].url,
          type: data.picker[0].type === 'photo' ? 'photo' : 'video',
          quality: 'auto',
        };
      }
    } catch (e) {
      console.error(`Cobalt instance ${instance} failed:`, e);
    }
  }
  return null;
}

async function tryAlternativeAPIs(url: string, platform: any): Promise<DownloadResult | null> {
  // Try RapidAPI-free alternatives based on platform
  try {
    if (platform.name === 'TikTok') {
      return await tryTikTokDownload(url);
    }
    if (platform.name === 'Instagram') {
      return await tryInstagramDownload(url);
    }
    if (platform.name === 'Twitter/X') {
      return await tryTwitterDownload(url);
    }
    if (platform.name === 'Pinterest') {
      return await tryPinterestDownload(url);
    }
    // For YouTube and others, try a generic approach
    return await tryGenericDownload(url);
  } catch (e) {
    console.error('Alt API error:', e);
    return null;
  }
}

async function tryTikTokDownload(url: string): Promise<DownloadResult | null> {
  try {
    const resp = await fetch(`https://www.tikwm.com/api/?url=${encodeURIComponent(url)}&hd=1`);
    if (!resp.ok) return null;
    const data = await resp.json();
    if (data.code === 0 && data.data) {
      const d = data.data;
      if (d.images && d.images.length > 0) {
        return { url: d.images[0], type: 'photo', quality: 'HD' };
      }
      const videoUrl = d.hdplay || d.play;
      if (videoUrl) {
        return { url: videoUrl, type: 'video', quality: 'HD' };
      }
    }
  } catch (e) { console.error('TikTok alt error:', e); }
  return null;
}

async function tryInstagramDownload(url: string): Promise<DownloadResult | null> {
  try {
    const resp = await fetch(`https://api.saveig.app/api/v1/get-media?url=${encodeURIComponent(url)}`);
    if (!resp.ok) return null;
    const data = await resp.json();
    if (data.data && data.data.length > 0) {
      const item = data.data[0];
      return { url: item.url, type: item.type === 'image' ? 'photo' : 'video', quality: 'auto' };
    }
  } catch (e) { console.error('IG alt error:', e); }
  return null;
}

async function tryTwitterDownload(url: string): Promise<DownloadResult | null> {
  try {
    const resp = await fetch(`https://twitsave.com/info?url=${encodeURIComponent(url)}`);
    if (!resp.ok) return null;
    const html = await resp.text();
    const videoMatch = html.match(/https:\/\/[^"]+\.mp4[^"]*/);
    if (videoMatch) {
      return { url: videoMatch[0], type: 'video', quality: 'auto' };
    }
  } catch (e) { console.error('Twitter alt error:', e); }
  return null;
}

async function tryPinterestDownload(url: string): Promise<DownloadResult | null> {
  try {
    const resp = await fetch(`https://api.pinterest.com/url/?url=${encodeURIComponent(url)}`, { redirect: 'follow' });
    // Pinterest images are usually direct
    if (url.includes('/pin/')) {
      return { url, type: 'photo', quality: 'auto' };
    }
  } catch (e) { console.error('Pinterest alt error:', e); }
  return null;
}

async function tryGenericDownload(url: string): Promise<DownloadResult | null> {
  // Simple HEAD check to see if URL is a direct media link
  try {
    const resp = await fetch(url, { method: 'HEAD', redirect: 'follow' });
    const ct = resp.headers.get('content-type') || '';
    if (ct.startsWith('video/')) return { url, type: 'video', quality: 'auto' };
    if (ct.startsWith('image/')) return { url, type: 'photo', quality: 'auto' };
    if (ct.startsWith('audio/')) return { url, type: 'audio', quality: 'auto' };
  } catch (e) { /* ignore */ }
  return null;
}

// ===================== SEND MEDIA =====================

async function sendMediaToChat(headers: Record<string, string>, chatId: number, result: DownloadResult, platform: any) {
  const caption = `✅ تم التحميل!\n📌 ${platform.emoji} ${platform.name}\n📊 الجودة: ${result.quality || 'auto'}`;

  try {
    if (result.type === 'video') {
      const resp = await fetch(`${GATEWAY_URL}/sendVideo`, {
        method: 'POST', headers,
        body: JSON.stringify({
          chat_id: chatId,
          video: result.url,
          caption,
          supports_streaming: true,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        console.error('sendVideo failed, trying as document:', data);
        // Fallback: send as document
        await fetch(`${GATEWAY_URL}/sendDocument`, {
          method: 'POST', headers,
          body: JSON.stringify({ chat_id: chatId, document: result.url, caption }),
        });
      }
    } else if (result.type === 'photo') {
      const resp = await fetch(`${GATEWAY_URL}/sendPhoto`, {
        method: 'POST', headers,
        body: JSON.stringify({ chat_id: chatId, photo: result.url, caption }),
      });
      if (!resp.ok) {
        await fetch(`${GATEWAY_URL}/sendDocument`, {
          method: 'POST', headers,
          body: JSON.stringify({ chat_id: chatId, document: result.url, caption }),
        });
      }
    } else if (result.type === 'audio') {
      await fetch(`${GATEWAY_URL}/sendAudio`, {
        method: 'POST', headers,
        body: JSON.stringify({ chat_id: chatId, audio: result.url, caption }),
      });
    } else {
      await fetch(`${GATEWAY_URL}/sendDocument`, {
        method: 'POST', headers,
        body: JSON.stringify({ chat_id: chatId, document: result.url, caption }),
      });
    }
  } catch (e) {
    console.error('Send media error:', e);
    // Last fallback: send download link
    await sendMessage(headers, chatId, `✅ *تم إيجاد الرابط!*\n\n📌 ${platform.emoji} ${platform.name}\n🔗 [اضغط للتحميل](${result.url})`, 'Markdown');
  }
}

// ===================== UTILS =====================

interface DownloadResult {
  url: string;
  type: 'video' | 'photo' | 'audio' | 'document';
  quality?: string;
}

async function checkChannelMembership(headers: Record<string, string>, channel: string, userId: number): Promise<boolean> {
  try {
    const resp = await fetch(`${GATEWAY_URL}/getChatMember`, {
      method: 'POST', headers,
      body: JSON.stringify({ chat_id: channel, user_id: userId }),
    });
    const data = await resp.json();
    if (data.ok) {
      const status = data.result?.status;
      return ['member', 'administrator', 'creator'].includes(status);
    }
  } catch (e) {
    console.error('Check membership error:', e);
  }
  return true; // Allow on error
}

function detectPlatform(url: string): { name: string; emoji: string } | null {
  const platforms: { pattern: RegExp; name: string; emoji: string }[] = [
    { pattern: /youtube\.com|youtu\.be/i, name: 'YouTube', emoji: '🎥' },
    { pattern: /tiktok\.com/i, name: 'TikTok', emoji: '🎵' },
    { pattern: /instagram\.com/i, name: 'Instagram', emoji: '📸' },
    { pattern: /facebook\.com|fb\.watch/i, name: 'Facebook', emoji: '📘' },
    { pattern: /twitter\.com|x\.com/i, name: 'Twitter/X', emoji: '🐦' },
    { pattern: /reddit\.com/i, name: 'Reddit', emoji: '🔴' },
    { pattern: /snapchat\.com/i, name: 'Snapchat', emoji: '👻' },
    { pattern: /pinterest\.com|pin\.it/i, name: 'Pinterest', emoji: '📌' },
    { pattern: /soundcloud\.com/i, name: 'SoundCloud', emoji: '🎧' },
    { pattern: /vimeo\.com/i, name: 'Vimeo', emoji: '🎬' },
    { pattern: /dailymotion\.com/i, name: 'Dailymotion', emoji: '📺' },
    { pattern: /twitch\.tv/i, name: 'Twitch', emoji: '🟣' },
    { pattern: /streamable\.com/i, name: 'Streamable', emoji: '▶️' },
    { pattern: /imgur\.com/i, name: 'Imgur', emoji: '🖼️' },
    { pattern: /flickr\.com/i, name: 'Flickr', emoji: '📷' },
    { pattern: /mixcloud\.com/i, name: 'Mixcloud', emoji: '🎶' },
  ];

  for (const p of platforms) {
    if (p.pattern.test(url)) return { name: p.name, emoji: p.emoji };
  }
  return null;
}

async function sendMessage(headers: Record<string, string>, chatId: number, text: string, parseMode?: string) {
  const body: any = { chat_id: chatId, text };
  if (parseMode) body.parse_mode = parseMode;
  try {
    const resp = await fetch(`${GATEWAY_URL}/sendMessage`, {
      method: 'POST', headers, body: JSON.stringify(body),
    });
    if (!resp.ok) console.error('sendMessage failed:', await resp.text());
  } catch (e) {
    console.error('sendMessage error:', e);
  }
}

function errorResponse(msg: string) {
  console.error(msg);
  return new Response(JSON.stringify({ error: msg }), { status: 500 });
}
