import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const GATEWAY_URL = 'https://connector-gateway.lovable.dev/telegram';
const MAX_RUNTIME_MS = 55_000;
const MIN_REMAINING_MS = 5_000;
const DEVELOPER_CHAT_ID = 6570434162;

Deno.serve(async () => {
  const startTime = Date.now();

  const LOVABLE_API_KEY = Deno.env.get('LOVABLE_API_KEY');
  if (!LOVABLE_API_KEY) return errorResponse('LOVABLE_API_KEY is not configured');

  const TELEGRAM_API_KEY = Deno.env.get('TELEGRAM_API_KEY');
  if (!TELEGRAM_API_KEY) return errorResponse('TELEGRAM_API_KEY is not configured');

  const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
  const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
  const supabase = createClient(supabaseUrl, supabaseServiceKey);

  const headers = {
    'Authorization': `Bearer ${LOVABLE_API_KEY}`,
    'X-Connection-Api-Key': TELEGRAM_API_KEY,
    'Content-Type': 'application/json',
  };

  let totalProcessed = 0;

  // Read initial offset
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
      headers,
      body: JSON.stringify({
        offset: currentOffset,
        timeout,
        allowed_updates: ['message'],
      }),
    });

    const data = await response.json();
    if (!response.ok) return errorResponse(`Telegram API error: ${JSON.stringify(data)}`);

    const updates = data.result ?? [];
    if (updates.length === 0) continue;

    for (const update of updates) {
      if (!update.message) continue;

      const msg = update.message;
      const chatId = msg.chat.id;
      const userId = msg.from?.id;
      const text = msg.text ?? '';

      // Upsert user
      if (msg.from) {
        const { error: upsertErr } = await supabase.from('telegram_users').upsert({
          telegram_id: userId,
          username: msg.from.username ?? null,
          first_name: msg.from.first_name ?? null,
          last_name: msg.from.last_name ?? null,
          language_code: msg.from.language_code ?? null,
          is_premium: msg.from.is_premium ?? false,
        }, { onConflict: 'telegram_id' });

        if (upsertErr) console.error('User upsert error:', upsertErr);
      }

      // Store message
      await supabase.from('telegram_messages').upsert({
        update_id: update.update_id,
        chat_id: chatId,
        telegram_user_id: userId,
        text,
        raw_update: update,
      }, { onConflict: 'update_id' });

      // Handle commands
      await handleMessage(supabase, headers, chatId, userId, text, msg);

      totalProcessed++;
    }

    // Update offset
    const newOffset = Math.max(...updates.map((u: any) => u.update_id)) + 1;
    await supabase
      .from('telegram_bot_state')
      .update({ update_offset: newOffset, updated_at: new Date().toISOString() })
      .eq('id', 1);

    currentOffset = newOffset;
  }

  return new Response(JSON.stringify({ ok: true, processed: totalProcessed }));
});

async function handleMessage(
  supabase: any,
  headers: Record<string, string>,
  chatId: number,
  userId: number,
  text: string,
  msg: any
) {
  const lowerText = text.toLowerCase().trim();

  // /start command
  if (lowerText === '/start') {
    const welcomeMsg = `🎬 *مرحباً بك في ABU ALAZ PLATFORM!*

أنا بوت تحميل الوسائط الذكي 🤖

*المنصات المدعومة:*
🎥 YouTube • TikTok • Instagram • Facebook
🐦 Twitter/X • Reddit • Snapchat
📌 Pinterest • Vimeo • Dailymotion
🎧 SoundCloud • Twitch

*كيف تستخدمني:*
📎 أرسل رابط أي فيديو/صورة/صوت
🔍 سأحلل الرابط تلقائياً
⬇️ وأقدم لك خيارات التحميل

*الأوامر:*
/start - رسالة الترحيب
/help - المساعدة
/stats - إحصائياتك
/platforms - المنصات المدعومة

_Developed by HAMO ABU ALAZ • v3.0_`;

    await sendMessage(headers, chatId, welcomeMsg, 'Markdown');

    // Notify developer about new user
    if (userId !== DEVELOPER_CHAT_ID) {
      const name = [msg.from?.first_name, msg.from?.last_name].filter(Boolean).join(' ');
      const username = msg.from?.username ? `@${msg.from.username}` : 'بدون';
      await sendMessage(
        headers,
        DEVELOPER_CHAT_ID,
        `🆕 *مستخدم جديد!*\n👤 الاسم: ${name}\n🔗 يوزر: ${username}\n🆔 ID: \`${userId}\`\n🌐 اللغة: ${msg.from?.language_code ?? 'غير محدد'}`,
        'Markdown'
      );
    }
    return;
  }

  // /help command
  if (lowerText === '/help') {
    await sendMessage(headers, chatId, `📖 *المساعدة*

*لتحميل فيديو:*
1️⃣ انسخ رابط الفيديو من أي منصة
2️⃣ الصقه هنا في المحادثة
3️⃣ سأعرض لك خيارات الجودة
4️⃣ اختر الجودة وسيبدأ التحميل

*ملاحظات:*
• التحميلات المجانية محدودة بـ 10 يومياً
• الاشتراك المميز يمنحك تحميلات غير محدودة
• بعض المنصات قد تحتاج وقت أطول`, 'Markdown');
    return;
  }

  // /stats command
  if (lowerText === '/stats') {
    const { count } = await supabase
      .from('bot_downloads')
      .select('*', { count: 'exact', head: true })
      .eq('telegram_user_id', userId);

    await sendMessage(headers, chatId, `📊 *إحصائياتك*\n\n📥 إجمالي التحميلات: ${count ?? 0}\n📦 الاشتراك: مجاني\n\n_استخدم /upgrade للترقية_`, 'Markdown');
    return;
  }

  // /platforms command
  if (lowerText === '/platforms') {
    await sendMessage(headers, chatId, `📱 *المنصات المدعومة:*

🎥 *فيديو:*
• YouTube (فيديو + قوائم + صوت)
• TikTok (بدون علامة مائية + HD)
• Instagram (Reels + Stories + Posts)
• Facebook (فيديوهات عامة)
• Twitter/X
• Reddit
• Snapchat

📌 *صور ومحتوى:*
• Pinterest
• Imgur • Flickr

🎧 *صوت:*
• SoundCloud • Mixcloud

🎬 *إضافي:*
• Vimeo • Dailymotion
• Twitch (Clips + VOD)
• Streamable`, 'Markdown');
    return;
  }

  // Check if it's a URL
  const urlRegex = /https?:\/\/[^\s]+/gi;
  const urls = text.match(urlRegex);

  if (urls && urls.length > 0) {
    const url = urls[0];
    const platform = detectPlatform(url);

    if (platform) {
      // Save download request
      await supabase.from('bot_downloads').insert({
        telegram_user_id: userId,
        chat_id: chatId,
        url,
        platform: platform.name,
        status: 'analyzing',
      });

      await sendMessage(headers, chatId, `🔍 *جاري تحليل الرابط...*

📌 المنصة: ${platform.emoji} ${platform.name}
🔗 الرابط: \`${url.substring(0, 50)}...\`

⏳ يرجى الانتظار...`, 'Markdown');

      // Notify developer
      await sendMessage(
        headers,
        DEVELOPER_CHAT_ID,
        `📥 *طلب تحميل جديد*\n👤 المستخدم: \`${userId}\`\n📌 المنصة: ${platform.name}\n🔗 \`${url}\``,
        'Markdown'
      );

      // For now, inform that download feature is being developed
      setTimeout(async () => {
        await sendMessage(headers, chatId, `⚠️ *خاصية التحميل قيد التطوير*

تم تسجيل طلبك وسيتم إشعارك عندما تصبح الخاصية متاحة!

في الوقت الحالي، يمكنك استخدام الأوامر الأخرى:
/help - للمساعدة
/stats - لإحصائياتك`, 'Markdown');
      }, 2000);
    } else {
      await sendMessage(headers, chatId, '❌ عذراً، هذه المنصة غير مدعومة حالياً.\n\nاستخدم /platforms لمعرفة المنصات المدعومة.');
    }
    return;
  }

  // Default response
  if (text && !text.startsWith('/')) {
    await sendMessage(headers, chatId, '🤖 أرسل لي رابط فيديو أو صورة لتحميلها!\n\nاستخدم /help للمساعدة.');
  }
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

async function sendMessage(
  headers: Record<string, string>,
  chatId: number,
  text: string,
  parseMode?: string
) {
  const body: any = { chat_id: chatId, text };
  if (parseMode) body.parse_mode = parseMode;

  try {
    const resp = await fetch(`${GATEWAY_URL}/sendMessage`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
    const data = await resp.json();
    if (!resp.ok) {
      console.error(`sendMessage failed [${resp.status}]:`, data);
    }
    return data;
  } catch (e) {
    console.error('sendMessage error:', e);
  }
}

function errorResponse(msg: string) {
  console.error(msg);
  return new Response(JSON.stringify({ error: msg }), { status: 500 });
}
