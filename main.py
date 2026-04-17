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
    # قائمة المصرح لهم (IDs الإدارة والمالك)
    AUTHORIZED_USERS = [
        1341796578742243338,
        551817782996762624,
        366132848228564992,
        1376970309797941372,
        1342856146662461574
    ]

# --- نظام التحديث ---
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

class EmergencyModal(discord.ui.Modal, title='إرسال بلاغ عاجل ⚠️'):
    subject = discord.ui.TextInput(label="عنوان البلاغ", placeholder="تحديث هام..", required=True)
    details = discord.ui.TextInput(label="تفاصيل البلاغ", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, interaction: discord.Interaction):
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
        await interaction.response.send_message("✅ تم الإرسال", ephemeral=True)

# --- لوحة التحكم ---
class AdminDashboard(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    @discord.ui.button(label="إرسال رسالة 📝", style=discord.ButtonStyle.success, emoji="💬")
    async def s(self, i, b): await i.response.send_modal(SayModal())
    @discord.ui.button(label="بلاغ عاجل ⚠️", style=discord.ButtonStyle.primary, emoji="📢")
    async def e(self, i, b): await i.response.send_modal(EmergencyModal())
    @discord.ui.button(label="تحديث الإحصائيات 🔄", style=discord.ButtonStyle.secondary, emoji="♻️")
    async def r(self, i, b):
        await i.response.defer(ephemeral=True)
        if await refresh_radar_stats(i.guild): await i.followup.send("✅ تم تحديث الرادار", ephemeral=True)
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
        for g in self.guilds: await refresh_radar_stats(g)

bot = RadarBot()

@bot.tree.command(name="panel", description="لوحة التحكم للإدارة المصرح لها")
async def panel(interaction: discord.Interaction):
    # التحقق عبر الأيدي أو صلاحية الإدارة
    if interaction.user.id in RadarConfig.AUTHORIZED_USERS or interaction.user.guild_permissions.administrator:
        embed = discord.Embed(title="🎮 مركز عمليات RADARZ", description="تم رصد هويتك.. الوصول متاح للمسؤولين فقط.", color=RadarConfig.MAIN_COLOR)
        await interaction.response.send_message(embed=embed, view=AdminDashboard(bot), ephemeral=True)
    else:
        await interaction.response.send_message("❌ عذراً، هويتك غير مدرجة في سجلات الوصول!", ephemeral=True)

if __name__ == '__main__':
    keep_alive()
    bot.run(RadarConfig.TOKEN)
