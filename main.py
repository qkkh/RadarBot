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

class SayModal(discord.ui.Modal, title='إرسال رسالة رادرز المخصصة'):
    message_content = discord.ui.TextInput(
        label="محتوى الرسالة",
        style=discord.TextStyle.paragraph,
        placeholder="اكتب رسالتك هنا..",
        required=True, max_length=2000
    )
    mention_type = discord.ui.TextInput(
        label="نوع المنشن (everyone / here / none)",
        placeholder="everyone / here / none",
        default="none", max_length=10
    )
    async def on_submit(self, interaction: discord.Interaction):
        formatted_message = f"**{self.message_content.value}**"
        content = ""
        m_type = self.mention_type.value.lower()
        if "everyone" in m_type: content = "@everyone"
        elif "here" in m_type: content = "@here"
        await interaction.channel.send(content=f"{content}\n{formatted_message}")
        await interaction.response.send_message("✅ تم الإرسال بنجاح!", ephemeral=True)

# --- لوحة التحكم العامة ---
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

# --- تشغيل البوت ونظام الإحصائيات ---
class RadarBotV9(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def on_ready(self):
        await self.tree.sync()
        self.update_stats.start() # تشغيل تحديث الإحصائيات تلقائياً
        print(f"📡 RADARZ SYSTEM v9.2 ONLINE")

    @tasks.loop(minutes=10) # تحديث كل 10 دقائق لتجنب الحظر
    async def update_stats(self):
        for guild in self.guilds:
            # البحث عن كاتيجوري الإحصائيات أو إنشاؤه
            category = discord.utils.get(guild.categories, name="📊 إحصائيات الرادار")
            if not category:
                category = await guild.create_category("📊 إحصائيات الرادار", position=0)
            
            total_members = guild.member_count
            online_members = len([m for m in guild.members if m.status != discord.Status.offline])
            bots_count = len([m for m in guild.members if m.bot])

            stats = {
                f"👥 الأعضاء: {total_members}": "total",
                f"🟢 المتواجدون: {online_members}": "online",
                f"🤖 البوتات: {bots_count}": "bots"
            }

            for name, s_type in stats.items():
                channel = discord.utils.get(category.voice_channels, name=lambda x: s_type in x.name.lower() or any(char in x.name for char in ["👥", "🟢", "🤖"]))
                if not channel:
                    await guild.create_voice_channel(name, category=category, overwrites={guild.default_role: discord.PermissionOverwrite(connect=False)})
                else:
                    await channel.edit(name=name)

bot = RadarBotV9()

@bot.tree.command(name="say", description="يفتح نافذة لكتابة رسالة طويلة ومنسقة")
async def say(interaction: discord.Interaction):
    if interaction.user.guild_permissions.manage_messages or interaction.user.id == interaction.guild.owner_id:
        await interaction.response.send_modal(SayModal())
    else:
        await interaction.response.send_message("❌ ليس لديك صلاحية!", ephemeral=True)

@bot.tree.command(name="panel", description="مركز قيادة رادرز")
async def panel(interaction: discord.Interaction):
    if not interaction.guild: return
    if interaction.user.guild_permissions.manage_messages or interaction.user.id == interaction.guild.owner_id:
        embed = discord.Embed(
            title="🎮 مركز عمليات RADARZ", 
            description="مرحباً بك في لوحة التحكم.\n\n- **إطلاق بث**: لإرسال إشارة بث.\n- **تعديل الحالة**: لتغيير نشاط البوت.", 
            color=RadarConfig.MAIN_COLOR
        )
        await interaction.response.send_message(embed=embed, view=AdminDashboard(bot), ephemeral=True)
    else:
        await interaction.response.send_message("صلاحياتك لا تسمح بالدخول ❌", ephemeral=True)

if __name__ == '__main__':
    keep_alive()
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    if RadarConfig.TOKEN:
        bot.run(RadarConfig.TOKEN)
    else:
        print("❌ خطأ: التوكن غير موجود!")
