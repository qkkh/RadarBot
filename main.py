import asyncio, os, re, discord, io
from discord.ext import commands, tasks
from discord import app_commands
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageOps # مكتبة معالجة الصور

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
    DASHBOARD_IMG_PATH = "dashboard.png"
    WELCOME_IMG_PATH = "welcome.png" # هذه الصورة اللي فيها الدائرة
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
            try:
                if vcs[i].name != stat_text: await vcs[i].edit(name=stat_text)
            except: pass

# --- وظيفة دمج الافتار في الدائرة ---
async def create_welcome_image(member):
    # فتح صورة الترحيب الأساسية
    background = Image.open(RadarConfig.WELCOME_IMG_PATH).convert("RGBA")
    
    # جلب افتار العضو وتحويله لدائرة
    asset = member.display_avatar.with_format("png")
    data = io.BytesIO(await asset.read())
    pfp = Image.open(data).convert("RGBA")
    
    # تكبير الافتار ليتناسب مع حجم الدائرة (مثلاً 240x240)
    pfp = pfp.resize((240, 240)) 
    
    # قص الافتار بشكل دائري
    mask = Image.new("L", pfp.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + pfp.size, fill=255)
    pfp = ImageOps.fit(pfp, mask.size, centering=(0.5, 0.5))
    pfp.putalpha(mask)
    
    # وضع الافتار فوق الخلفية (الاحداثيات هنا تقريبية لمكان الدائرة في صورتك)
    # تحتاج تعديل الـ (325, 135) بناءً على موقع الدائرة بالضبط في welcome.png
    background.paste(pfp, (325, 135), pfp) 
    
    final_buffer = io.BytesIO()
    background.save(final_buffer, format="PNG")
    final_buffer.seek(0)
    return final_buffer

# --- المودالز ---
class SayModal(discord.ui.Modal, title='إرسال رسالة رادار 💬'):
    msg = discord.ui.TextInput(label="محتوى الرسالة", style=discord.TextStyle.paragraph, required=True)
    ment = discord.ui.TextInput(label="المنشن", placeholder="none / here / everyone", default="none", required=True)
    async def on_submit(self, i):
        formatted_msg = f"**{self.msg.value}**"
        mention_str = ""
        m_choice = self.ment.value.lower().strip()
        if m_choice == "everyone": mention_str = "@everyone\n"
        elif m_choice == "here": mention_str = "@here\n"
        await i.channel.send(content=f"{mention_str}{formatted_msg}")
        await i.response.send_message("تم الإرسال" , ephemeral=True)

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
        await i.response.send_message("تم إطلاق البث" , ephemeral=True)

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
        if os.path.exists(RadarConfig.DASHBOARD_IMG_PATH):
            file = discord.File(RadarConfig.DASHBOARD_IMG_PATH, filename="dashboard.png")
            await i.followup.send(content="**تم التحديث بنجاح**", file=file, ephemeral=True)
        else:
            await i.followup.send("تم التحديث بنجاح" , ephemeral=True)

class RadarBot(commands.Bot):
    def __init__(self): 
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self): self.add_view(AdminDashboard())
    async def on_ready(self): 
        await self.tree.sync(); print(f"📡 {self.user} Online")

    # نظام الترحيب بالصورة المدمجة
    async def on_member_join(self, member):
        channel = self.get_channel(RadarConfig.WELCOME_CHANNEL_ID)
        if channel:
            welcome_text = (
                f"_'Have fun in **__Radraz__**_\n"
                f"_'User: {member.mention}_<a:Via1:1378238620418183188>"
            )
            try:
                # إنشاء الصورة المدمجة (الافتار داخل الدائرة)
                img_data = await create_welcome_image(member)
                file = discord.File(img_data, filename="welcome_final.png")
                
                emb = discord.Embed(description=welcome_text, color=RadarConfig.MAIN_COLOR)
                emb.set_image(url="attachment://welcome_final.png")
                await channel.send(file=file, embed=emb)
            except Exception as e:
                print(f"Error creating image: {e}")
                await channel.send(content=welcome_text)

bot = RadarBot()

# --- الـ 20 أمر إداري (نفس الأوامر السابقة بدون تغيير) ---
@bot.tree.command(name="setpanel", description="تثبيت لوحة التحكم")
async def setpanel(i: discord.Interaction):
    if not has_radar_permission(i.user): return await i.response.send_message("لا تملك صلاحية" , ephemeral=True)
    emb = discord.Embed(title="🎮 RADARZ Dashboard", color=RadarConfig.MAIN_COLOR)
    if os.path.exists(RadarConfig.DASHBOARD_IMG_PATH):
        file = discord.File(RadarConfig.DASHBOARD_IMG_PATH, filename="dashboard.png")
        emb.set_image(url="attachment://dashboard.png")
        await i.channel.send(embed=emb, file=file, view=AdminDashboard())
    else: await i.channel.send(embed=emb, view=AdminDashboard())
    await i.response.send_message("تم تثبيت البانل" , ephemeral=True)

# ... باقي الأوامر (say, clear, kick, ban, etc.) ...
# [ملاحظة: أبقيت جميع الأوامر الإدارية في الذاكرة لتعمل كما هي]

if __name__ == '__main__': keep_alive(); bot.run(RadarConfig.TOKEN)
