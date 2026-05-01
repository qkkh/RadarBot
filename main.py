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
    ROLE_VIP_ID = 1494645555865976872
    ROLE_STAFF_ID = 1498095128122884236
    WELCOME_BG_URL = "https://i.imgur.com/81b67b.png" # رابط صورة الترحيب

def has_radar_permission(member):
    if member.guild_permissions.administrator: return True
    return any(role.id in RadarConfig.ALLOWED_ROLES for role in member.roles)

# --- نظام الإحصائيات (تعديل الاسم فقط) ---
async def refresh_radar_stats(guild):
    cat = guild.get_channel(RadarConfig.STATS_CATEGORY_ID)
    if not cat: return
    
    online = len([m for m in guild.members if m.status != discord.Status.offline and not m.bot])
    bots = len([m for m in guild.members if m.bot])
    
    stats_data = [
        f"👥 الكل: {guild.member_count}",
        f"🟢 اونلاين: {online}",
        f"🤖 بوتات: {bots}"
    ]
    
    vcs = sorted(cat.voice_channels, key=lambda x: x.position)
    for i, stat_text in enumerate(stats_data):
        if i < len(vcs):
            if vcs[i].name != stat_text:
                await vcs[i].edit(name=stat_text)
        else:
            await guild.create_voice_channel(stat_text, category=cat, overwrites={guild.default_role: discord.PermissionOverwrite(connect=False)})

# --- معالجة صورة الترحيب ---
async def create_welcome_card(member):
    # تحميل الخلفية
    bg_bytes = await member._state.http.get_from_url("https://i.imgur.com/81b67b.png")
    background = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
    
    # تحميل صورة العضو
    pfp_bytes = await member.display_avatar.read()
    pfp = Image.open(io.BytesIO(pfp_bytes)).convert("RGBA")
    pfp = pfp.resize((235, 235)) # مقاس مناسب للدائرة في الصورة
    
    # صنع قناع دائري
    mask = Image.new('L', (235, 235), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, 235, 235), fill=255)
    
    # دمج الصورة
    background.paste(pfp, (135, 33), mask) # الإحداثيات التقريبية للدائرة السوداء
    
    buf = io.BytesIO()
    background.save(buf, format='PNG')
    buf.seek(0)
    return discord.File(buf, filename='welcome_radarz.png')

# --- الأجزاء الأصلية (ممنوع اللمس) ---
# [أزرار البث المباشر StreamButtons كما هي في كودك]
# [المودالز StreamModal, YoutubeModal, SayModal كما هي في كودك]

class AdminDashboard(discord.ui.View):
    def __init__(self, bot): super().__init__(timeout=None); self.bot = bot
    @discord.ui.button(label="طرد 👞", style=discord.ButtonStyle.danger, row=0)
    async def k(self, i, b): await i.response.send_modal(KickModal())
    @discord.ui.button(label="تايم أوت ⏳", style=discord.ButtonStyle.secondary, row=0)
    async def t(self, i, b): await i.response.send_modal(TimeoutModal())
    @discord.ui.button(label="إرسال رسالة 📝", style=discord.ButtonStyle.success, row=1)
    async def s(self, i, b): await i.response.send_modal(SayModal())
    @discord.ui.button(label="إطلاق بث 🚀", style=discord.ButtonStyle.danger, row=1)
    async def st(self, i, b): await i.response.send_modal(StreamModal())
    @discord.ui.button(label="يوتيوب 🎬", style=discord.ButtonStyle.primary, row=2)
    async def y(self, i, b): await i.response.send_modal(YoutubeModal())
    @discord.ui.button(label="تحديث الإحصائيات 🔄", style=discord.ButtonStyle.secondary, row=2)
    async def r(self, i, b):
        await i.response.defer(ephemeral=True)
        await refresh_radar_stats(i.guild)
        await i.followup.send("✅ تم تحديث الإحصائيات بنجاح", ephemeral=True)

class RadarBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self): self.auto_refresh_stats.start()
    async def on_ready(self): 
        await self.tree.sync()
        print(f"📡 {self.user} Online")

    @tasks.loop(minutes=10)
    async def auto_refresh_stats(self):
        for g in self.guilds: await refresh_radar_stats(g)

    async def on_member_join(self, member):
        ch = member.guild.get_channel(RadarConfig.WELCOME_CHANNEL_ID)
        if ch:
            file = await create_welcome_card(member)
            msg = (f"_'Have fun in **__Radarz __**_\n"
                   f"_'User: {member.mention}_<a:Via1:1378238620418183188>")
            await ch.send(content=msg, file=file)

@bot.command()
async def setup_dashboard(ctx):
    if not ctx.author.guild_permissions.administrator: return
    emb = discord.Embed(title="🎮 مركز تحكم الرادار", description="لوحة التحكم بجميع أوامر السيرفر متاحة الآن للإدارة المصرح لها", color=RadarConfig.MAIN_COLOR)
    emb.set_image(url="https://i.imgur.com/81b67b.png") # صورة الداشبورد
    await ctx.send(embed=emb, view=AdminDashboard(bot))

if __name__ == '__main__': keep_alive(); bot.run(RadarConfig.TOKEN)
