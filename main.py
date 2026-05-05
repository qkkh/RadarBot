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
def home(): return "RADARZ Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run); t.daemon = True; t.start()

# --- الإعدادات ---
أبشر يا Phoenix عدلت لك الإحداثيات (Coordinates)class RadarConfig:
    TOKEN = os.getenv('DISCORD_TOKEN')
    MAIN_COLOR = discord.Color.red()
    STREAM_CHANNEL_ID بالضبط لتكون الصورة أكبر ومزاحة لليمين لتتوسط الدائرة تماماً وحدثت رس = 1200740059817721856
    YOUTUBE_CHANNEL_ID = 9243الة الترحيب بنفس التنسيق والمحتوى اللي طلبته16521050820609
    STATS_CATEGORY_ID = 1494627032112 مع الحفاظ على كل الأوامر الإدارية العشرين وال304179 
    WELCOME_CHANNEL_ID = 924274202872266785
    داشبورد وكافة وظائف الكود الأساسي بدون أي تغيير آخرVERIFY_ROLE_ID = 1377890014964482048 
    VERIFY_MSG_ID

إليك الكود المحدث بالكامل وجاهز للنسخ:
```python
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
    VERIFY_ROLE_ID = 1377890014964482048 
    VERIFY_MSG_ID = 1501027535386054756   
    DASHBOARD_IMG_PATH = "dashboard.png"
    WELCOME_IMG_PATH = "welcome.png"
    ALLOWED_ROLES = [1377997626938753114, 1494645555865976872, 1498095128122884236]

def has_radar_permission(member):
    if member.guild_permissions.administrator: return True
    return any(role.id in RadarConfig.ALLOWED_ROLES for role in member.roles)

# --- معالجة صورة الترحيب الموزونة (تكبير + إزاحة لليمين لتتوسط الدائرة) ---
async def create_welcome_image(member):
    background = Image.open(RadarConfig.WELCOME_IMG_PATH).convert("RGBA")
    asset = member.display_avatar.with_format("png")
    data = io.BytesIO(await asset.read())
    pfp = Image.open(data).convert("RGBA")
    
    # تكبير الافتار ليكون أوضح ومتناسب مع الدائرة
    pfp_size = (330, 330)
    pfp = pfp.resize(pfp_size) 
    
    mask = Image.new("L", pfp_size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + pfp_size, fill=255)
    pfp.putalpha(mask)
    
    # الإحداثيات الموزونة: 215 (يمين) | 200 (تحت) لتلائم نص الدائرة تماماً
    background.paste(pfp, (215, 200), pfp) 
    
    final_buffer = io.BytesIO()
    background.save(final_buffer, format="PNG")
    final_buffer.seek(0)
    return final_buffer

# --- المودالز ---
class SayModal(discord.ui.Modal, title='إرسال رسالة رادار 💬'):
    msg = discord.ui.TextInput(label="محتوى الرسالة", style=discord.TextStyle.paragraph, required=True)
    ment = discord.ui.TextInput(label="المنشن", placeholder="none / here / everyone", default="none", required=True)
    async def on_submit(self, i):
        mention_str = ""
        m_choice = self.ment.value.lower().strip()
        if m_choice == "everyone": mention_str = "@everyone\n"
        elif m_choice == "here": mention_str = "@here\n"
        await i.channel.send(content=f"{mention_str}**{self.msg.value}**")
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
        await i.followup.send("تم طلب تحديث الإحصائيات" , ephemeral=True)

class RadarBot(commands.Bot):
    def __init__(self): 
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self): self.add_view(AdminDashboard())
    async def on_ready(self): 
        await self.tree.sync(); print(f"📡 {self.user} Online")

    async def on_member_join(self, member):
        channel = self.get_channel(RadarConfig.WELCOME_CHANNEL_ID)
        if channel:
            # رسالة الترحيب المحدثة كما طلبت بالضبط
            welcome_msg = (
                f"_'Have fun in **__Radarz __**_\n"
                f"     _'User: {member.mention}_<a:Via1:1378238620418183188>"
            )
            try:
                img_data = await create_welcome_image(member)
                file = discord.File(img_data, filename="welcome.png")
                await channel.send(content=welcome_msg, file=file)
            except:
                await channel.send(content=welcome_msg)

    async def on_raw_reaction_add(self, payload):
        if payload.message_id == RadarConfig.VERIFY_MSG_ID:
            guild = self.get_guild(payload.guild_id)
            role = guild.get_role(RadarConfig.VERIFY_ROLE_ID)
            member = guild.get_member(payload.user_id)
            if member and not member.bot and role:
                try: await member.add_roles(role)
                except: pass

bot = RadarBot()

# --- قائمة الأوامر الإدارية الـ 20 ---
@bot.tree.command(name="say", description="إرسال رسالة")
async def say(i: discord.Interaction):
    if not has_radar_permission(i.user): return await i.response.send_message("صلاحية ناقصة" , ephemeral=True)
    await i.response.send_modal(SayModal())

@bot.tree.command(name="clear", description="مسح شات")
async def clear(i: discord.Interaction, amount: int):
    if not i.user.guild_permissions.manage_messages: return await i.response.send_message("صلاحية ناقصة" , ephemeral=True)
    await i.response.defer(ephemeral=True)
    await i.channel.purge(limit=amount)
    await i.followup.send(f"تم مسح {amount} رسالة" , ephemeral=True)

@bot.tree.command(name="kick", description="طرد عضو")
async def kick(i: discord.Interaction, member: discord.Member):
    if not i.user.guild_permissions.kick_members: return await i.response.send_message("صلاحية ناقصة" , ephemeral=True)
    await member.kick(); await i.response.send_message(f"تم طرد {member.name}")

@bot.tree.command(name="ban", description="حظر عضو")
async def ban(i: discord.Interaction, member: discord.Member):
    if not i.user.guild_permissions.ban_members: return await i.response.send_message("صلاحية ناقصة" , ephemeral=True)
    await member.ban(); await i.response.send_message(f"تم حظر {member.name}")

@bot.tree.command(name="mute", description="كتم عضو")
async def mute(i: discord.Interaction, member: discord.Member, minutes: int):
    if not i.user.guild_permissions.moderate_members: return await i.response.send_message("صلاحية ناقصة" , ephemeral=True)
    await member.timeout(timedelta(minutes=minutes)); await i.response.send_message(f"تم كتم {member.name}")

@bot.tree.command(name="unmute", description="فك كتم")
async def unmute(i: discord.Interaction, member: discord.Member):
    await member.timeout(None); await i.response.send_message(f"تم فك كتم {member.name}")

@bot.tree.command(name="lock", description="قفل روم")
async def lock(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("الروم مقفل")

@bot.tree.command(name="unlock", description="فتح روم")
async def unlock(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("الروم مفتوح")

@bot.tree.command(name="hide", description="إخفاء روم")
async def hide(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("الروم مخفي")

@bot.tree.command(name="show", description="إظهار روم")
async def show(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, view_channel=True); await i.response.send_message("الروم ظاهر")

@bot.tree.command(name="slowmode", description="وضع بطيء")
async def slowmode(i: discord.Interaction, seconds: int):
    await i.channel.edit(slowmode_delay=seconds); await i.response.send_message(f"الوضع البطيء {seconds}ث")

@bot.tree.command(name="setnick", description="تغيير لقب")
async def setnick(i: discord.Interaction, member: discord.Member, nick: str):
    await member.edit(nick=nick); await i.response.send_message("تم تغيير اللقب")

@bot.tree.command(name="warn", description="تحذير")
async def warn(i: discord.Interaction, member: discord.Member, reason: str):
    await i.response.send_message(f"تحذير لـ {member.mention} السبب {reason}")

@bot.tree.command(name="role_add", description="إضافة رتبة")
async def role_add(i: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.add_roles(role); await i.response.send_message("تمت الإضافة")

@bot.tree.command(name="role_remove", description="إزالة رتبة")
async def role_remove(i: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.remove_roles(role); await i.response.send_message("تمت الإزالة")

@bot.tree.command(name="setpanel", description="لوحة التحكم")
async def setpanel(i: discord.Interaction):
    if not has_radar_permission(i.user): return await i.response.send_message("لا تملك صلاحية" , ephemeral=True)
    emb = discord.Embed(title="🎮 RADARZ Dashboard", color=RadarConfig.MAIN_COLOR)
    await i.channel.send(embed=emb, view=AdminDashboard())
    await i.response.send_message("تم التثبيت" , ephemeral=True)

@bot.tree.command(name="avatar", description="افتار")
async def avatar(i: discord.Interaction, member: discord.Member):
    await i.response.send_message(member.display_avatar.url)

@bot.tree.command(name="ping", description="سرعة البوت")
async def ping(i: discord.Interaction):
    await i.response.send_message(f"البينق {round(bot.latency * 1000)}ms")

@bot.tree.command(```name="server_info", description="بيانات سيرفر")
async def server_info(i: discord.Interaction):
    await i.response.send_message(f"السيرفر {i.guild.name} الأعضاء {i.guild.member_count}")

@bot.tree.command(name="user_info", description="بيانات عضو")
async def user_info(i: discord.Interaction, member: discord.Member):
    await i.response.send_message(f"الاسم {member.name} تاريخ الانضمام {member.joined_at.strftime('%Y-%m-%d')}")

if __name__ == '__main__': keep_alive(); bot.run(RadarConfig.TOKEN)
