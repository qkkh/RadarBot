import asyncio, os, re, discord, io
from discord.ext import commands, tasks
from discord import app_commands
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageOps

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
    LOGS_ROOM_ID = 1498422633669197904 
    WELCOME_CHANNEL_ID = 924274202872266785
    DASHBOARD_ROOM_ID = 1494618976498483261
    ALLOWED_ROLES = [1377997626938753114, 1494645555865976872, 1498095128122884236]

def has_radar_permission(member):
    if member.guild_permissions.administrator: return True
    return any(role.id in RadarConfig.ALLOWED_ROLES for role in member.roles)

# --- نظام الإحصائيات الذكي ---
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
        else:
            await guild.create_voice_channel(stat_text, category=cat, overwrites={guild.default_role: discord.PermissionOverwrite(connect=False)})

# --- نظام الترحيب المعدل ---
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

# --- المودالز الأساسية ---
class SayModal(discord.ui.Modal, title='رسالة 📝'):
    m = discord.ui.TextInput(label="المحتوى", style=discord.TextStyle.paragraph)
    n = discord.ui.TextInput(label="المنشن", default="none")
    async def on_submit(self, i):
        c = f"@{self.n.value}" if self.n.value.lower() in ['everyone', 'here'] else ""
        await i.channel.send(content=f"{c}\n**{self.m.value}**"); await i.response.send_message("✅ تم", ephemeral=True)

class YoutubeModal(discord.ui.Modal, title='فيديو جديد 🎬'):
    l = discord.ui.TextInput(label="الرابط"); m = discord.ui.TextInput(label="المنشن", default="everyone")
    async def on_submit(self, i):
        ch = i.guild.get_channel(RadarConfig.YOUTUBE_CHANNEL_ID)
        if ch: await ch.send(content=f"📣 @{self.m.value} فيديو جديد!\n{self.l.value}")
        await i.response.send_message("✅ تم النشر", ephemeral=True)

# --- الداشبورد ---
class AdminDashboard(discord.ui.View):
    def __init__(self, bot): super().__init__(timeout=None); self.bot = bot
    @discord.ui.button(label="إرسال رسالة 📝", style=discord.ButtonStyle.success, row=0)
    async def s(self, i, b): await i.response.send_modal(SayModal())
    @discord.ui.button(label="يوتيوب 🎬", style=discord.ButtonStyle.primary, row=0)
    async def y(self, i, b): await i.response.send_modal(YoutubeModal())
    @discord.ui.button(label="تحديث الإحصائيات 🔄", style=discord.ButtonStyle.secondary, row=1)
    async def r(self, i, b):
        await i.response.defer(ephemeral=True)
        await refresh_radar_stats(i.guild)
        await i.followup.send("✅ تم التحديث", ephemeral=True)

class RadarBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self): self.auto_refresh_stats.start()
    async def on_ready(self): 
        await self.tree.sync(); print(f"📡 {self.user} Online")
    @tasks.loop(minutes=10)
    async def auto_refresh_stats(self):
        for g in self.guilds: await refresh_radar_stats(g)
    async def on_member_join(self, member):
        ch = self.get_channel(RadarConfig.WELCOME_CHANNEL_ID)
        if ch:
            file = await create_welcome_card(member)
            msg = (f"_'Have fun in **__Radarz__**_\n"
                   f"_'User: {member.mention}_<a:Via1:1378238620418183188>")
            await ch.send(content=msg, file=file) if file else await ch.send(content=msg)

bot = RadarBot()

# --- نظام أوامر السلاش (أهم الأوامر) ---
@bot.tree.command(name="panel", description="لوحة التحكم")
async def panel(i):
    if has_radar_permission(i.user):
        emb = discord.Embed(title="🎮 RADARZ Dashboard", color=RadarConfig.MAIN_COLOR)
        try:
            file = discord.File("dashboard.png", filename="dashboard.png")
            emb.set_image(url="attachment://dashboard.png")
            await i.response.send_message(file=file, embed=emb, view=AdminDashboard(bot), ephemeral=True)
        except: await i.response.send_message(embed=emb, view=AdminDashboard(bot), ephemeral=True)
    else: await i.response.send_message("❌ لا تملك صلاحية", ephemeral=True)

@bot.tree.command(name="clear", description="مسح الرسائل")
@app_commands.describe(amount="عدد الرسائل")
async def clear(i: discord.Interaction, amount: int):
    if i.user.guild_permissions.manage_messages:
        await i.response.defer(ephemeral=True)
        deleted = await i.channel.purge(limit=amount)
        await i.followup.send(f"✅ تم مسح {len(deleted)} رسالة")
    else: await i.response.send_message("❌ لا تملك صلاحية", ephemeral=True)

@bot.tree.command(name="user_info", description="معلومات العضو")
async def user_info(i: discord.Interaction, member: discord.Member = None):
    member = member or i.user
    emb = discord.Embed(title=f"👤 {member}", color=member.color)
    emb.set_thumbnail(url=member.display_avatar.url)
    emb.add_field(name="ID", value=member.id)
    emb.add_field(name="انضم للسيرفر", value=member.joined_at.strftime("%Y/%m/%d"))
    await i.response.send_message(embed=emb)

@bot.tree.command(name="server_info", description="معلومات السيرفر")
async def server_info(i: discord.Interaction):
    g = i.guild
    emb = discord.Embed(title=f"🏰 {g.name}", color=RadarConfig.MAIN_COLOR)
    emb.add_field(name="الأعضاء", value=g.member_count)
    emb.add_field(name="الرتب", value=len(g.roles))
    emb.set_thumbnail(url=g.icon.url if g.icon else None)
    await i.response.send_message(embed=emb)

@bot.tree.command(name="avatar", description="عرض صورة العضو")
async def avatar(i: discord.Interaction, member: discord.Member = None):
    member = member or i.user
    await i.response.send_message(member.display_avatar.url)

@bot.tree.command(name="lock", description="قفل الروم")
async def lock(i: discord.Interaction):
    if i.user.guild_permissions.manage_channels:
        await i.channel.set_permissions(i.guild.default_role, send_messages=False)
        await i.response.send_message("🔒 تم قفل الروم بنجاح")
    else: await i.response.send_message("❌ لا تملك صلاحية", ephemeral=True)

@bot.tree.command(name="unlock", description="فتح الروم")
async def unlock(i: discord.Interaction):
    if i.user.guild_permissions.manage_channels:
        await i.channel.set_permissions(i.guild.default_role, send_messages=True)
        await i.response.send_message("🔓 تم فتح الروم بنجاح")
    else: await i.response.send_message("❌ لا تملك صلاحية", ephemeral=True)

if __name__ == '__main__': keep_alive(); bot.run(RadarConfig.TOKEN)
