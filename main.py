import asyncio, os, re, discord, io
from discord.ext import commands, tasks
from discord import app_commands
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta
from PIL import Image, ImageDraw

# --- نظام الاستضافة ---
app = Flask('')
@app.route('/')
def home(): return "RADARZ Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run); t.daemon = True; t.start()

# --- الإعدادات ---
class RadarConfig:
    TOKEN = os.getenv('DISCORD_TOKEN')
    MAIN_COLOR = discord.Color.red()
    STREAM_CHANNEL_ID = 1200740059817721856
    YOUTUBE_CHANNEL_ID = 924316521050820609
    STATS_CATEGORY_ID = 1494627032112304179 
    WELCOME_CHANNEL_ID = 924274202872266785
    ALLOWED_ROLES = [1377997626938753114, 1494645555865976872, 1498095128122884236]

def has_radar_permission(member):
    if member.guild_permissions.administrator: return True
    return any(role.id in RadarConfig.ALLOWED_ROLES for role in member.roles)

# --- نظام الإحصائيات ---
async def refresh_radar_stats(guild):
    cat = guild.get_channel(RadarConfig.STATS_CATEGORY_ID)
    if not cat: return
    online = len([m for m in guild.members if m.status != discord.Status.offline and not m.bot])
    bots = len([m for m in guild.members if m.bot])
    stats_data = [f"👥 Members {guild.member_count}", f"🟢 Online {online}", f"🤖 Bots {bots}"]
    vcs = sorted(cat.voice_channels, key=lambda x: x.position)
    for i, stat_text in enumerate(stats_data):
        if i < len(vcs):
            if vcs[i].name != stat_text: await vcs[i].edit(name=stat_text)

# --- المودالز ---
class StreamModal(discord.ui.Modal, title='إشارة بث 📡'):
    t = discord.ui.TextInput(label="العنوان")
    ti = discord.ui.TextInput(label="بعد كم دقيقة؟")
    l = discord.ui.TextInput(label="الرابط")
    async def on_submit(self, i):
        ts = int((datetime.now() + timedelta(minutes=int(self.ti.value))).timestamp())
        ch = i.guild.get_channel(RadarConfig.STREAM_CHANNEL_ID)
        emb = discord.Embed(title=f"🚨 إشارة بث {self.t.value}", color=discord.Color.red())
        emb.add_field(name="⏳ الانطلاق", value=f"<t:{ts}:R>")
        await ch.send(content="@everyone رادار البث رصد إشارة جديدة", embed=emb)
        await i.response.send_message("تم الإرسال بنجاح" , ephemeral=True)

class YoutubeModal(discord.ui.Modal, title='فيديو جديد 🎬'):
    l = discord.ui.TextInput(label="الرابط")
    m = discord.ui.TextInput(label="المنشن", default="everyone")
    async def on_submit(self, i):
        ch = i.guild.get_channel(RadarConfig.YOUTUBE_CHANNEL_ID)
        if ch: await ch.send(content=f"📣 @{self.m.value} فيديو جديد\n{self.l.value}")
        await i.response.send_message("تم نشر الفيديو" , ephemeral=True)

# --- الداشبورد ---
class AdminDashboard(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="إطلاق بث 🚀", style=discord.ButtonStyle.danger, custom_id="btn_stream")
    async def st(self, i, b): await i.response.send_modal(StreamModal())
    @discord.ui.button(label="يوتيوب 🎬", style=discord.ButtonStyle.primary, custom_id="btn_yt")
    async def yt(self, i, b): await i.response.send_modal(YoutubeModal())
    @discord.ui.button(label="تحديث الإحصائيات 🔄", style=discord.ButtonStyle.secondary, custom_id="btn_refresh")
    async def r(self, i, b):
        await i.response.defer(ephemeral=True)
        await refresh_radar_stats(i.guild)
        await i.followup.send("تم التحديث")

class RadarBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self): 
        self.auto_refresh_stats.start()
        self.add_view(AdminDashboard())
    async def on_ready(self): 
        await self.tree.sync(); print(f"📡 {self.user} Online")
    @tasks.loop(minutes=10)
    async def auto_refresh_stats(self):
        for g in self.guilds: await refresh_radar_stats(g)

bot = RadarBot()

# --- أوامر السلاش الإدارية ---

@bot.tree.command(name="setpanel", description="تثبيت لوحة التحكم")
async def setpanel(i: discord.Interaction):
    if not has_radar_permission(i.user): return await i.response.send_message("لا تملك صلاحية" , ephemeral=True)
    await i.response.defer(ephemeral=True)
    emb = discord.Embed(title="🎮 RADARZ Dashboard", description="لوحة التحكم الدائمة للمسؤولين", color=RadarConfig.MAIN_COLOR)
    await i.channel.send(embed=emb, view=AdminDashboard())
    await i.followup.send("تم تثبيت البانل")

@bot.tree.command(name="say", description="إرسال رسالة من البوت")
async def say(i: discord.Interaction, message: str, mention: str = None):
    if not has_radar_permission(i.user): return await i.response.send_message("صلاحيات ناقصة" , ephemeral=True)
    await i.channel.send(content=f"@{mention}\n{message}" if mention else message)
    await i.response.send_message("تم الإرسال" , ephemeral=True)

@bot.tree.command(name="clear", description="مسح الرسائل")
async def clear(i: discord.Interaction, amount: int):
    if not i.user.guild_permissions.manage_messages: return await i.response.send_message("لا تملك صلاحية مسح" , ephemeral=True)
    await i.response.defer(ephemeral=True)
    await i.channel.purge(limit=amount)
    await i.followup.send(f"تم مسح {amount} رسالة")

@bot.tree.command(name="lock", description="قفل الروم")
async def lock(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=False)
    await i.response.send_message("تم قفل الروم")

@bot.tree.command(name="unlock", description="فتح الروم")
async def unlock(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=True)
    await i.response.send_message("تم فتح الروم")

@bot.tree.command(name="kick", description="طرد عضو")
async def kick(i: discord.Interaction, member: discord.Member):
    if not i.user.guild_permissions.kick_members: return await i.response.send_message("خطأ في الصلاحيات" , ephemeral=True)
    await member.kick()
    await i.response.send_message(f"تم طرد {member.name}")

@bot.tree.command(name="ban", description="حظر عضو")
async def ban(i: discord.Interaction, member: discord.Member):
    if not i.user.guild_permissions.ban_members: return await i.response.send_message("خطأ في الصلاحيات" , ephemeral=True)
    await member.ban()
    await i.response.send_message(f"تم حظر {member.name}")

@bot.tree.command(name="mute", description="كتم مؤقت")
async def mute(i: discord.Interaction, member: discord.Member, minutes: int):
    await member.timeout(timedelta(minutes=minutes))
    await i.response.send_message(f"تم كتم {member.name} لمدة {minutes} دقيقة")

@bot.tree.command(name="unmute", description="فك الكتم")
async def unmute(i: discord.Interaction, member: discord.Member):
    await member.timeout(None)
    await i.response.send_message(f"تم فك كتم {member.name}")

@bot.tree.command(name="hide", description="إخفاء الروم")
async def hide(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, view_channel=False)
    await i.response.send_message("تم إخفاء الروم")

@bot.tree.command(name="show", description="إظهار الروم")
async def show(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, view_channel=True)
    await i.response.send_message("تم إظهار الروم")

@bot.tree.command(name="slowmode", description="وضع البطيء")
async def slowmode(i: discord.Interaction, seconds: int):
    await i.channel.edit(slowmode_delay=seconds)
    await i.response.send_message(f"تم تفعيل الوضع البطيء {seconds} ثانية")

if __name__ == '__main__': keep_alive(); bot.run(RadarConfig.TOKEN)
