import asyncio
import os
import re
import discord
import time
from discord.ext import commands, tasks
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# --- نظام البقاء حياً ---
app = Flask('')
@app.route('/')
def home(): return "RADARZ Operations Online"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- الإعدادات العامة ---
class RadarConfig:
    TOKEN = os.getenv('DISCORD_TOKEN')
    MAIN_COLOR = discord.Color.red()
    STATS_CATEGORY_ID = 1494627032112304179 
    AUTHORIZED_USERS = [1341796578742243338, 551817782996762624, 366132848228564992, 1376970309797941372, 1342856146662461574]

# --- نظام التحديث للإحصائيات ---
async def refresh_radar_stats(guild):
    category = guild.get_channel(RadarConfig.STATS_CATEGORY_ID)
    if not category: return False
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

# --- واجهات التفاعل (Modals) ---

class StreamModal(discord.ui.Modal, title='تجهيز إشارة البث الاحترافية 📡'):
    title_input = discord.ui.TextInput(label="عنوان البث", placeholder="عنوان يشد المتابعين...", required=True)
    time_input = discord.ui.TextInput(label="بعد كم دقيقة يبدأ؟ (أرقام فقط)", placeholder="مثلاً: 10", required=True)
    link_input = discord.ui.TextInput(label="رابط اليوتيوب", placeholder="ضع الرابط هنا...", required=True)
    mention_input = discord.ui.TextInput(label="نوع التنبيه", default="everyone", placeholder="everyone / here / none", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            minutes = int(self.time_input.value)
            start_time = datetime.now() + timedelta(minutes=minutes)
            unix_ts = int(start_time.timestamp())
        except:
            return await interaction.followup.send("⚠️ التوقيت لازم يكون أرقام!", ephemeral=True)

        video_id = re.search(r"(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^\"&?\/\s]{11})", self.link_input.value)
        thumb = f"https://img.youtube.com/vi/{video_id.group(1)}/maxresdefault.jpg" if video_id else "https://r2.community.sony.com/t5/image/serverpage/image-id/703649i6E2E195F919E3A9F/image-size/large?v=v2&px=999"

        embed = discord.Embed(title=f"🚨 إشارة بث نشطة: {self.title_input.value}", description="**نظام رادرز للإرسال الرقمي**", color=discord.Color.red())
        embed.add_field(name="⏳ الانطلاق:", value=f"<t:{unix_ts}:R>", inline=True)
        embed.add_field(name="🗓️ الموعد:", value=f"<t:{unix_ts}:F>", inline=False)
        embed.add_field(name="📡 المكتشفين على الرادار", value="✅ 0 حاضر | ❌ 0 غائب", inline=False)
        embed.set_image(url=thumb)
        embed.set_footer(text="نظام RADARZ الذكي v9.2 | مركز القيادة")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="سأحضر ✅", style=discord.ButtonStyle.success))
        view.add_item(discord.ui.Button(label="لن أحضر ❌", style=discord.ButtonStyle.danger))
        view.add_item(discord.ui.Button(label="دخول البث المباشر 🚌", url=self.link_input.value))

        content = f"@{self.mention_input.value} !إرصدنا إشارة بث جديدة" if self.mention_input.value != "none" else "!إرصدنا إشارة بث جديدة"
        await interaction.channel.send(content=content, embed=embed, view=view)
        await interaction.followup.send("✅ تم إطلاق البث", ephemeral=True)

class SayModal(discord.ui.Modal, title='إرسال رسالة 📝'):
    msg = discord.ui.TextInput(label="المحتوى", style=discord.TextStyle.paragraph, required=True)
    ment = discord.ui.TextInput(label="نوع المنشن", placeholder="everyone / here / none", default="none")
    async def on_submit(self, interaction: discord.Interaction):
        content = f"@{self.ment.value}" if self.ment.value.lower() in ['everyone', 'here'] else ""
        await interaction.channel.send(content=f"{content}\n**{self.msg.value}**")
        await interaction.response.send_message("✅ تم الإرسال", ephemeral=True)

class EmergencyModal(discord.ui.Modal, title='إرسال بلاغ عاجل ⚠️'):
    subject = discord.ui.TextInput(label="عنوان البلاغ", required=True)
    details = discord.ui.TextInput(label="التفاصيل", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"🚨 بلاغ عاجل: {self.subject.value}", description=f"**{self.details.value}**", color=discord.Color.red())
        await interaction.channel.send(content="@everyone", embed=embed)
        await interaction.response.send_message("✅ تم النشر", ephemeral=True)

class StatusModal(discord.ui.Modal, title='تعديل حالة البوت 🛠️'):
    status = discord.ui.TextInput(label="النشاط الجديد", placeholder="Watching...", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=self.status.value))
        await interaction.response.send_message("✅ تم تحديث الحالة", ephemeral=True)

# --- لوحة التحكم الكاملة ---
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
        if await refresh_radar_stats(i.guild): await i.followup.send("✅ تم التحديث", ephemeral=True)

class RadarBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def on_ready(self):
        await self.tree.sync()
        print(f"📡 {self.user} Online")

bot = RadarBot()

@bot.tree.command(name="panel", description="عرض لوحة التحكم")
async def panel(interaction: discord.Interaction):
    if interaction.user.id in RadarConfig.AUTHORIZED_USERS or interaction.user.guild_permissions.administrator:
        embed = discord.Embed(title="🎮 مركز عمليات RADARZ", description="جميع الأوامر متاحة الآن في اللوحة.", color=RadarConfig.MAIN_COLOR)
        await interaction.response.send_message(embed=embed, view=AdminDashboard(bot), ephemeral=True)

if __name__ == '__main__':
    keep_alive()
    bot.run(RadarConfig.TOKEN)
