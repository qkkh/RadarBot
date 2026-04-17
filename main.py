import asyncio
import os
import re
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# --- نظام الاستضافة للبقاء حياً على Render ---
app = Flask('')
@app.route('/')
def home(): return "RADARZ Operations Online"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- الإعدادات العامة ---
class RadarConfig:
    TOKEN = os.getenv('DISCORD_TOKEN')
    MAIN_COLOR = discord.Color.red()
    STATS_CATEGORY_ID = 1494627032112304179 
    AUTHORIZED_USERS = [1341796578742243338, 551817782996762624, 366132848228564992, 1376970309797941372, 1342856146662461574]

# --- وظيفة تحديث الإحصائيات ---
async def refresh_radar_stats(guild):
    category = guild.get_channel(RadarConfig.STATS_CATEGORY_ID)
    if not category: return False
    for vc in category.voice_channels:
        try: await vc.delete()
        except: pass
    total, online = guild.member_count, len([m for m in guild.members if m.status != discord.Status.offline])
    stats = [f"👥 الأعضاء: {total}", f"🟢 المتواجدون: {online}", f"🤖 البوتات: {len([m for m in guild.members if m.bot])}"]
    for s in stats:
        await guild.create_voice_channel(s, category=category, overwrites={guild.default_role: discord.PermissionOverwrite(connect=False)})
    return True

# --- نظام أزرار البث المباشر ---
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
    async def go_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.going.add(interaction.user.id); self.not_going.discard(interaction.user.id)
        await interaction.message.edit(embed=self.update_embed(interaction.message.embeds[0]))
        await interaction.response.send_message(f"تم تسجيل حضورك! الرابط: {self.stream_link}", ephemeral=True)

    @discord.ui.button(label="لن أحضر ❌", style=discord.ButtonStyle.danger, custom_id="no_btn")
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.not_going.add(interaction.user.id); self.going.discard(interaction.user.id)
        await interaction.message.edit(embed=self.update_embed(interaction.message.embeds[0]))
        await interaction.response.send_message("تم تسجيل غيابك، نراك لاحقاً!", ephemeral=True)

# --- واجهة فيديو اليوتيوب الجديد (تم التعريب) ---
class YoutubeModal(discord.ui.Modal, title='نشر فيديو يوتيوب جديد 🎬'):
    link = discord.ui.TextInput(label="رابط الفيديو", placeholder="https://www.youtube.com/watch?v=...", required=True)
    ment = discord.ui.TextInput(label="المنشن", default="everyone")
    async def on_submit(self, interaction: discord.Interaction):
        # الرسالة المعربة الجديدة
        content = f"📣 @{self.ment.value} **رادارز Radarz** نزل فيديو جديد ورهيب على اليوتيوب! لا يفوتكم المشاهدة 🔥\n\n{self.link.value}"
        await interaction.channel.send(content=content)
        await interaction.response.send_message("✅ تم نشر الفيديو بالعربي بنجاح!", ephemeral=True)

# --- واجهات اللوحة الأخرى ---
class SayModal(discord.ui.Modal, title='إرسال رسالة 📝'):
    msg = discord.ui.TextInput(label="المحتوى", style=discord.TextStyle.paragraph, required=True)
    ment = discord.ui.TextInput(label="نوع المنشن", default="none")
    async def on_submit(self, interaction: discord.Interaction):
        c = f"@{self.ment.value}" if self.ment.value.lower() in ['everyone', 'here'] else ""
        await interaction.channel.send(content=f"{c}\n**{self.msg.value}**")
        await interaction.response.send_message("✅ تم الإرسال", ephemeral=True)

class StreamModal(discord.ui.Modal, title='تجهيز إشارة البث الاحترافية 📡'):
    title_in = discord.ui.TextInput(label="عنوان البث", required=True)
    time_in = discord.ui.TextInput(label="بعد كم دقيقة؟", required=True)
    link_in = discord.ui.TextInput(label="رابط اليوتيوب", required=True)
    ment_in = discord.ui.TextInput(label="التنبيه", default="everyone")
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try: ts = int((datetime.now() + timedelta(minutes=int(self.time_in.value))).timestamp())
        except: return await interaction.followup.send("⚠️ أرقام فقط!", ephemeral=True)
        v_id = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", self.link_in.value)
        thumb = f"https://img.youtube.com/vi/{v_id.group(1)}/maxresdefault.jpg" if v_id else ""
        embed = discord.Embed(title=f"🚨 إشارة بث نشطة: {self.title_in.value}", color=discord.Color.red())
        embed.add_field(name="⏳ الانطلاق:", value=f"<t:{ts}:R>", inline=True)
        embed.add_field(name="🗓️ الموعد:", value=f"<t:{ts}:F>", inline=False)
        embed.add_field(name="📡 المكتشفين على الرادار", value="✅ 0 حاضر | ❌ 0 غائب", inline=False)
        if thumb: embed.set_image(url=thumb)
        await interaction.channel.send(content=f"@{self.ment_in.value} !إرصدنا إشارة بث جديدة", embed=embed, view=StreamButtons(self.link_in.value))
        await interaction.followup.send("✅ تم الإطلاق", ephemeral=True)

# --- لوحة التحكم الشاملة ---
class AdminDashboard(discord.ui.View):
    def __init__(self, bot): super().__init__(timeout=None); self.bot = bot
    @discord.ui.button(label="إرسال رسالة 📝", style=discord.ButtonStyle.success, emoji="💬", row=0)
    async def s(self, i, b): await i.response.send_modal(SayModal())
    @discord.ui.button(label="إطلاق بث 🚀", style=discord.ButtonStyle.danger, emoji="🔴", row=0)
    async def strm(self, i, b): await i.response.send_modal(StreamModal())
    @discord.ui.button(label="فيديو اليوتيوب 🎬", style=discord.ButtonStyle.primary, emoji="🎥", row=1)
    async def yt(self, i, b): await i.response.send_modal(YoutubeModal())
    @discord.ui.button(label="تعديل الحالة 🛠️", style=discord.ButtonStyle.secondary, emoji="✍️", row=1)
    async def st(self, i, b):
        class StatM(discord.ui.Modal, title='تعديل الحالة'):
            s = discord.ui.TextInput(label="النشاط")
            async def on_submit(self, i): 
                await i.client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=self.s.value))
                await i.response.send_message("✅ تم", ephemeral=True)
        await i.response.send_modal(StatM())
    @discord.ui.button(label="بلاغ عاجل ⚠️", style=discord.ButtonStyle.primary, emoji="📢", row=2)
    async def e(self, i, b):
        class EmM(discord.ui.Modal, title='بلاغ عاجل'):
            t = discord.ui.TextInput(label="العنوان"); d = discord.ui.TextInput(label="التفاصيل", style=discord.TextStyle.paragraph)
            async def on_submit(self, i):
                await i.channel.send(content="@everyone", embed=discord.Embed(title=f"🚨 {self.t.value}", description=self.d.value, color=discord.Color.red()))
                await i.response.send_message("✅ تم", ephemeral=True)
        await i.response.send_modal(EmM())
    @discord.ui.button(label="تحديث الإحصائيات 🔄", style=discord.ButtonStyle.secondary, emoji="♻️", row=2)
    async def refresh(self, i, b):
        await i.response.defer(ephemeral=True)
        if await refresh_radar_stats(i.guild): await i.followup.send("✅ تم التحديث", ephemeral=True)
        else: await i.followup.send("❌ خطأ بالـ ID", ephemeral=True)

class RadarBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def on_ready(self): await self.tree.sync(); print(f"📡 {self.user} Online")

bot = RadarBot()
@bot.tree.command(name="panel", description="لوحة التحكم")
async def panel(i: discord.Interaction):
    if i.user.id in RadarConfig.AUTHORIZED_USERS:
        emb = discord.Embed(title="🎮 مركز عمليات RADARZ", description="دليل الأوامر جاهز، اختر ما يناسبك.", color=RadarConfig.MAIN_COLOR)
        await i.response.send_message(embed=emb, view=AdminDashboard(bot), ephemeral=True)

if __name__ == '__main__': keep_alive(); bot.run(RadarConfig.TOKEN)
