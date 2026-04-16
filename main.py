import asyncio
import sys
import time
import re
import os
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread

# --- نظام البقاء حياً للاستضافة 24 ساعة ---
app = Flask('')
@app.route('/')
def home():
    return "I am alive"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- الإعدادات ---
class RadarConfig:
    # تم تعديل التوكن هنا ليقرأ من إعدادات السيرفر المخفية (Environment Variables)
    TOKEN = os.getenv('DISCORD_TOKEN')
    MAIN_COLOR = discord.Color.red()
    FOOTER = "نظام RADARZ الذكي v9.2 | مركز القيادة"

def get_yt_thumb(url):
    video_id = None
    patterns = [r"v=([a-zA-Z0-9_-]{11})", r"be/([a-zA-Z0-9_-]{11})", r"shorts/([a-zA-Z0-9_-]{11})", r"live/([a-zA-Z0-9_-]{11})"]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            break
    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg" if video_id else None

# --- واجهة تفاعل المتابعين ---
class StreamView(discord.ui.View):
    def __init__(self, url: str):
        super().__init__(timeout=None)
        self.url = url
        self.going_count = 0
        self.not_going_count = 0
        self.add_item(discord.ui.Button(label="دخول البث المباشر 📺", url=url, row=1))

    @discord.ui.button(label="سأحضر ✅", style=discord.ButtonStyle.success, custom_id="going_v9")
    async def going_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.going_count += 1
        embed = interaction.message.embeds[0]
        embed.set_field_at(0, name="المكتشفين على الرادار 📡", value=f"✅ **{self.going_count}** حاضر | ❌ **{self.not_going_count}** غائب", inline=True)
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send("كفو ننتظرك في البث يا بطل 🔥", ephemeral=True)

    @discord.ui.button(label="لن أحضر ❌", style=discord.ButtonStyle.danger, custom_id="not_going_v9")
    async def not_going_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.not_going_count += 1
        embed = interaction.message.embeds[0]
        embed.set_field_at(0, name="المكتشفين على الرادار 📡", value=f"✅ **{self.going_count}** حاضر | ❌ **{self.not_going_count}** غائب", inline=True)
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(f"أفا يا {interaction.user.mention} البث بدونك ناقص حاول تعيد تفكيرك نبيك معنا 💔", ephemeral=False)
        try:
            dm_embed = discord.Embed(title="لا تفوت المتعة في RADARZ 📡", description=f"وصلنا إنك ما تقدر تحضر البث حابين نذكرك إن فيه فعاليات وتوزيع جوائز بتصير\n\n**رابط البث لو غيرت رأيك**\n{self.url}", color=discord.Color.gold())
            await interaction.user.send(embed=dm_embed)
        except: pass

# --- نوافذ الإدخال Modals ---
class StatusUpdateModal(discord.ui.Modal, title='تحديث حالة البوت'):
    new_status = discord.ui.TextInput(label="ماذا تريد أن يظهر تحت اسم البوت؟", placeholder="مثال في بث مباشر الآن 🔴", required=True, max_length=100)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=self.new_status.value))
        await interaction.response.send_message(f"✅ تم تحديث الحالة إلى **{self.new_status.value}**", ephemeral=True)

class BroadcastModal(discord.ui.Modal, title='تجهيز إشارة البث الاحترافية'):
    title_in = discord.ui.TextInput(label="عنوان البث", placeholder="عنوان يشد المتابعين")
    mins_in = discord.ui.TextInput(label="التوقيت بالدقائق", placeholder="مثال 10")
    url_in = discord.ui.TextInput(label="رابط اليوتيوب")
    mention_type = discord.ui.TextInput(label="نوع التنبيه", placeholder="everyone / here / none", default="everyone")
    async def on_submit(self, interaction: discord.Interaction):
        try:
            start_time = int(time.time()) + (int(self.mins_in.value) * 60)
            thumb = get_yt_thumb(self.url_in.value)
            embed = discord.Embed(title=f"🚨 إشارة بث نشطة {self.title_in.value}", color=RadarConfig.MAIN_COLOR)
            embed.description = f"**نظام رادرز للإرسال الرقمي**\n\n⏳ الانطلاق <t:{start_time}:R>\n📅 الموعد <t:{start_time}:F>"
            embed.add_field(name="المكتشفين على الرادار 📡", value="✅ **0** حاضر | ❌ **0** غائب", inline=True)
            if thumb: embed.set_image(url=thumb)
            embed.set_footer(text=RadarConfig.FOOTER)
            content = f"@{self.mention_type.value.lower()}" if self.mention_type.value.lower() in ['everyone', 'here'] else ""
            await interaction.response.send_message(content=f"{content} رصدنا إشارة بث جديدة", embed=embed, view=StreamView(self.url_in.value))
        except Exception as e:
            await interaction.response.send_message(f"حدث خطأ {e}", ephemeral=True)

# --- لوحة التحكم ---
class AdminDashboard(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    @discord.ui.button(label="إطلاق بث 🔴", style=discord.ButtonStyle.danger, emoji="🚀")
    async def broadcast_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BroadcastModal())
    @discord.ui.button(label="تعديل الحالة 🛠️", style=discord.ButtonStyle.secondary, emoji="✍️")
    async def status_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StatusUpdateModal())

# --- تشغيل البوت ---
class RadarBotV9(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def on_ready(self):
        await self.tree.sync()
        print(f"📡 RADARZ SYSTEM v9.2 ONLINE")

bot = RadarBotV9()

@bot.tree.command(name="panel", description="مركز قيادة رادرز")
async def panel(interaction: discord.Interaction):
    if not interaction.guild: return
    if interaction.user.guild_permissions.manage_messages or interaction.user.id == interaction.guild.owner_id:
        embed = discord.Embed(title="🎮 مركز عمليات RADARZ", description="مرحباً بك في لوحة التحكم اضغط على تعديل الحالة لتغيير نشاط البوت فوراً", color=RadarConfig.MAIN_COLOR)
        await interaction.response.send_message(embed=embed, view=AdminDashboard(bot), ephemeral=True)
    else:
        await interaction.response.send_message("صلاحياتك لا تسمح بالدخول ❌", ephemeral=True)

if __name__ == '__main__':
    keep_alive()
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # التحقق من وجود التوكن قبل التشغيل
    if RadarConfig.TOKEN:
        bot.run(RadarConfig.TOKEN)
    else:
        print("❌ خطأ: التوكن غير موجود! تأكد من إضافته في Environment Variables باسم DISCORD_TOKEN")