# --- معالجة صورة الترحيب من ملف محلي ---
async def create_welcome_card(member):
    try:
        # فتح الصورة اللي سميتها welcome.png من ملفات البوت
        background = Image.open("welcome.png").convert("RGBA")
        
        # تحميل صورة العضو
        pfp_bytes = await member.display_avatar.read()
        pfp = Image.open(io.BytesIO(pfp_bytes)).convert("RGBA")
        pfp = pfp.resize((235, 235)) # مقاس الدائرة في الصورة
        
        # صنع قناع دائري عشان تطلع صورة العضو مدورة
        mask = Image.new('L', (235, 235), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 235, 235), fill=255)
        
        # دمج صورة العضو فوق الخلفية (الإحداثيات 135, 33 هي مكان الدائرة السوداء)
        background.paste(pfp, (135, 33), mask)
        
        buf = io.BytesIO()
        background.save(buf, format='PNG')
        buf.seek(0)
        return discord.File(buf, filename='welcome_radarz.png')
    except Exception as e:
        print(f"Error creating welcome image: {e}")
        return None

# --- حدث دخول الأعضاء ---
@bot.event
async def on_member_join(member):
    ch = member.guild.get_channel(RadarConfig.WELCOME_CHANNEL_ID)
    if ch:
        file = await create_welcome_card(member)
        # النص اللي طلبته بالضبط مع المنشن والإيموجي
        msg = (f"_'Have fun in **__Radarz __**_\n"
               f"_'User: {member.mention}_<a:Via1:1378238620418183188>")
        
        if file:
            await ch.send(content=msg, file=file)
        else:
            await ch.send(content=msg) # يرسل الكلام لو صار خطأ في الصورة
