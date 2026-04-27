import asyncio, os, re, discord, datetime
from discord.ext import commands, tasks
from discord import app_commands
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# --- نظام الاستضافة ---
app = Flask('')
@app.route('/')
def home(): return "RADARZ Logs Active"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run); t.daemon = True; t.start()

# --- الإعدادات العامة ---
class RadarConfig:
    TOKEN = os.getenv('DISCORD_TOKEN')
    LOGS_ROOM_ID = 1498422633669197904 # روم اللوجات المعتمد
    STREAM_CHANNEL_ID = 1200740059817721856
    YOUTUBE_CHANNEL_ID = 924316521050820609
    STATS_CATEGORY_ID = 1494627032112304179
    AUTHORIZED_USERS = [1341796578742243338, 551817782996762624, 366132848228564992, 1376970309797941372, 1342856146662461574]

class RadarBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    
    async def on_ready(self):
        await self.tree.sync()
        print(f"📡 {self.user} Online - Radar Active")

    # --- 1. مراقبة الرسائل (عضو أو إداري) ---
    async def on_message_delete(self, message):
        if message.author.bot: return
        log_ch = self.get_channel(RadarConfig.LOGS_ROOM_ID)
        if log_ch:
            embed = discord.Embed(title="🗑️ رسالة محذوفة", color=discord.Color.red(), timestamp=datetime.now())
            embed.add_field(name="الكاتب:", value=f"{message.author.mention} ({message.author})")
            embed.add_field(name="القناة:", value=message.channel.mention)
            embed.add_field(name="المحتوى:", value=message.content or "ملف/صورة", inline=False)
            await log_ch.send(embed=embed)

    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content: return
        log_ch = self.get_channel(RadarConfig.LOGS_ROOM_ID)
        if log_ch:
            embed = discord.Embed(title="📝 رسالة معدلة", color=discord.Color.orange(), timestamp=datetime.now())
            embed.add_field(name="الكاتب:", value=before.author.mention)
            embed.add_field(name="قبل:", value=before.content, inline=False)
            embed.add_field(name="بعد:", value=after.content, inline=False)
            await log_ch.send(embed=embed)

    # --- 2. مراقبة الرومات والسيرفر (إضافة/حذف/تعديل) ---
    async def on_guild_channel_create(self, channel):
        log_ch = self.get_channel(RadarConfig.LOGS_ROOM_ID)
        if log_ch:
            await log_ch.send(f"🆕 **تم إنشاء روم جديد:** {channel.name} ({channel.mention})")

    async def on_guild_channel_delete(self, channel):
        log_ch = self.get_channel(RadarConfig.LOGS_ROOM_ID)
        if log_ch:
            await log_ch.send(f"❌ **تم حذف روم:** {channel.name}")

    async def on_guild_update(self, before, after):
        log_ch = self.get_channel(RadarConfig.LOGS_ROOM_ID)
        if log_ch and before.name != after.name:
            await log_ch.send(f"⚙️ **تم تغيير اسم السيرفر من:** {before.name} **إلى:** {after.name}")

    # --- 3. مراقبة أفعال الإداريين (طرد/باند/تايم أوت) ---
    async def on_audit_log_entry_create(self, entry):
        log_ch = self.get_channel(RadarConfig.LOGS_ROOM_ID)
        if not log_ch: return

        # طرد
        if entry.action == discord.AuditLogAction.kick:
            embed = discord.Embed(title="👞 طرد عضو", color=discord.Color.dark_orange(), timestamp=datetime.now())
            embed.add_field(name="الإداري:", value=entry.user.mention)
            embed.add_field(name="المطرود:", value=entry.target.mention)
            await log_ch.send(embed=embed)

        # باند
        elif entry.action == discord.AuditLogAction.ban:
            embed = discord.Embed(title="🚫 حظر (باند)", color=discord.Color.dark_red(), timestamp=datetime.now())
            embed.add_field(name="الإداري:", value=entry.user.mention)
            embed.add_field(name="المحظور:", value=entry.target.mention)
            await log_ch.send(embed=embed)

        # تايم أوت (سجن)
        elif entry.action == discord.AuditLogAction.member_update:
            if hasattr(entry.after, 'timeout_until'):
                embed = discord.Embed(title="⏳ تايم أوت (سجن)", color=discord.Color.blue(), timestamp=datetime.now())
                embed.add_field(name="الإداري:", value=entry.user.mention)
                embed.add_field(name="العضو:", value=entry.target.mention)
                await log_ch.send(embed=embed)

# --- بقية الدوال (Panel, Buttons, Youtube) من كودك الأصلي تبقى كما هي ---
# ... (يمكنك إضافتها هنا ليكون الملف كاملاً)

bot = RadarBot()

if __name__ == '__main__':
    keep_alive()
    bot.run(RadarConfig.TOKEN)
