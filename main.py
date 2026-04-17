import asyncio
import sys
import time
import re
import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
from flask import Flask
from threading import Thread

# --- نظام البقاء حياً ---
app = Flask('')
@app.route('/')
def home(): return "RADARZ System is Alive"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- الإعدادات العامة ---
class RadarConfig:
    TOKEN = os.getenv('DISCORD_TOKEN')
    MAIN_COLOR = discord.Color.red()
    FOOTER = "نظام RADARZ الذكي v9.6 | مركز القيادة"
    # الأيدي الخاص بالكاتقوري للإحصائيات
    STATS_CATEGORY_ID = 1494627032112304179 

def get_yt_thumb(url):
    video_id = None
    patterns = [r"v=([a-zA-Z0-9_-]{11})", r"be/([a-zA-Z0-9_-]{11})", r"shorts/([a-zA-Z0-9_-]{11})", r"live/([a-zA-Z0-9_-]{11})"]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match: video_id = match.group(1); break
    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg" if video_id else None

# --- واجهات التفاعل (Views & Modals) ---
class StreamView(discord.ui.View):
    def __init__(self, url: str):
        super().__init__(timeout=None)
        self.url = url
        self.going = 0
        self.not_going = 0
        self.add_item(discord.ui.Button(label="دخول البث 📺", url=url, row=1))

    @discord.ui.button(label="سأحضر ✅", style=discord.ButtonStyle.success, custom_id="going_btn")
    async def going_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.going += 1
        embed = interaction.message.embeds[0]
        embed.set_field_at(0, name="الرادار 📡", value=f"✅ **{self.going}** حاضر | ❌ **{self.not_going}** غائب")
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="لن أحضر ❌", style=discord.ButtonStyle.danger, custom_id="not_going_btn")
    async def not_going_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.not_going += 1
        embed = interaction.message.embeds[0]
        embed.set_field_at(0, name="الرادار 📡", value=f"✅ **{self.going}** حاضر | ❌ **{self.not_going}** غائب")
        await interaction.response.edit_message(embed=embed)

# نافذة تعديل الحالة
class StatusUpdateModal(discord.ui.Modal, title='تحديث حالة البوت'):
    new_status = discord.ui.TextInput(label="نشاط البوت الحالي", placeholder="مثال: في بث مباشر الآن 🔴", required=True, max_length=100)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=self.new_status.value))
        await interaction.response.send_message(f"✅ تم تحديث الحالة إلى **{self.new_status.value}**", ephemeral=True)

# نافذة إرسال الرسالة
class SayModal(discord.ui.Modal, title='إرسال رسالة مخصصة'):
    msg = discord.ui.TextInput(label="محتوى الرسالة", style=discord.TextStyle.paragraph, required=True, placeholder="اكتب رسالتك هنا..")
    ment = discord.ui.TextInput(label="المنشن (everyone / here / none)", default="none")
    async def on_submit(self, interaction: discord.Interaction):
        content = ""
        m = self.ment.value.lower()
        if "everyone" in m: content = "@everyone"
        elif "here" in m: content = "@here"
        await interaction.channel.send(content=f"{content}\n**{self.msg.value}**")
        await interaction.response.send_message("✅ تم الإرسال!", ephemeral=True)

# نافذة إطلاق البث
class BroadcastModal(discord.ui.Modal, title='تجهيز إشارة البث'):
    title_in = discord.ui.TextInput(label="عنوان البث")
    mins_in = discord.ui.TextInput(label="بعد كم دقيقة؟")
    url_in = discord.ui.TextInput(label="رابط اليوتيوب")
    async def on_submit(self, interaction: discord.Interaction):
        try:
            start_t = int(time.time()) + (int(self.mins_in.value) * 60)
            embed = discord.Embed(title=f"🚨 إشارة بث: {self.title_in.value}", color=RadarConfig.MAIN_COLOR)
            embed.description = f"⏳ يبدأ البث <t:{start_t}:R>\n📅 الموعد <t:{start_t}:F>"
            embed.add_field(name="الرادار 📡", value="✅ **0** حاضر | ❌ **0** غائب")
            thumb = get_yt_thumb(self.url_in.value)
            if thumb: embed.set_image(url=thumb)
            embed.set_footer(text=RadarConfig.FOOTER)
            await interaction.response.send_message(embed=embed, view=StreamView(self.url_in.value))
        except: await interaction.response.send_message("خطأ في البيانات!", ephemeral=True)

# لوحة التحكم الشاملة
class AdminDashboard(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="إطلاق بث 🔴", style=discord.ButtonStyle.danger, emoji="🚀")
    async def b_btn(self, i, b): await i.response.send_modal(BroadcastModal())

    @discord.ui.button(label="إرسال رسالة 📝", style=discord.ButtonStyle.success, emoji="💬")
    async def s_btn(self, i, b): await i.response.send_modal(SayModal())

    @discord.ui.button(label="تعديل الحالة 🛠️", style=discord.ButtonStyle.secondary, emoji="✍️")
    async def status_btn(self, i, b): await i.response.send_modal(StatusUpdateModal())

# --- البوت الرئيسي ---
class RadarBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def on_ready(self):
        await self.tree.sync()
        if not self.update_stats.is_running(): self.update_stats.start()
        print(f"📡 {self.user.name} Is Online!")

    @tasks.loop(minutes=10)
    async def update_stats(self):
        for guild in self.guilds:
            category = guild.get_channel(RadarConfig.STATS_CATEGORY_ID)
            if not category: continue
            for vc in category.voice_channels:
                try: await vc.delete()
                except: pass
            total = guild.member_count
            online = len([m for m in guild.members if m.status != discord.Status.offline])
            bots = len([m for m in guild.members if m.bot])
            stats = [f"👥 الأعضاء: {total}", f"🟢 المتواجدون: {online}", f"🤖 البوتات: {bots}"]
            for s in stats:
                await guild.create_voice_channel(s, category=category, overwrites={guild.default_role: discord.PermissionOverwrite(connect=False)})

bot = RadarBot()

@bot.tree.command(name="panel", description="لوحة تحكم رادرز")
async def panel(interaction: discord.Interaction):
    if interaction.user.guild_permissions.manage_messages:
        embed = discord.Embed(
            title="🎮 مركز عمليات RADARZ", 
            description="اختر العملية المطلوبة من الأزرار أدناه.", 
            color=RadarConfig.MAIN_COLOR
        )
        await interaction.response.send_message(embed=embed, view=AdminDashboard(bot), ephemeral=True)
    else:
        await interaction.response.send_message("صلاحياتك لا تكفي! ❌", ephemeral=True)

if __name__ == '__main__':
    keep_alive()
    bot.run(RadarConfig.TOKEN)
