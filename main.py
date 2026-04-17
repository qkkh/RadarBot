import asyncio, os, re, discord, requests
from discord.ext import commands, tasks
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# --- نظام الاستضافة ---
app = Flask('')
@app.route('/')
def home(): return "RADARZ Operations Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run); t.daemon = True; t.start()

# --- الإعدادات العامة ---
class RadarConfig:
    TOKEN = os.getenv('DISCORD_TOKEN')
    MAIN_COLOR = discord.Color.red()
    # القناة التي حددتها لنشر الفيديوهات
    YT_POST_CHANNEL_ID = 924316521050820609 
    # كاتيجوري الإحصائيات
    STATS_CATEGORY_ID = 1494627032112304179
    # ضع هنا الـ ID الخاص بقناتك (يبدأ بـ UC) للربط التلقائي
    YOUTUBE_CHANNEL_ID = "ضع_هنا_ID_قناتك" 
    AUTHORIZED_USERS = [1341796578742243338, 551817782996762624, 366132848228564992, 1376970309797941372, 1342856146662461574]

# --- دالة سحب اسم القناة (حل مشكلة "YouTube Creator") ---
def get_yt_channel_name(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers).text
        # البحث عن اسم صاحب القناة في كود الصفحة
        match = re.search(r'"author":"(.*?)"', r)
        if match: return match.group(1)
        match_alt = re.search(r'<link itemprop="name" content="(.*?)">', r)
        return match_alt.group(1) if match_alt else "قناة يوتيوب"
    except: return "قناة يوتيوب"

# --- نظام تحديث الإحصائيات ---
async def refresh_stats(guild):
    category = guild.get_channel(RadarConfig.STATS_CATEGORY_ID)
    if not category: return False
    for vc in category.voice_channels: await vc.delete()
    stats = [f"👥 الأعضاء: {guild.member_count}", f"🟢 المتواجدون: {len([m for m in guild.members if m.status != discord.Status.offline])}"]
    for s in stats:
        await guild.create_voice_channel(s, category=category, overwrites={guild.default_role: discord.PermissionOverwrite(connect=False)})
    return True

# --- واجهة فيديو اليوتيوب الجديدة ---
class YoutubeModal(discord.ui.Modal, title='نشر فيديو يوتيوب 🎬'):
    link = discord.ui.TextInput(label="رابط الفيديو", required=True)
    ment = discord.ui.TextInput(label="المنشن", default="everyone")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # سحب اسم القناة الحقيقي تلقائياً
        channel_name = get_yt_channel_name(self.link.value)
        target_ch = interaction.guild.get_channel(RadarConfig.YT_POST_CHANNEL_ID)
        
        # التنسيق الاحترافي المطلوب
        content = f"Hey @{self.ment.value} **{channel_name}** uploaded a new youtube video!\n{self.link.value}"
        
        if target_ch:
            await target_ch.send(content=content)
            await interaction.followup.send(f"✅ تم النشر في قناة الفيديوهات باسم: {channel_name}", ephemeral=True)
        else:
            await interaction.followup.send("❌ فشل العثور على قناة النشر.", ephemeral=True)

# --- لوحة التحكم الكاملة بجميع الأزرار ---
class AdminDashboard(discord.ui.View):
    def __init__(self, bot): super().__init__(timeout=None); self.bot = bot
    
    @discord.ui.button(label="إرسال رسالة 📝", style=discord.ButtonStyle.success, emoji="💬", row=0)
    async def s(self, i, b):
        class MsgM(discord.ui.Modal, title='إرسال رسالة'):
            m = discord.ui.TextInput(label="المحتوى", style=discord.TextStyle.paragraph)
            async def on_submit(self, i): await i.channel.send(self.m.value); await i.response.send_message("✅ تم الإرسال", ephemeral=True)
        await i.response.send_modal(MsgM())

    @discord.ui.button(label="إطلاق بث 🚀", style=discord.ButtonStyle.danger, emoji="🔴", row=0)
    async def strm(self, i, b):
        await i.response.send_message("🚀 ميزة البث المتقدمة قيد الصيانة.. استخدم فيديو اليوتيوب مؤقتاً.", ephemeral=True)

    @discord.ui.button(label="فيديو اليوتيوب 🎬", style=discord.ButtonStyle.primary, emoji="🎥", row=1)
    async def yt(self, i, b): await i.response.send_modal(YoutubeModal())

    @discord.ui.button(label="تحديث الإحصائيات 🔄", style=discord.ButtonStyle.secondary, emoji="♻️", row=1)
    async def refresh_btn(self, i, b):
        await i.response.defer(ephemeral=True)
        if await refresh_stats(i.guild): await i.followup.send("✅ تم تحديث الإحصائيات", ephemeral=True)
        else: await i.followup.send("❌ تأكد من ID الكاتيجوري", ephemeral=True)

# --- نظام المراقبة التلقائي (الربط) ---
last_video_id = None
@tasks.loop(minutes=5)
async def check_youtube_task():
    global last_video_id
    if RadarConfig.YOUTUBE_CHANNEL_ID == "ضع_هنا_ID_قناتك": return
    try:
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={RadarConfig.YOUTUBE_CHANNEL_ID}"
        response = requests.get(rss_url).text
        video_id = re.search(r'<yt:videoId>(.*?)</yt:videoId>', response).group(1)
        if video_id != last_video_id:
            if last_video_id is not None:
                channel = bot.get_channel(RadarConfig.YT_POST_CHANNEL_ID)
                author = re.search(r'<author><name>(.*?)</name>', response).group(1)
                await channel.send(f"Hey @everyone **{author}** uploaded a new youtube video!\nhttps://www.youtube.com/watch?v={video_id}")
            last_video_id = video_id
    except: pass

class RadarBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def on_ready(self):
        await self.tree.sync()
        check_youtube_task.start()
        print(f"📡 {self.user} Online & Tracking {RadarConfig.YT_POST_CHANNEL_ID}")

bot = RadarBot()
@bot.tree.command(name="panel", description="لوحة التحكم الكاملة")
async def panel(i: discord.Interaction):
    if i.user.id in RadarConfig.AUTHORIZED_USERS:
        emb = discord.Embed(title="🎮 مركز عمليات RADARZ", description="تحكم في النشر التلقائي واليدوي والإحصائيات.", color=RadarConfig.MAIN_COLOR)
        await i.response.send_message(embed=emb, view=AdminDashboard(bot), ephemeral=True)

if __name__ == '__main__':
    keep_alive()
    bot.run(RadarConfig.TOKEN)
