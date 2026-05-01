import asyncio, os, re, discord, io
from discord.ext import commands, tasks
from discord import app_commands
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

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
    # رابط صورة الداشبورد (تأكد من رفع الصورة بنفس الاسم dashboard.png في ملفات البوت)
    DASHBOARD_IMG_PATH = "dashboard.png"
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

# --- الداشبورد ---
class AdminDashboard(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @discord.ui.button(label="إطلاق بث 🚀", style=discord.ButtonStyle.danger, custom_id="btn_stream")
    async def st(self, i, b): 
        # يمكنك إضافة المودال الخاص بالبث هنا
        await i.response.send_message("قريباً", ephemeral=True)

    @discord.ui.button(label="تحديث الإحصائيات 🔄", style=discord.ButtonStyle.secondary, custom_id="btn_refresh")
    async def r(self, i, b):
        await i.response.defer(ephemeral=True)
        await refresh_radar_stats(i.guild)
        # إرسال الصورة بدلاً من كلمة "تم التحديث"
        if os.path.exists(RadarConfig.DASHBOARD_IMG_PATH):
            file = discord.File(RadarConfig.DASHBOARD_IMG_PATH, filename="dashboard.png")
            await i.followup.send(file=file, ephemeral=True)
        else:
            await i.followup.send("تم التحديث بنجاح", ephemeral=True)

class RadarBot(commands.Bot):
    def __init__(self): 
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
    
    async def setup_hook(self): 
        self.add_view(AdminDashboard())
        
    async def on_ready(self): 
        await self.tree.sync(); print(f"📡 {self.user} Online")

    async def on_member_join(self, member):
        channel = self.get_channel(RadarConfig.WELCOME_CHANNEL_ID)
        if channel:
            welcome_msg = (
                f"_'Have fun in **__Radarz__**_\n"
                f"_'User: {member.mention}_<a:Via1:1378238620418183188>"
            )
            await channel.send(content=welcome_msg)

bot = RadarBot()

# --- أوامر السلاش ---

@bot.tree.command(name="setpanel", description="تثبيت لوحة التحكم")
async def setpanel(i: discord.Interaction):
    if not has_radar_permission(i.user): return await i.response.send_message("لا تملك صلاحية" , ephemeral=True)
    await i.response.defer(ephemeral=True)
    
    emb = discord.Embed(
        title="🎮 RADARZ Dashboard", 
        description="لوحة التحكم الدائمة للمسؤولين", 
        color=RadarConfig.MAIN_COLOR
    )
    
    # محاولة إرفاق صورة الداشبورد مع البانل الأساسي
    if os.path.exists(RadarConfig.DASHBOARD_IMG_PATH):
        file = discord.File(RadarConfig.DASHBOARD_IMG_PATH, filename="dashboard.png")
        emb.set_image(url="attachment://dashboard.png")
        await i.channel.send(embed=emb, file=file, view=AdminDashboard())
    else:
        await i.channel.send(embed=emb, view=AdminDashboard())
        
    await i.followup.send("تم تثبيت البانل بنجاح")

@bot.tree.command(name="say", description="إرسال رسالة عريضة")
async def say(i: discord.Interaction):
    if not has_radar_permission(i.user): return await i.response.send_message("لا تملك صلاحية" , ephemeral=True)
    await i.response.send_modal(SayModal())

@bot.tree.command(name="clear", description="مسح الرسائل")
async def clear(i: discord.Interaction, amount: int):
    if not i.user.guild_permissions.manage_messages: return await i.response.send_message("صلاحيات ناقصة" , ephemeral=True)
    await i.response.defer(ephemeral=True)
    await i.channel.purge(limit=amount)
    # ملاحظة: تم حذف رسالة التأكيد ليبقى الشات نظيفاً كما طلبت

if __name__ == '__main__': keep_alive(); bot.run(RadarConfig.TOKEN)
