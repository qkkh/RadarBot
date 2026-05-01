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
def home(): return "RADARZ Operations Online"
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
    stats_data = [f"👥 Members: {guild.member_count}", f"🟢 Online: {online}", f"🤖 Bots: {bots}"]
    vcs = sorted(cat.voice_channels, key=lambda x: x.position)
    for i, stat_text in enumerate(stats_data):
        if i < len(vcs):
            if vcs[i].name != stat_text: await vcs[i].edit(name=stat_text)

# --- نظام الترحيب ---
async def create_welcome_card(member):
    try:
        background = Image.open("welcome.png").convert("RGBA")
        pfp_bytes = await member.display_avatar.read()
        pfp = Image.open(io.BytesIO(pfp_bytes)).convert("RGBA")
        size = (310, 310) 
        pfp = pfp.resize(size)
        mask = Image.new('L', size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size[0], size[1]), fill=255)
        background.paste(pfp, (132, 235), mask) 
        buf = io.BytesIO()
        background.save(buf, format='PNG')
        buf.seek(0)
        return discord.File(buf, filename='welcome_radarz.png')
    except: return None

# --- المودالز ---
class StreamModal(discord.ui.Modal, title='إشارة بث 📡'):
    t = discord.ui.TextInput(label="العنوان")
    ti = discord.ui.TextInput(label="بعد كم دقيقة؟")
    l = discord.ui.TextInput(label="الرابط")
    async def on_submit(self, i):
        ts = int((datetime.now() + timedelta(minutes=int(self.ti.value))).timestamp())
        ch = i.guild.get_channel(RadarConfig.STREAM_CHANNEL_ID)
        emb = discord.Embed(title=f"🚨 إشارة بث: {self.t.value}", color=discord.Color.red())
        emb.add_field(name="⏳ الانطلاق:", value=f"<t:{ts}:R>")
        await ch.send(content="@everyone رادار البث رصد إشارة جديدة", embed=emb)
        await i.response.send_message("✅ تم الإرسال", ephemeral=True)

class SayModal(discord.ui.Modal, title='رسالة 📝'):
    m = discord.ui.TextInput(label="المحتوى", style=discord.TextStyle.paragraph)
    async def on_submit(self, i):
        await i.channel.send(content=f"**{self.m.value}**")
        await i.response.send_message("✅ تم", ephemeral=True)

# --- الداشبورد الثابتة ---
class AdminDashboard(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="إطلاق بث 🚀", style=discord.ButtonStyle.danger, custom_id="btn_stream")
    async def st(self, i, b): await i.response.send_modal(StreamModal())
    @discord.ui.button(label="إرسال رسالة 📝", style=discord.ButtonStyle.success, custom_id="btn_say")
    async def s(self, i, b): await i.response.send_modal(SayModal())
    @discord.ui.button(label="تحديث الإحصائيات 🔄", style=discord.ButtonStyle.secondary, custom_id="btn_refresh")
    async def r(self, i, b):
        await i.response.defer(ephemeral=True)
        await refresh_radar_stats(i.guild)
        await i.followup.send("✅ تم التحديث")

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
    async def on_member_join(self, member):
        ch = self.get_channel(RadarConfig.WELCOME_CHANNEL_ID)
        if ch:
            file = await create_welcome_card(member)
            msg = f"_'Have fun in **__Radarz__**_\n_'User: {member.mention}_<a:Via1:1378238620418183188>"
            await ch.send(content=msg, file=file)

bot = RadarBot()

# --- أوامر السلاش المعدلة للاستجابة السريعة ---

@bot.tree.command(name="setpanel", description="تثبيت لوحة التحكم في هذا الروم")
async def setpanel(i: discord.Interaction):
    if not has_radar_permission(i.user): return await i.response.send_message("❌ صلاحيات ناقصة", ephemeral=True)
    await i.response.defer(ephemeral=True)
    emb = discord.Embed(title="🎮 RADARZ Dashboard", description="لوحة التحكم الدائمة للمسؤولين", color=RadarConfig.MAIN_COLOR)
    try:
        file = discord.File("dashboard.png", filename="dashboard.png")
        emb.set_image(url="attachment://dashboard.png")
        await i.channel.send(file=file, embed=emb, view=AdminDashboard())
    except: await i.channel.send(embed=emb, view=AdminDashboard())
    await i.followup.send("✅ تم تثبيت البانل")

@bot.tree.command(name="clear", description="مسح الرسائل")
async def clear(i: discord.Interaction, amount: int):
    if not i.user.guild_permissions.manage_messages: return await i.response.send_message("❌", ephemeral=True)
    await i.response.defer(ephemeral=True)
    await i.channel.purge(limit=amount)
    await i.followup.send(f"✅ تم مسح {amount}")

@bot.tree.command(name="lock", description="قفل الروم")
async def lock(i: discord.Interaction):
    await i.response.defer(ephemeral=True)
    await i.channel.set_permissions(i.guild.default_role, send_messages=False)
    await i.followup.send("🔒 تم القفل")

@bot.tree.command(name="unlock", description="فتح الروم")
async def unlock(i: discord.Interaction):
    await i.response.defer(ephemeral=True)
    await i.channel.set_permissions(i.guild.default_role, send_messages=True)
    await i.followup.send("🔓 تم الفتح")

@bot.tree.command(name="mute", description="كتم عضو")
async def mute(i: discord.Interaction, member: discord.Member, minutes: int):
    await i.response.defer(ephemeral=True)
    await member.timeout(timedelta(minutes=minutes))
    await i.followup.send(f"🔇 كتم {member.name}")

@bot.tree.command(name="unmute", description="فك كتم")
async def unmute(i: discord.Interaction, member: discord.Member):
    await i.response.defer(ephemeral=True)
    await member.timeout(None)
    await i.followup.send(f"🔊 فك كتم {member.name}")

if __name__ == '__main__': keep_alive(); bot.run(RadarConfig.TOKEN)
