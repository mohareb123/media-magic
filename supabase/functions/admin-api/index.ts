import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-admin-password',
};

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
  const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
  const supabase = createClient(supabaseUrl, supabaseServiceKey);

  const url = new URL(req.url);
  const action = url.searchParams.get('action');

  // Simple admin auth via password in header
  const adminPass = req.headers.get('x-admin-password');
  const { data: settings } = await supabase.from('bot_settings').select('admin_password').eq('id', 1).single();

  if (adminPass !== settings?.admin_password) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }

  try {
    let result: any = {};

    switch (action) {
      case 'stats': {
        const { count: userCount } = await supabase.from('telegram_users').select('*', { count: 'exact', head: true });
        const { count: downloadCount } = await supabase.from('bot_downloads').select('*', { count: 'exact', head: true });
        const { count: messageCount } = await supabase.from('telegram_messages').select('*', { count: 'exact', head: true });
        
        const today = new Date().toISOString().split('T')[0];
        const { count: todayDownloads } = await supabase.from('bot_downloads').select('*', { count: 'exact', head: true }).gte('created_at', today);
        const { count: todayUsers } = await supabase.from('telegram_users').select('*', { count: 'exact', head: true }).gte('created_at', today);
        
        const { count: completedCount } = await supabase.from('bot_downloads').select('*', { count: 'exact', head: true }).eq('status', 'completed');
        const { count: failedCount } = await supabase.from('bot_downloads').select('*', { count: 'exact', head: true }).eq('status', 'failed');

        // Platform breakdown
        const { data: platformData } = await supabase.from('bot_downloads').select('platform');
        const platformCounts: Record<string, number> = {};
        platformData?.forEach((d: any) => {
          if (d.platform) platformCounts[d.platform] = (platformCounts[d.platform] || 0) + 1;
        });

        result = {
          users: { total: userCount ?? 0, today: todayUsers ?? 0 },
          downloads: { total: downloadCount ?? 0, today: todayDownloads ?? 0, completed: completedCount ?? 0, failed: failedCount ?? 0 },
          messages: { total: messageCount ?? 0 },
          platforms: platformCounts,
        };
        break;
      }

      case 'users': {
        const { data, count } = await supabase.from('telegram_users').select('*', { count: 'exact' }).order('created_at', { ascending: false }).limit(100);
        result = { users: data, total: count };
        break;
      }

      case 'downloads': {
        const { data, count } = await supabase.from('bot_downloads').select('*', { count: 'exact' }).order('created_at', { ascending: false }).limit(100);
        result = { downloads: data, total: count };
        break;
      }

      case 'settings': {
        const { data } = await supabase.from('bot_settings').select('*').eq('id', 1).single();
        result = { settings: data };
        break;
      }

      case 'update-settings': {
        const body = await req.json();
        const { error } = await supabase.from('bot_settings').update({
          forced_channel: body.forced_channel ?? null,
          forced_channel_name: body.forced_channel_name ?? null,
          is_forced_subscription_enabled: body.is_forced_subscription_enabled ?? false,
          daily_download_limit: body.daily_download_limit ?? 10,
        }).eq('id', 1);
        if (error) throw error;
        result = { success: true };
        break;
      }

      case 'block-user': {
        const body = await req.json();
        const { error } = await supabase.from('telegram_users').update({ is_blocked: true }).eq('telegram_id', body.telegram_id);
        if (error) throw error;
        result = { success: true };
        break;
      }

      case 'unblock-user': {
        const body = await req.json();
        const { error } = await supabase.from('telegram_users').update({ is_blocked: false }).eq('telegram_id', body.telegram_id);
        if (error) throw error;
        result = { success: true };
        break;
      }

      default:
        return new Response(JSON.stringify({ error: 'Unknown action' }), {
          status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
    }

    return new Response(JSON.stringify(result), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (e) {
    console.error('Admin API error:', e);
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
