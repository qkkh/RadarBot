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

# --- نظام الإحصائيات (Members, Online, Bots) ---
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

# --- المودالز والأنظمة التفاعلية ---
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
    t = discord.ui.TextInput(label="العنوان")
    ti = discord.ui.TextInput(label="بعد كم دقيقة؟")
    l = discord.ui.TextInput(label="الرابط")
    async def on_submit(self, i):
        ts = int((datetime.now() + timedelta(minutes=int(self.ti.value))).timestamp())
        ch = i.guild.get_channel(RadarConfig.STREAM_CHANNEL_ID)
        emb = discord.Embed(title=f"🚨 إشارة بث: {self.t.value}", color=discord.Color.red())
        emb.add_field(name="⏳ الانطلاق:", value=f"<t:{ts}:R>")
        emb.add_field(name="🗓️ الموعد:", value=f"<t:{ts}:F>")
        emb.add_field(name="📡 المكتشفين", value="✅ 0 | ❌ 0", inline=False)
        await ch.send(content="@everyone !إرصدنا إشارة بث جديدة", embed=emb, view=StreamButtons(self.l.value))
        await i.response.send_message("✅ تم الإطلاق", ephemeral=True)

class SayModal(discord.ui.Modal, title='رسالة 📝'):
    m = discord.ui.TextInput(label="المحتوى", style=discord.TextStyle.paragraph)
    n = discord.ui.TextInput(label="المنشن", default="none")
    async def on_submit(self, i):
        c = f"@{self.n.value}" if self.n.value.lower() in ['everyone', 'here'] else ""
        await i.channel.send(content=f"{c}\n**{self.m.value}**")
        await i.response.send_message("✅ تم", ephemeral=True)

class YoutubeModal(discord.ui.Modal, title='فيديو جديد 🎬'):
    l = discord.ui.TextInput(label="الرابط"); m = discord.ui.TextInput(label="المنشن", default="everyone")
    async def on_submit(self, i):
        ch = i.guild.get_channel(RadarConfig.YOUTUBE_CHANNEL_ID)
        if ch: await ch.send(content=f"📣 @{self.m.value} فيديو جديد!\n{self.l.value}")
        await i.response.send_message("✅ تم النشر", ephemeral=True)

# --- الداشبورد الثابتة ---
class AdminDashboard(discord.ui.View):
    def __init__(self, bot): super().__init__(timeout=None); self.bot = bot
    @discord.ui.button(label="إطلاق بث 🚀", style=discord.ButtonStyle.danger, row=0)
    async def st(self, i, b): await i.response.send_modal(StreamModal())
    @discord.ui.button(label="إرسال رسالة 📝", style=discord.ButtonStyle.success, row=0)
    async def s(self, i, b): await i.response.send_modal(SayModal())
    @discord.ui.button(label="يوتيوب 🎬", style=discord.ButtonStyle.primary, row=1)
    async def y(self, i, b): await i.response.send_modal(YoutubeModal())
    @discord.ui.button(label="تحديث الإحصائيات 🔄", style=discord.ButtonStyle.secondary, row=1)
    async def r(self, i, b):
        await i.response.defer(ephemeral=True)
        await refresh_radar_stats(i.guild)
        await i.followup.send("✅ تم التحديث", ephemeral=True)

class RadarBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self): 
        self.auto_refresh_stats.start()
        self.add_view(AdminDashboard(self)) # لتفعيل الأزرار للأبد
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

# --- أوامر السلاش الإدارية (20 أمر) ---

@bot.tree.command(name="panel", description="إرسال لوحة التحكم الثابتة")
async def panel(i):
    if has_radar_permission(i.user):
        emb = discord.Embed(title="🎮 RADARZ Dashboard", description="لوحة التحكم الدائمة للإدارة", color=RadarConfig.MAIN_COLOR)
        file = discord.File("dashboard.png", filename="dashboard.png")
        emb.set_image(url="attachment://dashboard.png")
        await i.channel.send(file=file, embed=emb, view=AdminDashboard(bot))
        await i.response.send_message("✅ تم إرسال الداشبورد", ephemeral=True)
    else: await i.response.send_message("❌ لا تملك صلاحية", ephemeral=True)

@bot.tree.command(name="lock", description="قفل الروم")
async def lock(i):
    if i.user.guild_permissions.manage_channels:
        await i.channel.set_permissions(i.guild.default_role, send_messages=False)
        await i.response.send_message("🔒 تم قفل الروم")
@bot.tree.command(name="unlock", description="فتح الروم")
async def unlock(i):
    if i.user.guild_permissions.manage_channels:
        await i.channel.set_permissions(i.guild.default_role, send_messages=True)
        await i.response.send_message("🔓 تم فتح الروم")
@bot.tree.command(name="hide", description="إخفاء الروم")
async def hide(i):
    if i.user.guild_permissions.manage_channels:
        await i.channel.set_permissions(i.guild.default_role, view_channel=False)
        await i.response.send_message("👻 تم إخفاء الروم")
@bot.tree.command(name="show", description="إظهار الروم")
async def show(i):
    if i.user.guild_permissions.manage_channels:
        await i.channel.set_permissions(i.guild.default_role, view_channel=True)
        await i.response.send_message("👁️ تم إظهار الروم")
@bot.tree.command(name="kick", description="طرد عضو")
async def kick(i, member: discord.Member, reason: str = "بدون سبب"):
    if i.user.guild_permissions.kick_members:
        await member.kick(reason=reason); await i.response.send_message(f"👞 تم طرد {member.name}")
@bot.tree.command(name="ban", description="حظر عضو")
async def ban(i, member: discord.Member, reason: str = "بدون سبب"):
    if i.user.guild_permissions.ban_members:
        await member.ban(reason=reason); await i.response.send_message(f"🚫 تم حظر {member.name}")
@bot.tree.command(name="mute", description="إسكات عضو (Timeout)")
async def mute(i, member: discord.Member, minutes: int):
    if i.user.guild_permissions.moderate_members:
        await member.timeout(timedelta(minutes=minutes)); await i.response.send_message(f"🙊 تم كتم {member.name} لـ {minutes} دقيقة")
@bot.tree.command(name="unmute", description="فك الكتم")
async def unmute(i, member: discord.Member):
    if i.user.guild_permissions.moderate_members:
        await member.timeout(None); await i.response.send_message(f"🔊 تم فك الكتم عن {member.name}")
@bot.tree.command(name="clear", description="مسح الرسائل")
async def clear(i, amount: int):
    if i.user.guild_permissions.manage_messages:
        await i.channel.purge(limit=amount); await i.response.send_message(f"🧹 تم مسح {amount} رسالة", ephemeral=True)
@bot.tree.command(name="nickname", description="تغيير لقب عضو")
async def nickname(i, member: discord.Member, name: str):
    if i.user.guild_permissions.manage_nicknames:
        await member.edit(nick=name); await i.response.send_message(f"📝 تم تغيير لقب {member.name}")
@bot.tree.command(name="role_add", description="إضافة رتبة لعضو")
async def role_add(i, member: discord.Member, role: discord.Role):
    if i.user.guild_permissions.manage_roles:
        await member.add_roles(role); await i.response.send_message(f"✅ تم إضافة رتبة {role.name} لـ {member.name}")
@bot.tree.command(name="role_remove", description="سحب رتبة من عضو")
async def role_remove(i, member: discord.Member, role: discord.Role):
    if i.user.guild_permissions.manage_roles:
        await member.remove_roles(role); await i.response.send_message(f"❌ تم سحب رتبة {role.name} من {member.name}")
@bot.tree.command(name="slowmode", description="وضع البطيء للروم")
async def slowmode(i, seconds: int):
    if i.user.guild_permissions.manage_channels:
        await i.channel.edit(slowmode_delay=seconds); await i.response.send_message(f"⏳ وضع البطيء: {seconds} ثانية")
@bot.tree.command(name="warn", description="تحذير عضو")
async def warn(i, member: discord.Member, reason: str):
    if has_radar_permission(i.user):
        await i.response.send_message(f"⚠️ تحذير لـ {member.mention}: {reason}")
@bot.tree.command(name="move", description="نقل عضو لروم صوتي آخر")
async def move(i, member: discord.Member, channel: discord.VoiceChannel):
    if i.user.guild_permissions.move_members:
        await member.move_to(channel); await i.response.send_message(f"✈️ تم نقل {member.name} إلى {channel.name}")
@bot.tree.command(name="vmute", description="كتم صوتي للعضو")
async def vmute(i, member: discord.Member):
    if i.user.guild_permissions.mute_members:
        await member.edit(mute=True); await i.response.send_message(f"🔇 كتم صوتي لـ {member.name}")
@bot.tree.command(name="vunmute", description="فك كتم صوتي للعضو")
async def vunmute(i, member: discord.Member):
    if i.user.guild_permissions.mute_members:
        await member.edit(mute=False); await i.response.send_message(f"🔊 فك كتم صوتي لـ {member.name}")
@bot.tree.command(name="deafen", description="تعطيل سماع العضو")
async def deafen(i, member: discord.Member):
    if i.user.guild_permissions.deafen_members:
        await member.edit(deafen=True); await i.response.send_message(f"🎧 تعطيل سماع {member.name}")
@bot.tree.command(name="undeafen", description="تفعيل سماع العضو")
async def undeafen(i, member: discord.Member):
    if i.user.guild_permissions.deafen_members:
        await member.edit(deafen=False); await i.response.send_message(f"👂 تفعيل سماع {member.name}")
@bot.tree.command(name="setup_stats", description="تأسيس روم الإحصائيات")
async def setup_stats(i):
    if i.user.guild_permissions.administrator:
        await refresh_radar_stats(i.guild); await i.response.send_message("📊 تم تأسيس الإحصائيات")

if __name__ == '__main__': keep_alive(); bot.run(RadarConfig.TOKEN)
