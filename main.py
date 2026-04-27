import asyncio, os, re, discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# --- نظام الاستضافة للبقاء حياً على Render ---
app = Flask('')
@app.route('/')
def home(): return "RADARZ Operations Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run); t.daemon = True; t.start()

# --- الإعدادات العامة ---
class RadarConfig:
    TOKEN = os.getenv('DISCORD_TOKEN')
    MAIN_COLOR = discord.Color.red()
    STREAM_CHANNEL_ID = 1200740059817721856
    YOUTUBE_CHANNEL_ID = 924316521050820609
    STATS_CATEGORY_ID = 1494627032112304179 
    LOGS_ROOM_ID = 1498422633669197904 
    AUTHORIZED_USERS = [1341796578742243338, 551817782996762624, 366132848228564992, 1376970309797941372, 1342856146662461574]

# --- أنظمة الأزرار والمودالز ---

# 1. نظام أزرار حضور البث
class StreamButtons(discord.ui.View):
    def __init__(self, stream_link):
        super().__init__(timeout=None)
        self.stream_link = stream_link
        self.going, self.not_going = set(), set()
        self.add_item(discord.ui.Button(label="دخول البث المباشر 🚌", url=self.stream_link))

    def update_embed(self, embed):
        embed.set_field_at(2, name="📡 المكتشفين على الرادار", value=f"✅ {len(self.going)} حاضر | ❌ {len(self.not_going)} غائب", inline=False)
        return embed

    @discord.ui.button(label="سأحضر ✅", style=discord.ButtonStyle.success, custom_id="go_btn")
    async def go_button(self, interaction, button):
        self.going.add(interaction.user.id); self.not_going.discard(interaction.user.id)
        await interaction.message.edit(embed=self.update_embed(interaction.message.embeds[0]))
        await interaction.response.send_message(f"تم تسجيل حضورك!", ephemeral=True)

    @discord.ui.button(label="لن أحضر ❌", style=discord.ButtonStyle.danger, custom_id="no_btn")
    async def no_button(self, interaction, button):
        self.not_going.add(interaction.user.id); self.going.discard(interaction.user.id)
        await interaction.message.edit(embed=self.update_embed(interaction.message.embeds[0]))
        await interaction.response.send_message("تم تسجيل غيابك", ephemeral=True)

# 2. مودالز الإدارة (طرد، تايم أوت، بث، يوتيوب، رسائل)
class KickModal(discord.ui.Modal, title='طرد عضو 👞'):
    u = discord.ui.TextInput(label="ID العضو"); r = discord.ui.TextInput(label="السبب", required=False)
    async def on_submit(self, i):
        m = i.guild.get_member(int(self.u.value))
        await m.kick(reason=self.r.value); await i.response.send_message(f"✅ طردنا {m.name}", ephemeral=True)

class TimeoutModal(discord.ui.Modal, title='تايم أوت ⏳'):
    u = discord.ui.TextInput(label="ID العضو"); d = discord.ui.TextInput(label="المدة بالدقائق", default="10")
    async def on_submit(self, i):
        m = i.guild.get_member(int(self.u.value))
        await m.timeout(timedelta(minutes=int(self.d.value))); await i.response.send_message(f"✅ تم سجن {m.name}", ephemeral=True)

class StreamModal(discord.ui.Modal, title='إشارة بث 📡'):
    t = discord.ui.TextInput(label="العنوان"); ti = discord.ui.TextInput(label="بعد كم دقيقة؟"); l = discord.ui.TextInput(label="الرابط")
    async def on_submit(self, i):
        ts = int((datetime.now() + timedelta(minutes=int(self.ti.value))).timestamp())
        v_id = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", self.l.value)
        thumb = f"https://img.youtube.com/vi/{v_id.group(1)}/maxresdefault.jpg" if v_id else ""
        embed = discord.Embed(title=f"🚨 إشارة بث: {self.t.value}", color=discord.Color.red())
        embed.add_field(name="⏳ الانطلاق:", value=f"<t:{ts}:R>"); embed.add_field(name="📡 المكتشفين", value="✅ 0 | ❌ 0", inline=False)
        if thumb: embed.set_image(url=thumb)
        ch = i.guild.get_channel(RadarConfig.STREAM_CHANNEL_ID)
        await ch.send(content="@everyone !إرصدنا إشارة بث جديدة", embed=embed, view=StreamButtons(self.l.value))
        await i.response.send_message("✅ تم الإطلاق", ephemeral=True)

class YoutubeModal(discord.ui.Modal, title='فيديو جديد 🎬'):
    l = discord.ui.TextInput(label="الرابط"); m = discord.ui.TextInput(label="المنشن", default="everyone")
    async def on_submit(self, i):
        ch = i.guild.get_channel(RadarConfig.YOUTUBE_CHANNEL_ID)
        await ch.send(content=f"📣 @{self.m.value} فيديو جديد!\n{self.l.value}")
        await i.response.send_message("✅ تم النشر", ephemeral=True)

class SayModal(discord.ui.Modal, title='رسالة 📝'):
    m = discord.ui.TextInput(label="المحتوى", style=discord.TextStyle.paragraph); n = discord.ui.TextInput(label="المنشن", default="none")
    async def on_submit(self, i):
        c = f"@{self.n.value}" if self.n.value.lower() in ['everyone', 'here'] else ""
        await i.channel.send(content=f"{c}\n**{self.m.value}**"); await i.response.send_message("✅ تم", ephemeral=True)

# --- لوحة التحكم الشاملة ---
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
        cat = i.guild.get_channel(RadarConfig.STATS_CATEGORY_ID)
        for vc in cat.voice_channels: await vc.delete()
        await i.guild.create_voice_channel(f"👥 الأعضاء: {i.guild.member_count}", category=cat)
        await i.followup.send("✅ تم", ephemeral=True)

# --- البوت الأساسي ---
class RadarBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def on_ready(self): await self.tree.sync(); print(f"📡 {self.user} Online")

    async def on_message_delete(self, m):
        if m.author.bot: return
        log = self.get_channel(RadarConfig.LOGS_ROOM_ID)
        emb = discord.Embed(title="🗑️ حذف رسالة", color=discord.Color.red(), timestamp=datetime.now())
        emb.add_field(name="الكاتب:", value=m.author.mention); emb.add_field(name="المحتوى:", value=m.content or "ملف")
        await log.send(embed=emb)

    async def on_message_edit(self, b, a):
        if b.author.bot or b.content == a.content: return
        log = self.get_channel(RadarConfig.LOGS_ROOM_ID)
        emb = discord.Embed(title="📝 تعديل رسالة", color=discord.Color.orange(), timestamp=datetime.now())
        emb.add_field(name="قبل:", value=b.content); emb.add_field(name="بعد:", value=a.content)
        await log.send(embed=emb)

    async def on_audit_log_entry_create(self, e):
        log = self.get_channel(RadarConfig.LOGS_ROOM_ID)
        if e.action in [discord.AuditLogAction.kick, discord.AuditLogAction.ban, discord.AuditLogAction.channel_delete]:
            emb = discord.Embed(title="🛡️ إجراء إداري", color=discord.Color.blue(), timestamp=datetime.now())
            emb.add_field(name="المنفذ:", value=e.user.mention); emb.add_field(name="النوع:", value=str(e.action).split('.')[-1])
            await log.send(embed=emb)

bot = RadarBot()
@bot.tree.command(name="panel", description="مركز العمليات")
async def panel(i):
    if i.user.id in RadarConfig.AUTHORIZED_USERS:
        await i.response.send_message(embed=discord.Embed(title="🎮 RADARZ Panel", color=RadarConfig.MAIN_COLOR), view=AdminDashboard(bot), ephemeral=True)

if __name__ == '__main__': keep_alive(); bot.run(RadarConfig.TOKEN)
