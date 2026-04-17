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
    new_status = discord.ui.TextInput(
        label="نشاط البوت", 
        placeholder="أدخل الحالة الجديدة هنا..",
        help_text="سيتم عرض هذا النص تحت اسم البوت كنشاط (Watching).",
        required=True
    )
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=self.new_status.value))
        await interaction.response.send_message("✅ تم تحديث حالة البوت بنجاح", ephemeral=True)

class SayModal(discord.ui.Modal, title='إرسال رسالة'):
    msg = discord.ui.TextInput(label="المحتوى", style=discord.TextStyle.paragraph, required=True)
    ment = discord.ui.TextInput(
        label="نوع المنشن", 
        placeholder="everyone / here / none", 
        default="none",
        help_text="اختر 'everyone' لمنشن الكل، 'here' لمنشن المتواجدين، أو 'none' بدون منشن."
    )
    async def on_submit(self, interaction: discord.Interaction):
        content = ""
        if "everyone" in self.ment.value.lower(): content = "@everyone"
        elif "here" in self.ment.value.lower(): content = "@here"
        
        await interaction.channel.send(content=f"{content}\n**{self.msg.value}**")
        await interaction.response.send_message("✅ تم إرسال الرسالة", ephemeral=True)

# --- لوحة التحكم (تصميم عمودي مع شروحات) ---
class AdminDashboard(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="إرسال رسالة 📝", style=discord.ButtonStyle.success, emoji="💬", row=0)
    async def s(self, i, b): 
        await i.response.send_modal(SayModal())

    @discord.ui.button(label="بلاغ عاجل ⚠️", style=discord.ButtonStyle.primary, emoji="📢", row=1)
    async def e(self, i, b): 
        await i.response.send_modal(EmergencyModal())

    @discord.ui.button(label="تحديث الإحصائيات 🔄", style=discord.ButtonStyle.secondary, emoji="♻️", row=2)
    async def refresh_btn(self, i, b):
        await i.response.defer(ephemeral=True)
        if await refresh_radar_stats(i.guild): 
            await i.followup.send("✅ تم تحديث قنوات الإحصائيات فوراً", ephemeral=True)

    @discord.ui.button(label="تعديل الحالة 🛠️", style=discord.ButtonStyle.secondary, emoji="✍️", row=3)
    async def st(self, i, b): 
        await i.response.send_modal(StatusUpdateModal())

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

@bot.tree.command(name="panel", description="عرض لوحة تحكم الإدارة")
async def panel(interaction: discord.Interaction):
    if interaction.user.id in RadarConfig.AUTHORIZED_USERS or interaction.user.guild_permissions.administrator:
        embed = discord.Embed(
            title="🎮 مركز عمليات RADARZ", 
            description=(
                "**دليل أوامر اللوحة:**\n\n"
                "💬 **إرسال رسالة:** لنشر نص عادي مع خيارات المنشن (everyone/here).\n"
                "📢 **بلاغ عاجل:** إرسال إعلان رسمي باللون الأحمر مع تثبيت وتنبيه للكل.\n"
                "♻️ **تحديث الإحصائيات:** مزامنة أعداد الأعضاء والمتواجدين في القنوات الصوتية فوراً.\n"
                "✍️ **تعديل الحالة:** لتغيير النص الظاهر تحت اسم البوت في قائمة الأعضاء.\n\n"
                "📡 تم رصد هويتك.. الوصول متاح للمسؤولين فقط."
            ), 
            color=RadarConfig.MAIN_COLOR
        )
        await interaction.response.send_message(embed=embed, view=AdminDashboard(bot), ephemeral=True)
    else:
        await interaction.response.send_message("❌ عذراً، الوصول مرفوض!", ephemeral=True)

if __name__ == '__main__':
    keep_alive()
    bot.run(RadarConfig.TOKEN)
