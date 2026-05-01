import asyncio, os, re, discord, io
from discord.ext import commands, tasks
from discord import app_commands
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

# --- نظام الاستضافة (لم يتم لمسه) ---
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

def has_radar_permission(member):
    if member.guild_permissions.administrator: return True
    return any(role.id in RadarConfig.ALLOWED_ROLES for role in member.roles)

# --- نظام الإحصائيات المطور (تحديث الاسم فقط) ---
async def refresh_radar_stats(guild):
    cat = guild.get_channel(RadarConfig.STATS_CATEGORY_ID)
    if not cat: return
    
    online = len([m for m in guild.members if m.status != discord.Status.offline and not m.bot])
    bots = len([m for m in guild.members if m.bot])
    
    stats_data = [
        f"👥 Members: {guild.member_count}",
        f"🟢 online: {online}",
        f"🤖 bots: {bots}"
    ]
    
    vcs = sorted(cat.voice_channels, key=lambda x: x.position)
    
    # تحديث القنوات الموجودة أو إنشاء نواقص
    for i, stat_text in enumerate(stats_data):
        if i < len(vcs):
            if vcs[i].name != stat_text:
                await vcs[i].edit(name=stat_text)
        else:
            await guild.create_voice_channel(stat_text, category=cat, overwrites={guild.default_role: discord.PermissionOverwrite(connect=False)})

# --- نظام الترحيب بالصور ---
async def create_welcome_img(member):
    img = Image.new('RGB', (800, 300), color=(40, 40, 40)) # يمكنك استبدالها بصورة خلفية
    draw = ImageDraw.Draw(img)
    # ملاحظة: يتطلب وجود ملف خط في السيرفر أو استخدام الخط الافتراضي
    draw.text((250, 120), f"Welcome {member.name}", fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return discord.File(buf, filename='welcome.png')

# --- الأجزاء الأصلية (أزرار البث والمودالز - لم يتم لمسها) ---
class StreamButtons(discord.ui.View):
    def __init__(self, link):
        super().__init__(timeout=None)
        self.link = link
        self.going, self.not_going = set(), set()
        self.add_item(discord.ui.Button(label="دخول البث المباشر 🚌", url=self.link))
    def update_embed(self, embed):
        embed.set_field_at(2, name="📡 المكتشفين على الرادار", value=f"✅ {len(self.going)} حاضر | ❌ {len(self.not_going)} غائب", inline=False)
        return embed
    @discord.ui.button(label="سأحضر ✅", style=discord.ButtonStyle.success, custom_id="go_btn")
    async def go(self, i, b):
        self.going.add(i.user.id); self.not_going.discard(i.user.id)
        await i.message.edit(embed=self.update_embed(i.message.embeds[0]))
        await i.response.send_message("تم تسجيل حضورك!", ephemeral=True)
    @discord.ui.button(label="لن أحضر ❌", style=discord.ButtonStyle.danger, custom_id="no_btn")
    async def no(self, i, b):
        self.not_going.add(i.user.id); self.going.discard(i.user.id)
        await i.message.edit(embed=self.update_embed(i.message.embeds[0]))
        await i.response.send_message("تم تسجيل غيابك", ephemeral=True)

# [هنا تضع كود الـ Modals الخاص بك: KickModal, StreamModal, YoutubeModal, SayModal كما هي بدون تغيير]

# --- لوحة التحكم والداشبورد ---
class AdminDashboard(discord.ui.View):
    def __init__(self, bot): super().__init__(timeout=None); self.bot = bot
    @discord.ui.button(label="طرد 👞", style=discord.ButtonStyle.danger, row=0)
    async def k(self, i, b): await i.response.send_modal(KickModal())
    # ... وبقية الأزرار تتبع نفس النمط السابق ...

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
            file = await create_welcome_img(member)
            await ch.send(f"أطلق إشارة ترحيب لـ {member.mention} نورت الرادار!", file=file)

@bot.command()
async def setup_dashboard(ctx):
    if not ctx.author.guild_permissions.administrator: return
    emb = discord.Embed(title="🎮 مركز تحكم الرادار", description="استخدم الأزرار أدناه لإدارة السيرفر والبثوث", color=RadarConfig.MAIN_COLOR)
    # يمكنك وضع رابط الصورة اللي أرفقتها هنا
    emb.set_image(url="https://example.com/your_dashboard_image.png") 
    await ctx.send(embed=emb, view=AdminDashboard(bot))

if __name__ == '__main__': keep_alive(); bot.run(RadarConfig.TOKEN)
