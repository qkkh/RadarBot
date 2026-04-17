import asyncio
import os
import re
import discord
import requests
from discord.ext import commands, tasks
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# --- نظام الاستضافة (Flask) ---
app = Flask('')
@app.route('/')
def home(): return "RADARZ YouTube Tracking Active"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run); t.daemon = True; t.start()

# --- الإعدادات العامة ---
class RadarConfig:
    TOKEN = os.getenv('DISCORD_TOKEN')
    MAIN_COLOR = discord.Color.red()
    # القناة التي أرسلتها لنشر الفيديوهات
    YT_POST_CHANNEL_ID = 924316521050820609
    # ضع هنا الـ ID الخاص بقناتك على يوتيوب (الذي يبدأ بـ UC) للربط التلقائي
    YOUTUBE_CHANNEL_ID = "UC_YOUR_CHANNEL_ID_HERE"
    AUTHORIZED_USERS = [1341796578742243338, 551817782996762624, 1376970309797941372]

# --- وظيفة ذكية لسحب اسم القناة من الرابط ---
def fetch_channel_name(url):
    try:
        response = requests.get(url).text
        # البحث عن اسم صاحب القناة في كود الصفحة
        match = re.search(r'"author":"(.*?)"', response)
        return match.group(1) if match else "YouTube Creator"
    except:
        return "YouTube Creator"

# --- نظام الربط التلقائي (المراقبة) ---
last_video_id = None
@tasks.loop(minutes=5)
async def youtube_tracker():
    global last_video_id
    if RadarConfig.YOUTUBE_CHANNEL_ID == "UC_YOUR_CHANNEL_ID_HERE": return
    try:
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={RadarConfig.YOUTUBE_CHANNEL_ID}"
        feed = requests.get(rss_url).text
        current_id = re.search(r'<yt:videoId>(.*?)</yt:videoId>', feed).group(1)
        
        if current_id != last_video_id:
            if last_video_id is not None:
                channel = bot.get_channel(RadarConfig.YT_POST_CHANNEL_ID)
                author = re.search(r'<author><name>(.*?)</name>', feed).group(1)
                # تنسيق الإعلان الاحترافي
                await channel.send(f"Hey @everyone **{author}** uploaded a new youtube video!\nhttps://www.youtube.com/watch?v={current_id}")
            last_video_id = current_id
    except: pass

# --- واجهة إدخال فيديو اليوتيوب (الزر اليدوي) ---
class YoutubeManualModal(discord.ui.Modal, title='نشر فيديو يوتيوب 🎬'):
    link = discord.ui.TextInput(label="رابط الفيديو", placeholder="انسخ الرابط هنا...", required=True)
    ment = discord.ui.TextInput(label="المنشن", default="everyone")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # سحب اسم القناة الحقيقي بدلاً من اسم المستخدم
        channel_display_name = fetch_channel_name(self.link.value)
        
        # إرسال الرسالة إلى القناة المحددة 924316521050820609
        target_channel = interaction.guild.get_channel(RadarConfig.YT_POST_CHANNEL_ID)
        content = f"Hey @{self.ment.value} **{channel_display_name}** uploaded a new youtube video!\n{self.link.value}"
        
        if target_channel:
            await target_channel.send(content=content)
            await interaction.followup.send(f"✅ تم النشر في قناة الفيديوهات باسم: {channel_display_name}", ephemeral=True)
        else:
            await interaction.followup.send("❌ لم أجد القناة، تأكد من الصلاحيات.", ephemeral=True)

# --- لوحة التحكم ---
class AdminDashboard(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @discord.ui.button(label="فيديو اليوتيوب 🎬", style=discord.ButtonStyle.primary, emoji="🎥")
    async def youtube_btn(self, i, b):
        await i.response.send_modal(YoutubeManualModal())

    @discord.ui.button(label="إطلاق بث 🚀", style=discord.ButtonStyle.danger, emoji="🔴")
    async def stream_btn(self, i, b):
        # هنا تضع كود StreamModal السابق الذي صممناه
        pass

class RadarBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def on_ready(self):
        await self.tree.sync()
        youtube_tracker.start() # تشغيل الربط التلقائي
        print(f"📡 RADARZ Online - Target Channel: {RadarConfig.YT_POST_CHANNEL_ID}")

bot = RadarBot()

@bot.tree.command(name="panel", description="فتح لوحة تحكم رادارز")
async def panel(interaction: discord.Interaction):
    if interaction.user.id in RadarConfig.AUTHORIZED_USERS:
        embed = discord.Embed(title="🎮 مركز عمليات RADARZ", description="تحكم في النشر والإشعارات فوراً.", color=RadarConfig.MAIN_COLOR)
        await interaction.response.send_message(embed=embed, view=AdminDashboard(), ephemeral=True)

if __name__ == '__main__':
    keep_alive()
    bot.run(RadarConfig.TOKEN)
