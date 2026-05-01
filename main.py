import asyncio os re discord io
from discord.ext import commands tasks
from discord import app_commands
from flask import Flask
from threading import Thread
from datetime import datetime timedelta
from PIL import Image ImageDraw

# --- نظام الاستضافة ---
app = Flask('')
@app.route('/')
def home(): return "RADARZ Operations Online"
def run(): app.run(host='0.0.0.0' port=8080)
def keep_alive():
    t = Thread(target=run) t.daemon = True t.start()

# --- الإعدادات ---
class RadarConfig:
    TOKEN = os.getenv('DISCORD_TOKEN')
    MAIN_COLOR = discord.Color.red()
    STREAM_CHANNEL_ID = 1200740059817721856
    YOUTUBE_CHANNEL_ID = 924316521050820609
    STATS_CATEGORY_ID = 1494627032112304179 
    WELCOME_CHANNEL_ID = 924274202872266785
    ALLOWED_ROLES = [1377997626938753114 1494645555865976872 1498095128122884236]

def has_radar_permission(member):
    if member.guild_permissions.administrator: return True
    return any(role.id in RadarConfig.ALLOWED_ROLES for role in member.roles)

# --- نظام الإحصائيات ---
async def refresh_radar_stats(guild):
    cat = guild.get_channel(RadarConfig.STATS_CATEGORY_ID)
    if not cat: return
    online = len([m for m in guild.members if m.status != discord.Status.offline and not m.bot])
    bots = len([m for m in guild.members if m.bot])
    stats_data = [f"👥 Members: {guild.member_count}" f"🟢 Online: {online}" f"🤖 Bots: {bots}"]
    vcs = sorted(cat.voice_channels key=lambda x: x.position)
    for i stat_text in enumerate(stats_data):
        if i < len(vcs):
            if vcs[i].name != stat_text: await vcs[i].edit(name=stat_text)

# --- نظام الداشبورد الثابتة (أزرار للأبد) ---
class AdminDashboard(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="إطلاق بث 🚀" style=discord.ButtonStyle.danger custom_id="btn_stream")
    async def st(self i b): await i.response.send_modal(StreamModal())
    @discord.ui.button(label="يوتيوب 🎬" style=discord.ButtonStyle.primary custom_id="btn_yt")
    async def yt(self i b): await i.response.send_modal(YoutubeModal())
    @discord.ui.button(label="تحديث الإحصائيات 🔄" style=discord.ButtonStyle.secondary custom_id="btn_refresh")
    async def r(self i b):
        await i.response.defer(ephemeral=True)
        await refresh_radar_stats(i.guild)
        await i.followup.send("✅ تم تحديث الإحصائيات")

class StreamModal(discord.ui.Modal title='إشارة بث 📡'):
    t = discord.ui.TextInput(label="العنوان")
    ti = discord.ui.TextInput(label="بعد كم دقيقة؟")
    l = discord.ui.TextInput(label="الرابط")
    async def on_submit(self i):
        ts = int((datetime.now() + timedelta(minutes=int(self.ti.value))).timestamp())
        ch = i.guild.get_channel(RadarConfig.STREAM_CHANNEL_ID)
        emb = discord.Embed(title=f"🚨 إشارة بث: {self.t.value}" color=discord.Color.red())
        emb.add_field(name="⏳ الانطلاق" value=f"<t:{ts}:R>")
        await ch.send(content="@everyone رادار البث رصد إشارة جديدة" embed=emb)
        await i.response.send_message("✅ تم الإرسال" ephemeral=True)

class YoutubeModal(discord.ui.Modal title='فيديو جديد 🎬'):
    l = discord.ui.TextInput(label="الرابط")
    m = discord.ui.TextInput(label="المنشن" default="everyone")
    async def on_submit(self i):
        ch = i.guild.get_channel(RadarConfig.YOUTUBE_CHANNEL_ID)
        if ch: await ch.send(content=f"📣 @{self.m.value} فيديو جديد!\n{self.l.value}")
        await i.response.send_message("✅ تم النشر" ephemeral=True)

class RadarBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!" intents=discord.Intents.all())
    async def setup_hook(self): 
        self.auto_refresh_stats.start()
        self.add_view(AdminDashboard())
    async def on_ready(self): 
        await self.tree.sync() print(f"📡 {self.user} Online")
    @tasks.loop(minutes=10)
    async def auto_refresh_stats(self):
        for g in self.guilds: await refresh_radar_stats(g)

bot = RadarBot()

# --- أوامر السلاش (20 أمر إداري + الأوامر الخاصة) ---

@bot.tree.command(name="setpanel" description="تثبيت لوحة التحكم")
async def setpanel(i):
    if not has_radar_permission(i.user): return await i.response.send_message("❌" ephemeral=True)
    await i.response.defer(ephemeral=True)
    emb = discord.Embed(title="🎮 RADARZ Dashboard" description="لوحة التحكم الدائمة للمسؤولين" color=RadarConfig.MAIN_COLOR)
    await i.channel.send(embed=emb view=AdminDashboard())
    await i.followup.send("✅ تم تثبيت البانل")

@bot.tree.command(name="say" description="إرسال رسالة")
async def say(i message: str mention: str = None):
    if not has_radar_permission(i.user): return await i.response.send_message("❌" ephemeral=True)
    await i.channel.send(content=f"@{mention}\n{message}" if mention else message)
    await i.response.send_message("✅ تم" ephemeral=True)

@bot.tree.command(name="clear" description="مسح الرسائل")
async def clear(i amount: int):
    await i.response.defer(ephemeral=True)
    await i.channel.purge(limit=amount)
    await i.followup.send(f"🧹 تم مسح {amount}")

@bot.tree.command(name="lock" description="قفل الروم")
async def lock(i):
    await i.channel.set_permissions(i.guild.default_role send_messages=False)
    await i.response.send_message("🔒 قفل")

@bot.tree.command(name="unlock" description="فتح الروم")
async def unlock(i):
    await i.channel.set_permissions(i.guild.default_role send_messages=True)
    await i.response.send_message("🔓 فتح")

@bot.tree.command(name="hide" description="إخفاء الروم")
async def hide(i):
    await i.channel.set_permissions(i.guild.default_role view_channel=False)
    await i.response.send_message("👻 إخفاء")

@bot.tree.command(name="show" description="إظهار الروم")
async def show(i):
    await i.channel.set_permissions(i.guild.default_role view_channel=True)
    await i.response.send_message("👁️ إظهار")

@bot.tree.command(name="kick" description="طرد")
async def kick(i member: discord.Member):
    await member.kick()
    await i.response.send_message(f"👞 طرد {member.name}")

@bot.tree.command(name="ban" description="حظر")
async def ban(i member: discord.Member):
    await member.ban()
    await i.response.send_message(f"🚫 حظر {member.name}")

@bot.tree.command(name="mute" description="كتم")
async def mute(i member: discord.Member minutes: int):
    await member.timeout(timedelta(minutes=minutes))
    await i.response.send_message(f"🔇 كتم {member.name}")

@bot.tree.command(name="unmute" description="فك كتم")
async def unmute(i member: discord.Member):
    await member.timeout(None)
    await i.response.send_message(f"🔊 فك كتم {member.name}")

@bot.tree.command(name="slowmode" description="وضع بطيء")
async def slowmode(i seconds: int):
    await i.channel.edit(slowmode_delay=seconds)
    await i.response.send_message(f"⏳ {seconds} ثانية")

@bot.tree.command(name="nick" description="تغيير لقب")
async def nick(i member: discord.Member name: str):
    await member.edit(nick=name)
    await i.response.send_message(f"📝 تغيير لقب {member.name}")

@bot.tree.command(name="role_add" description="إضافة رتبة")
async def role_add(i member: discord.Member role: discord.Role):
    await member.add_roles(role)
    await i.response.send_message("✅ إضافة")

@bot.tree.command(name="role_remove" description="سحب رتبة")
async def role_remove(i member: discord.Member role: discord.Role):
    await member.remove_roles(role)
    await i.response.send_message("❌ سحب")

@bot.tree.command(name="warn" description="تحذير")
async def warn(i member: discord.Member reason: str):
    await i.response.send_message(f"⚠️ {member.mention} تحذير {reason}")

@bot.tree.command(name="move" description="نقل عضو")
async def move(i member: discord.Member channel: discord.VoiceChannel):
    await member.move_to(channel)
    await i.response.send_message("✈️ نقل")

@bot.tree.command(name="vmute" description="كتم صوتي")
async def vmute(i member: discord.Member):
    await member.edit(mute=True)
    await i.response.send_message("🔇 كتم صوت")

@bot.tree.command(name="vunmute" description="فك كتم صوت")
async def vunmute(i member: discord.Member):
    await member.edit(mute=False)
    await i.response.send_message("🔊 فك صوت")

@bot.tree.command(name="deafen" description="تعطيل سماع")
async def deafen(i member: discord.Member):
    await member.edit(deafen=True)
    await i.response.send_message("🎧 تعطيل")

@bot.tree.command(name="undeafen" description="تفعيل سماع")
async def undeafen(i member: discord.Member):
    await member.edit(deafen=False)
    await i.response.send_message("👂 تفعيل")

@bot.tree.command(name="unban" description="فك حظر")
async def unban(i user_id: str):
    user = await bot.fetch_user(int(user_id))
    await i.guild.unban(user)
    await i.response.send_message(f"✅ فك حظر {user.name}")

if __name__ == '__main__': keep_alive() bot.run(RadarConfig.TOKEN)
