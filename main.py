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

# --- نظام الإحصائيات المطور (تعديل الاسم فقط) ---
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

# --- نظام الترحيب ---
async def create_welcome_card(member):
    try:
        background = Image.open("welcome.png").convert("RGBA")
        pfp_bytes = await member.display_avatar.read()
        pfp = Image.open(io.BytesIO(pfp_bytes)).convert("RGBA")
        pfp = pfp.resize((235, 235))
        mask = Image.new('L', (235, 235), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 235, 235), fill=255)
        background.paste(pfp, (135, 33), mask)
        buf = io.BytesIO()
        background.save(buf, format='PNG')
        buf.seek(0)
        return discord.File(buf, filename='welcome_radarz.png')
    except: return None

# --- المودالز الأصلية ---
class KickModal(discord.ui.Modal, title='طرد عضو 👞'):
    u = discord.ui.TextInput(label="ID العضو")
    r = discord.ui.TextInput(label="السبب", required=False)
    async def on_submit(self, i):
        await i.response.defer(ephemeral=True)
        try:
            m = await i.guild.fetch_member(int(self.u.value))
            await m.kick(reason=self.r.value)
            await i.followup.send(f"✅ تم طرد {m.display_name}")
        except: await i.followup.send("❌ فشل الطرد")

class TimeoutModal(discord.ui.Modal, title='تايم أوت ⏳'):
    u = discord.ui.TextInput(label="ID العضو"); d = discord.ui.TextInput(label="المدة بالدقائق", default="10")
    async def on_submit(self, i):
        try:
            m = await i.guild.fetch_member(int(self.u.value))
            await m.timeout(timedelta(minutes=int(self.d.value)))
            await i.response.send_message(f"✅ تم سجن {m.display_name}", ephemeral=True)
        except: await i.response.send_message("❌ فشل الإجراء", ephemeral=True)

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

class StreamModal(discord.ui.Modal, title='إشارة بث 📡'):
    t = discord.ui.TextInput(label="العنوان"); ti = discord.ui.TextInput(label="بعد كم دقيقة؟"); l = discord.ui.TextInput(label="الرابط")
    async def on_submit(self, i):
        ts = int((datetime.now() + timedelta(minutes=int(self.ti.value))).timestamp())
        v_id = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", self.l.value)
        thumb = f"https://img.youtube.com/vi/{v_id.group(1)}/maxresdefault.jpg" if v_id else ""
        emb = discord.Embed(title=f"🚨 إشارة بث: {self.t.value}", color=discord.Color.red())
        emb.add_field(name="⏳ الانطلاق:", value=f"<t:{ts}:R>"); emb.add_field(name="🗓️ الموعد:", value=f"<t:{ts}:F>"); emb.add_field(name="📡 المكتشفين", value="✅ 0 | ❌ 0", inline=False)
        if thumb: emb.set_image(url=thumb)
        ch = i.guild.get_channel(RadarConfig.STREAM_CHANNEL_ID)
        await ch.send(content="@everyone !إرصدنا إشارة بث جديدة", embed=emb, view=StreamButtons(self.l.value))
        await i.response.send_message("✅ تم الإطلاق", ephemeral=True)

class YoutubeModal(discord.ui.Modal, title='فيديو جديد 🎬'):
    l = discord.ui.TextInput(label="الرابط"); m = discord.ui.TextInput(label="المنشن", default="everyone")
    async def on_submit(self, i):
        ch = i.guild.get_channel(RadarConfig.YOUTUBE_CHANNEL_ID)
        if ch: await ch.send(content=f"📣 @{self.m.value} فيديو جديد!\n{self.l.value}")
        await i.response.send_message("✅ تم النشر", ephemeral=True)

class SayModal(discord.ui.Modal, title='رسالة 📝'):
    m = discord.ui.TextInput(label="المحتوى", style=discord.TextStyle.paragraph); n = discord.ui.TextInput(label="المنشن", default="none")
    async def on_submit(self, i):
        c = f"@{self.n.value}" if self.n.value.lower() in ['everyone', 'here'] else ""
        await i.channel.send(content=f"{c}\n**{self.m.value}**"); await i.response.send_message("✅ تم", ephemeral=True)

# --- لوحة التحكم ---
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
        await i.followup.send("✅ تم تحديث الإحصائيات", ephemeral=True)

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
        ch = self.get_channel(RadarConfig.WELCOME_CHANNEL_ID)
        if ch:
            file = await create_welcome_card(member)
            msg = (f"_'Have fun in **__Radarz __**_\n"
                   f"_'User: {member.mention}_<a:Via1:1378238620418183188>")
            await ch.send(content=msg, file=file) if file else await ch.send(content=msg)
    async def on_message_delete(self, m):
        if m.author.bot: return
        log = self.get_channel(RadarConfig.LOGS_ROOM_ID)
        if log:
            emb = discord.Embed(title="🗑️ رسالة محذوفة", color=discord.Color.red(), timestamp=datetime.now())
            emb.add_field(name="الكاتب", value=m.author.mention); emb.add_field(name="المحتوى", value=m.content or "ملف")
            await log.send(embed=emb)

bot = RadarBot()

@bot.tree.command(name="panel", description="لوحة التحكم")
async def panel(i):
    if has_radar_permission(i.user):
        await i.response.send_message(embed=discord.Embed(title="🎮 RADARZ Panel", color=RadarConfig.MAIN_COLOR), view=AdminDashboard(bot), ephemeral=True)
    else: await i.response.send_message("❌ لا تملك صلاحية", ephemeral=True)

@bot.command()
async def setup_dashboard(ctx):
    if not ctx.author.guild_permissions.administrator: return
    emb = discord.Embed(title="🎮 مركز تحكم الرادار", description="لوحة التحكم بجميع أوامر السيرفر متاحة الآن للإدارة", color=RadarConfig.MAIN_COLOR)
    try:
        file = discord.File("dashboard.png", filename="dashboard.png")
        emb.set_image(url="attachment://dashboard.png")
        await ctx.send(file=file, embed=emb, view=AdminDashboard(bot))
    except: await ctx.send(embed=emb, view=AdminDashboard(bot))

if __name__ == '__main__': keep_alive(); bot.run(RadarConfig.TOKEN)
