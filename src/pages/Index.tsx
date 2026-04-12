import { Download, Zap, Shield, Bot, Globe, Headphones, Film, Image, Music } from "lucide-react";

const platforms = [
  { name: "YouTube", emoji: "🎥", color: "from-red-500 to-red-600" },
  { name: "TikTok", emoji: "🎵", color: "from-pink-500 to-violet-500" },
  { name: "Instagram", emoji: "📸", color: "from-orange-500 to-pink-500" },
  { name: "Facebook", emoji: "📘", color: "from-blue-500 to-blue-600" },
  { name: "Twitter/X", emoji: "🐦", color: "from-sky-400 to-blue-500" },
  { name: "Reddit", emoji: "🔴", color: "from-orange-600 to-red-600" },
  { name: "Pinterest", emoji: "📌", color: "from-red-500 to-red-700" },
  { name: "SoundCloud", emoji: "🎧", color: "from-orange-500 to-orange-600" },
  { name: "Vimeo", emoji: "🎬", color: "from-cyan-500 to-blue-500" },
  { name: "Twitch", emoji: "🟣", color: "from-purple-500 to-purple-700" },
  { name: "Dailymotion", emoji: "📺", color: "from-blue-400 to-indigo-500" },
  { name: "Snapchat", emoji: "👻", color: "from-yellow-400 to-yellow-500" },
];

const features = [
  { icon: Bot, title: "ذكاء اصطناعي", desc: "تحليل ذكي للروابط وفهم الأوامر بلغة طبيعية" },
  { icon: Zap, title: "تحميل فوري", desc: "أرسل الرابط واحصل على الملف في ثوانٍ" },
  { icon: Shield, title: "آمن وموثوق", desc: "حماية بياناتك مع تشفير شامل" },
  { icon: Globe, title: "+15 منصة", desc: "دعم لأكثر من 15 منصة وسائط مختلفة" },
];

const mediaTypes = [
  { icon: Film, label: "فيديو", count: "8+" },
  { icon: Image, label: "صور", count: "5+" },
  { icon: Music, label: "صوت", count: "3+" },
  { icon: Headphones, label: "بودكاست", count: "2+" },
];

const Index = () => {
  return (
    <div className="min-h-screen bg-background text-foreground font-body overflow-x-hidden">
      {/* Hero Section */}
      <section className="relative min-h-screen flex flex-col items-center justify-center px-4 py-20">
        {/* Background effects */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-primary/5 blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-80 h-80 rounded-full bg-accent/5 blur-3xl" />
        </div>

        <div className="relative z-10 text-center max-w-4xl mx-auto">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-primary/20 bg-primary/5 mb-8">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse-glow" />
            <span className="text-sm text-primary font-medium">v3.0 — AI-Powered</span>
          </div>

          <h1 className="font-display text-5xl md:text-7xl font-bold tracking-tight mb-6">
            <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
              ABU ALAZ
            </span>
            <br />
            <span className="text-foreground">PLATFORM</span>
          </h1>

          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
            منصة تحميل الوسائط الذكية المدعومة بالذكاء الاصطناعي.
            حمّل الفيديوهات والصور والصوتيات من +15 منصة بضغطة واحدة.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <a
              href="https://t.me/your_bot_username"
              target="_blank"
              rel="noopener noreferrer"
              className="group flex items-center gap-3 px-8 py-4 rounded-xl bg-primary text-primary-foreground font-display font-semibold text-lg transition-all hover:scale-105 animate-pulse-glow"
            >
              <Bot className="w-5 h-5" />
              ابدأ مع البوت
            </a>
            <button className="flex items-center gap-3 px-8 py-4 rounded-xl border border-border bg-card text-foreground font-display font-medium text-lg transition-all hover:border-primary/50 hover:bg-card/80">
              <Download className="w-5 h-5" />
              اكتشف المزيد
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-8 max-w-md mx-auto">
            {[
              { value: "+15", label: "منصة" },
              { value: "AI", label: "ذكاء اصطناعي" },
              { value: "∞", label: "تحميلات" },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="font-display text-3xl font-bold text-primary">{stat.value}</div>
                <div className="text-sm text-muted-foreground mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="font-display text-3xl md:text-4xl font-bold text-center mb-4">
            لماذا <span className="text-primary">ABU ALAZ</span>؟
          </h2>
          <p className="text-muted-foreground text-center mb-16 max-w-xl mx-auto">
            تجربة تحميل لم تعهدها من قبل
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((f) => (
              <div
                key={f.title}
                className="group p-6 rounded-2xl border border-border bg-card hover:border-primary/30 transition-all hover:-translate-y-1"
              >
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                  <f.icon className="w-6 h-6 text-primary" />
                </div>
                <h3 className="font-display text-lg font-semibold mb-2">{f.title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Media Types */}
      <section className="py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {mediaTypes.map((m) => (
              <div key={m.label} className="flex flex-col items-center gap-3 p-6 rounded-2xl border border-border bg-card/50">
                <m.icon className="w-8 h-8 text-primary" />
                <span className="font-display font-semibold">{m.label}</span>
                <span className="text-xs text-muted-foreground">{m.count} منصة</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Platforms */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="font-display text-3xl md:text-4xl font-bold text-center mb-4">
            المنصات <span className="text-primary">المدعومة</span>
          </h2>
          <p className="text-muted-foreground text-center mb-16">جميع منصاتك المفضلة في مكان واحد</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {platforms.map((p) => (
              <div
                key={p.name}
                className="flex flex-col items-center gap-2 p-4 rounded-xl border border-border bg-card/50 hover:border-primary/30 transition-all hover:-translate-y-1 cursor-default"
              >
                <span className="text-3xl">{p.emoji}</span>
                <span className="text-sm font-medium">{p.name}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="font-display text-3xl md:text-4xl font-bold mb-16">
            كيف <span className="text-primary">يعمل؟</span>
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { step: "1", title: "أرسل الرابط", desc: "انسخ رابط الفيديو وأرسله للبوت" },
              { step: "2", title: "تحليل ذكي", desc: "الذكاء الاصطناعي يحلل الرابط ويحدد المنصة" },
              { step: "3", title: "تحميل فوري", desc: "اختر الجودة واحصل على ملفك" },
            ].map((s) => (
              <div key={s.step} className="flex flex-col items-center">
                <div className="w-14 h-14 rounded-full bg-primary/10 border-2 border-primary flex items-center justify-center mb-4 font-display text-xl font-bold text-primary">
                  {s.step}
                </div>
                <h3 className="font-display text-lg font-semibold mb-2">{s.title}</h3>
                <p className="text-muted-foreground text-sm">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-10 px-4">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="font-display font-bold text-lg">
            <span className="text-primary">ABU ALAZ</span> PLATFORM
          </div>
          <p className="text-sm text-muted-foreground">
            Developed by HAMO ABU ALAZ • v3.0
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Index;
