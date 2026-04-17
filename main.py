import asyncio
import sys
import time
import re
import os
import discord
from discord.ext import commands, tasks
from flask import Flask
from threading import Thread

# --- نظام البقاء حياً ---
app = Flask('')
@app.route('/')
def home(): return "RADARZ Online"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- الإعدادات العامة ---
class RadarConfig:
    TOKEN = os.getenv('DISCORD_TOKEN')
    MAIN_COLOR = discord.Color.red()
    STATS_CATEGORY_ID = 1494627032112304179 

def get_yt_thumb(url):
    video_id = None
    patterns = [r"v=([a-zA-Z0-9_-]{11})", r"be/([a-zA-Z0-9_-]{11})", r"shorts/([a-zA-Z0-9_-]{11})", r"live/([a-zA-Z0-9_-]{11})"]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match: video_id = match.group(1); break
    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg" if video_id else None

# --- واجهات التفاعل ---

class EmergencyModal(discord.ui.Modal, title='إرسال بلاغ عاجل ⚠️'):
    subject = discord.ui.TextInput(label="عنوان البلاغ", placeholder="تحديث هام..", required=True)
    details = discord.ui.TextInput(label="تفاصيل البلاغ", style=discord.TextStyle.paragraph, required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        # تم حذف سطر "صدر من مركز القيادة" كما طلبت
        embed = discord.Embed(title=f"🚨 بلاغ عاجل: {self.subject.value}", description=f"\n**{self.details.value}**\n\n@everyone", color=discord.Color.red())
        msg = await interaction.channel.send(content="@everyone", embed=embed)
        try: await msg.pin()
        except: pass
        await interaction.response.send_message("✅ تم النشر والتثبيت", ephemeral=True)

class StatusUpdateModal(discord.ui.Modal, title='تحديث حالة البوت'):
    new_status = discord.ui.TextInput(label="نشاط البوت", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=self.new_status.value))
        await interaction.response.send_message("✅ تم التحديث", ephemeral=True)

class SayModal(discord.ui.Modal, title='إرسال رسالة'):
    msg = discord.ui.TextInput(label="المحتوى", style=discord.TextStyle.paragraph, required=True)
    ment = discord.ui.TextInput(label="المنشن", default="none")
    async def on_submit(self, interaction: discord.Interaction):
        content = ""
        if "everyone" in self.ment.value.lower(): content = "@everyone"
        elif "here" in self.ment.value.lower(): content = "@here"
        await interaction.channel.send(content=f"{content}\n**{self.msg.value}**")
        await interaction.response.send_message("✅ تم", ephemeral=True)

class BroadcastModal(discord.ui.Modal, title='تجهيز بث'):
    title_in = discord.ui.TextInput(label="العنوان")
    mins_in = discord.ui.TextInput(label="التوقيت (بالدقائق)")
    url_in = discord.ui.TextInput(label="الرابط")
    async def on_submit(self, interaction: discord.Interaction):
        start_t = int(time.time()) + (int(self.mins_in.value) * 60)
        embed = discord.Embed(title=f"🚨 بث نشط: {self.title_in.value}", color=RadarConfig.MAIN_COLOR)
        embed.description = f"⏳ انطلاق <t:{start_t}:R>"
        embed.add_field(name="الرادار 📡", value="✅ **0** | ❌ **0**")
        thumb = get_yt_thumb(self.url_in.value)
        if thumb: embed.set_image(url=thumb)
        await interaction.response.send_message(embed=embed, view=StreamView(self.url_in.value))

class StreamView(discord.ui.View):
    def __init__(self, url: str):
        super().__init__(timeout=None)
        self.url = url
        self.going = 0
        self.not_going = 0
        self.add_item(discord.ui.Button(label="دخول البث 📺", url=url, row=1))
    @discord.ui.button(label="سأحضر ✅", style=discord.ButtonStyle.success)
    async def g(self, i, b):
        self.going += 1
        e = i.message.embeds[0]
        e.set_field_at(0, name="الرادار 📡", value=f"✅ **{self.going}** | ❌ **{self.not_going}**")
        await i.response.edit_message(embed=e)
    @discord.ui.button(label="لن أحضر ❌", style=discord.ButtonStyle.danger)
    async def n(self, i, b):
        self.not_going += 1
        e = i.message.embeds[0]
        e.set_field_at(0, name="الرادار 📡", value=f"✅ **{self.going}** | ❌ **{self.not_going}**")
        await i.response.edit_message(embed=e)

class AdminDashboard(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    @discord.ui.button(label="إطلاق بث 🔴", style=discord.ButtonStyle.danger, emoji="🚀")
    async def b(self, i, b): await i.response.send_modal(BroadcastModal())
    @discord.ui.button(label="إرسال رسالة 📝", style=discord.ButtonStyle.success, emoji="💬")
    async def s(self, i, b): await i.response.send_modal(SayModal())
    @discord.ui.button(label="بلاغ عاجل ⚠️", style=discord.ButtonStyle.primary, emoji="📢")
    async def e(self, i, b): await i.response.send_modal(EmergencyModal())
    @discord.ui.button(label="تعديل الحالة 🛠️", style=discord.ButtonStyle.secondary, emoji="✍️")
    async def st(self, i, b): await i.response.send_modal(StatusUpdateModal())

# --- البوت الرئيسي ---
class RadarBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def on_ready(self):
        await self.tree.sync()
        if not self.u_s.is_running(): self.u_s.start()
        print(f"📡 {self.user} Online")
    @tasks.loop(minutes=10)
    async def u_s(self):
        for g in self.guilds:
            cat = g.get_channel(RadarConfig.STATS_CATEGORY_ID)
            if not cat: continue
            for vc in cat.voice_channels: await vc.delete()
            stats = [f"👥 الأعضاء: {g.member_count}", f"🟢 المتواجدون: {len([m for m in g.members if m.status != discord.Status.offline])}", f"🤖 البوتات: {len([m for m in g.members if m.bot])}"]
            for s in stats: await g.create_voice_channel(s, category=cat, overwrites={g.default_role: discord.PermissionOverwrite(connect=False)})

bot = RadarBot()

@bot.tree.command(name="panel", description="لوحة التحكم")
async def panel(interaction: discord.Interaction):
    if interaction.user.id == interaction.guild.owner_id:
        embed = discord.Embed(title="🎮 مركز عمليات RADARZ", description="تحكم كامل بالسيرفر من هنا.", color=RadarConfig.MAIN_COLOR)
        await interaction.response.send_message(embed=embed, view=AdminDashboard(bot), ephemeral=True)

if __name__ == '__main__':
    keep_alive()
    bot.run(RadarConfig.TOKEN)
