import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Users, Download, MessageSquare, Settings, Shield, BarChart3, Bot, LogOut, Lock, Ban, CheckCircle, XCircle, RefreshCw } from "lucide-react";
import { toast } from "sonner";

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

const Admin = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [password, setPassword] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [downloads, setDownloads] = useState<any[]>([]);
  const [settings, setSettings] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);

  const apiCall = useCallback(async (action: string, method = 'GET', body?: any) => {
    const opts: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_KEY}`,
        'x-admin-password': adminPassword,
      },
    };
    if (body) opts.body = JSON.stringify(body);
    const resp = await fetch(`${SUPABASE_URL}/functions/v1/admin-api?action=${action}`, opts);
    if (!resp.ok) throw new Error('API error');
    return resp.json();
  }, [adminPassword]);

  const login = async () => {
    setLoading(true);
    try {
      setAdminPassword(password);
      const opts: RequestInit = {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${SUPABASE_KEY}`,
          'x-admin-password': password,
        },
      };
      const resp = await fetch(`${SUPABASE_URL}/functions/v1/admin-api?action=stats`, opts);
      if (resp.ok) {
        setIsLoggedIn(true);
        toast.success("تم تسجيل الدخول بنجاح");
      } else {
        toast.error("كلمة المرور غير صحيحة");
      }
    } catch {
      toast.error("خطأ في الاتصال");
    }
    setLoading(false);
  };

  const loadData = useCallback(async () => {
    setRefreshing(true);
    try {
      const [statsData, usersData, downloadsData, settingsData] = await Promise.all([
        apiCall('stats'),
        apiCall('users'),
        apiCall('downloads'),
        apiCall('settings'),
      ]);
      setStats(statsData);
      setUsers(usersData.users || []);
      setDownloads(downloadsData.downloads || []);
      setSettings(settingsData.settings);
    } catch {
      toast.error("خطأ في تحميل البيانات");
    }
    setRefreshing(false);
  }, [apiCall]);

  useEffect(() => {
    if (isLoggedIn) loadData();
  }, [isLoggedIn, loadData]);

  const updateSettings = async () => {
    try {
      await apiCall('update-settings', 'POST', settings);
      toast.success("تم حفظ الإعدادات");
    } catch {
      toast.error("خطأ في حفظ الإعدادات");
    }
  };

  const toggleBlock = async (telegramId: number, blocked: boolean) => {
    try {
      await apiCall(blocked ? 'unblock-user' : 'block-user', 'POST', { telegram_id: telegramId });
      toast.success(blocked ? 'تم إلغاء الحظر' : 'تم الحظر');
      loadData();
    } catch {
      toast.error("خطأ");
    }
  };

  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
              <Lock className="w-8 h-8 text-primary" />
            </div>
            <CardTitle className="text-2xl font-display">لوحة التحكم</CardTitle>
            <CardDescription>ABU ALAZ PLATFORM — Admin Panel</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              type="password"
              placeholder="كلمة مرور المدير"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && login()}
              dir="ltr"
            />
            <Button className="w-full" onClick={login} disabled={loading}>
              {loading ? "جاري الدخول..." : "دخول"}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background" dir="rtl">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bot className="w-7 h-7 text-primary" />
            <h1 className="font-display text-xl font-bold">
              <span className="text-primary">ABU ALAZ</span> — لوحة التحكم
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={loadData} disabled={refreshing}>
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            </Button>
            <Button variant="ghost" size="icon" onClick={() => setIsLoggedIn(false)}>
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-4 space-y-6">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard icon={Users} label="المستخدمين" value={stats.users.total} sub={`+${stats.users.today} اليوم`} />
            <StatCard icon={Download} label="التحميلات" value={stats.downloads.total} sub={`+${stats.downloads.today} اليوم`} />
            <StatCard icon={CheckCircle} label="ناجحة" value={stats.downloads.completed} color="text-green-400" />
            <StatCard icon={XCircle} label="فاشلة" value={stats.downloads.failed} color="text-red-400" />
          </div>
        )}

        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="bg-card border border-border">
            <TabsTrigger value="overview"><BarChart3 className="w-4 h-4 ml-2" />نظرة عامة</TabsTrigger>
            <TabsTrigger value="users"><Users className="w-4 h-4 ml-2" />المستخدمين</TabsTrigger>
            <TabsTrigger value="downloads"><Download className="w-4 h-4 ml-2" />التحميلات</TabsTrigger>
            <TabsTrigger value="settings"><Settings className="w-4 h-4 ml-2" />الإعدادات</TabsTrigger>
          </TabsList>

          {/* Overview */}
          <TabsContent value="overview" className="space-y-4">
            {stats && (
              <div className="grid md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">📊 المنصات الأكثر استخداماً</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {Object.entries(stats.platforms || {})
                      .sort(([, a]: any, [, b]: any) => b - a)
                      .map(([name, count]: any) => (
                        <div key={name} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                          <span>{name}</span>
                          <Badge variant="secondary">{count}</Badge>
                        </div>
                      ))}
                    {Object.keys(stats.platforms || {}).length === 0 && (
                      <p className="text-muted-foreground text-sm">لا توجد بيانات بعد</p>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">📈 ملخص سريع</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <InfoRow label="إجمالي الرسائل" value={stats.messages.total} />
                    <InfoRow label="معدل النجاح" value={stats.downloads.total > 0 ? `${Math.round((stats.downloads.completed / stats.downloads.total) * 100)}%` : '0%'} />
                    <InfoRow label="مستخدمين اليوم" value={stats.users.today} />
                    <InfoRow label="تحميلات اليوم" value={stats.downloads.today} />
                  </CardContent>
                </Card>
              </div>
            )}
          </TabsContent>

          {/* Users */}
          <TabsContent value="users">
            <Card>
              <CardHeader>
                <CardTitle>المستخدمين ({users.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>المستخدم</TableHead>
                        <TableHead>يوزرنيم</TableHead>
                        <TableHead>Telegram ID</TableHead>
                        <TableHead>اللغة</TableHead>
                        <TableHead>الحالة</TableHead>
                        <TableHead>التاريخ</TableHead>
                        <TableHead>إجراء</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {users.map((u) => (
                        <TableRow key={u.id}>
                          <TableCell>{[u.first_name, u.last_name].filter(Boolean).join(' ') || '-'}</TableCell>
                          <TableCell dir="ltr">{u.username ? `@${u.username}` : '-'}</TableCell>
                          <TableCell dir="ltr">{u.telegram_id}</TableCell>
                          <TableCell>{u.language_code || '-'}</TableCell>
                          <TableCell>
                            {u.is_blocked ? <Badge variant="destructive">محظور</Badge> : <Badge className="bg-green-600">نشط</Badge>}
                            {u.is_premium && <Badge className="bg-yellow-500 mr-1">Premium</Badge>}
                          </TableCell>
                          <TableCell dir="ltr" className="text-xs">{new Date(u.created_at).toLocaleDateString()}</TableCell>
                          <TableCell>
                            <Button size="sm" variant={u.is_blocked ? "outline" : "destructive"} onClick={() => toggleBlock(u.telegram_id, u.is_blocked)}>
                              <Ban className="w-3 h-3 ml-1" />
                              {u.is_blocked ? 'فك' : 'حظر'}
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Downloads */}
          <TabsContent value="downloads">
            <Card>
              <CardHeader>
                <CardTitle>التحميلات ({downloads.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>المستخدم</TableHead>
                        <TableHead>المنصة</TableHead>
                        <TableHead>الرابط</TableHead>
                        <TableHead>الحالة</TableHead>
                        <TableHead>الجودة</TableHead>
                        <TableHead>التاريخ</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {downloads.map((d) => (
                        <TableRow key={d.id}>
                          <TableCell dir="ltr">{d.telegram_user_id}</TableCell>
                          <TableCell>{d.platform || '-'}</TableCell>
                          <TableCell dir="ltr" className="max-w-[200px] truncate text-xs">
                            <a href={d.url} target="_blank" rel="noopener" className="text-primary hover:underline">{d.url}</a>
                          </TableCell>
                          <TableCell>
                            <Badge variant={d.status === 'completed' ? 'default' : d.status === 'failed' ? 'destructive' : 'secondary'}>
                              {d.status === 'completed' ? '✅' : d.status === 'failed' ? '❌' : '⏳'} {d.status}
                            </Badge>
                          </TableCell>
                          <TableCell>{d.quality || '-'}</TableCell>
                          <TableCell dir="ltr" className="text-xs">{new Date(d.created_at).toLocaleString()}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Settings */}
          <TabsContent value="settings">
            {settings && (
              <div className="grid md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Shield className="w-5 h-5 text-primary" />
                      الاشتراك الإجباري
                    </CardTitle>
                    <CardDescription>إجبار المستخدمين على الاشتراك في قناة معينة</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span>تفعيل الاشتراك الإجباري</span>
                      <Switch
                        checked={settings.is_forced_subscription_enabled}
                        onCheckedChange={(v) => setSettings({ ...settings, is_forced_subscription_enabled: v })}
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm text-muted-foreground">معرّف القناة (مثال: @channel)</label>
                      <Input
                        dir="ltr"
                        placeholder="@your_channel"
                        value={settings.forced_channel || ''}
                        onChange={(e) => setSettings({ ...settings, forced_channel: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm text-muted-foreground">اسم القناة (للعرض)</label>
                      <Input
                        placeholder="اسم القناة"
                        value={settings.forced_channel_name || ''}
                        onChange={(e) => setSettings({ ...settings, forced_channel_name: e.target.value })}
                      />
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Settings className="w-5 h-5 text-primary" />
                      إعدادات عامة
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <label className="text-sm text-muted-foreground">الحد اليومي للتحميل</label>
                      <Input
                        type="number"
                        dir="ltr"
                        value={settings.daily_download_limit}
                        onChange={(e) => setSettings({ ...settings, daily_download_limit: parseInt(e.target.value) || 10 })}
                      />
                    </div>
                    <Button className="w-full" onClick={updateSettings}>
                      💾 حفظ الإعدادات
                    </Button>
                  </CardContent>
                </Card>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

// Small helper components
const StatCard = ({ icon: Icon, label, value, sub, color }: any) => (
  <Card>
    <CardContent className="p-4 flex items-center gap-3">
      <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
        <Icon className={`w-5 h-5 ${color || 'text-primary'}`} />
      </div>
      <div>
        <p className="text-2xl font-bold font-display">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
        {sub && <p className="text-xs text-primary">{sub}</p>}
      </div>
    </CardContent>
  </Card>
);

const InfoRow = ({ label, value }: any) => (
  <div className="flex items-center justify-between py-2 border-b border-border last:border-0">
    <span className="text-sm text-muted-foreground">{label}</span>
    <span className="font-semibold">{value}</span>
  </div>
);

export default Admin;
