import asyncio
import os
import re
import discord
from discord.ext import commands, tasks
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# --- نظام الاستضافة (Flask) للبقاء حياً على Render ---
app = Flask('')
@app.route('/')
def home(): return "RADARZ Operations Online"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- الإعدادات العامة ---
class RadarConfig:
    TOKEN = os.getenv('DISCORD_TOKEN')
    MAIN_COLOR = discord.Color.red()
    # ID الكاتيجوري اللي أرسلته
    STATS_CATEGORY_ID = 1494627032112304179 
    AUTHORIZED_USERS = [1341796578742243338, 551817782996762624, 366132848228564992, 1376970309797941372, 1342856146662461574]

# --- وظيفة تحديث الإحصائيات ---
async def refresh_radar_stats(guild):
    category = guild.get_channel(RadarConfig.STATS_CATEGORY_ID)
    if not category: return False
    
    # مسح القنوات القديمة في الكاتيجوري لتجنب التكرار
    for vc in category.voice_channels:
        try: await vc.delete()
        except: pass
        
    total = guild.member_count
    online = len([m for m in guild.members if m.status != discord.Status.offline])
    bots = len([m for m in guild.members if m.bot])
    
    stats = [f"👥 الأعضاء: {total}", f"🟢 المتواجدون: {online}", f"🤖 البوتات: {bots}"]
    for s in stats:
        await guild.create_voice_channel(s, category=category, overwrites={guild.default_role: discord.PermissionOverwrite(connect=False)})
    return True

# --- نظام أزرار الحضور والغياب ---
class StreamButtons(discord.ui.View):
    def __init__(self, stream_link):
        super().__init__(timeout=None)
        self.stream_link = stream_link
        self.going = set()
        self.not_going = set()
        self.add_item(discord.ui.Button(label="دخول البث المباشر 🚌", url=self.stream_link))

    def update_embed(self, embed):
        embed.set_field_at(2, name="📡 المكتشفين على الرادار", 
                          value=f"✅ {len(self.going)} حاضر | ❌ {len(self.not_going)} غائب", inline=False)
        return embed

    @discord.ui.button(label="سأحضر ✅", style=discord.ButtonStyle.success, custom_id="go_btn")
    async def go_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.going.add(interaction.user.id)
        self.not_going.discard(interaction.user.id)
        await interaction.message.edit(embed=self.update_embed(interaction.message.embeds[0]))
        await interaction.response.send_message(f"تم تسجيل حضورك! رابط البث: {self.stream_link}", ephemeral=True)

    @discord.ui.button(label="لن أحضر ❌", style=discord.ButtonStyle.danger, custom_id="no_btn")
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.not_going.add(interaction.user.id)
        self.going.discard(interaction.user.id)
        await interaction.message.edit(embed=self.update_embed(interaction.message.embeds[0]))
        await interaction.response.send_message("تم تسجيل غيابك، نراك لاحقاً!", ephemeral=True)

# --- واجهات إدخال البيانات (Modals) ---
class SayModal(discord.ui.Modal, title='إرسال رسالة 📝'):
    msg = discord.ui.TextInput(label="المحتوى", style=discord.TextStyle.paragraph, required=True)
    ment = discord.ui.TextInput(label="نوع المنشن", placeholder="everyone / here / none", default="none")
    async def on_submit(self, interaction: discord.Interaction):
        content = f"@{self.ment.value}" if self.ment.value.lower() in ['everyone', 'here'] else ""
        await interaction.channel.send(content=f"{content}\n**{self.msg.value}**")
        await interaction.response.send_message("✅ تم الإرسال", ephemeral=True)

class StreamModal(discord.ui.Modal, title='تجهيز إشارة البث الاحترافية 📡'):
    title_in = discord.ui.TextInput(label="عنوان البث", required=True)
    time_in = discord.ui.TextInput(label="بعد كم دقيقة؟", required=True)
    link_in = discord.ui.TextInput(label="رابط اليوتيوب", required=True)
    ment_in = discord.ui.TextInput(label="التنبيه", default="everyone")
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            unix_ts = int((datetime.now() + timedelta(minutes=int(self.time_in.value))).timestamp())
        except: return await interaction.followup.send("⚠️ أرقام فقط في التوقيت!", ephemeral=True)
        
        video_id = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", self.link_in.value)
        thumb = f"https://img.youtube.com/vi/{video_id.group(1)}/maxresdefault.jpg" if video_id else ""
        
        embed = discord.Embed(title=f"🚨 إشارة بث نشطة: {self.title_in.value}", color=discord.Color.red())
        embed.add_field(name="⏳ الانطلاق:", value=f"<t:{unix_ts}:R>", inline=True)
        embed.add_field(name="🗓️ الموعد:", value=f"<t:{unix_ts}:F>", inline=False)
        embed.add_field(name="📡 المكتشفين على الرادار", value="✅ 0 حاضر | ❌ 0 غائب", inline=False)
        if thumb: embed.set_image(url=thumb)
        
        await interaction.channel.send(content=f"@{self.ment_in.value} !إرصدنا إشارة بث جديدة", embed=embed, view=StreamButtons(self.link_in.value))
        await interaction.followup.send("✅ تم إطلاق البث", ephemeral=True)

class StatusModal(discord.ui.Modal, title='تعديل حالة البوت 🛠️'):
    status = discord.ui.TextInput(label="النشاط الجديد", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=self.status.value))
        await interaction.response.send_message("✅ تم تحديث الحالة", ephemeral=True)

class EmergencyModal(discord.ui.Modal, title='إرسال بلاغ عاجل ⚠️'):
    subject = discord.ui.TextInput(label="عنوان البلاغ", required=True)
    details = discord.ui.TextInput(label="التفاصيل", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"🚨 بلاغ عاجل: {self.subject.value}", description=f"**{self.details.value}**", color=discord.Color.red())
        await interaction.channel.send(content="@everyone", embed=embed)
        await interaction.response.send_message("✅ تم النشر", ephemeral=True)

# --- لوحة التحكم الشاملة ---
class AdminDashboard(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="إرسال رسالة 📝", style=discord.ButtonStyle.success, emoji="💬", row=0)
    async def s(self, i, b): await i.response.send_modal(SayModal())

    @discord.ui.button(label="إطلاق بث 🚀", style=discord.ButtonStyle.danger, emoji="🔴", row=0)
    async def stream_btn(self, i, b): await i.response.send_modal(StreamModal())

    @discord.ui.button(label="تعديل الحالة 🛠️", style=discord.ButtonStyle.secondary, emoji="✍️", row=1)
    async def st(self, i, b): await i.response.send_modal(StatusModal())

    @discord.ui.button(label="بلاغ عاجل ⚠️", style=discord.ButtonStyle.primary, emoji="📢", row=1)
    async def e(self, i, b): await i.response.send_modal(EmergencyModal())

    @discord.ui.button(label="تحديث الإحصائيات 🔄", style=discord.ButtonStyle.secondary, emoji="♻️", row=2)
    async def refresh_btn(self, i, b):
        await i.response.defer(ephemeral=True)
        success = await refresh_radar_stats(i.guild)
        if success: await i.followup.send("✅ تم تحديث الإحصائيات في الكاتيجوري المطلوب!", ephemeral=True)
        else: await i.followup.send("❌ فشل التحديث، تأكد من الـ ID والصلاحيات.", ephemeral=True)

class RadarBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def on_ready(self):
        await self.tree.sync()
        print(f"📡 {self.user} Online")

bot = RadarBot()

@bot.tree.command(name="panel", description="لوحة تحكم RADARZ")
async def panel(interaction: discord.Interaction):
    if interaction.user.id in RadarConfig.AUTHORIZED_USERS:
        embed = discord.Embed(title="🎮 مركز عمليات RADARZ", description="جميع الأوامر جاهزة للاستخدام.", color=RadarConfig.MAIN_COLOR)
        await interaction.response.send_message(embed=embed, view=AdminDashboard(bot), ephemeral=True)

if __name__ == '__main__':
    keep_alive()
    bot.run(RadarConfig.TOKEN)
