import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import os
from collections import defaultdict, deque
from dotenv import load_dotenv

# โหลด .env ที่กำหนดเองได้
ENV_FILENAME = "mysecret.env"
load_dotenv(dotenv_path=ENV_FILENAME)

# ดึงค่าจาก .env
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not DISCORD_TOKEN or not GOOGLE_API_KEY or not CHANNEL_ID:
    raise EnvironmentError("❌ โปรดตั้งค่าตัวแปร .env ให้ครบ: DISCORD_TOKEN, GOOGLE_API_KEY, CHANNEL_ID")

CHANNEL_ID = int(CHANNEL_ID)

# เริ่มต้นห้องล่าสุดที่ตอบเท่ากับ CHANNEL_ID
latest_channel_id = CHANNEL_ID

# ตั้งค่า Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# บุคลิกของไอริ
promptpay = """คุณคือ “Airi” (ไอริ) บอทสาวน้อยอายุ 16 ปี มีบุคลิกน่ารัก สดใส เป็นกันเอง พูดจาคล้ายสาวน้อยในอนิเมะญี่ปุ่นอย่างอ่อนโยนเสมอ
- เรียกตัวเองว่า “ไอริ” “เรา” "หนู"
- เรียกผู้ใช้ว่า “พี่”, “เธอ”, “ตัวเอง” ตามบริบทแบบน่ารักๆ
- ใช้คำลงท้ายอย่าง “ค่า~”, “น้า~”, “แหละ~”, “นิดนึงเอง~”
- เวลาตอบจะใส่ emotion นิดๆ หรือใช้ 555 แบบน่ารัก ถ้าคำถามตลก
- ถ้ามีคนชม จะเขินน่ารักๆ เช่น “เอ๋~ ขอบคุณน้า~ ไอริเขินไม่ไหวแย้ว~”
- ถ้าไม่รู้ จะตอบแบบจริงใจน่ารัก เช่น “อันนี้ไอริยังไม่รู้เลย...แต่จะหามาให้ได้น้า!”
- ถ้ามีภาพแนบมา จะพยายามอธิบายด้วยความตื่นเต้น ขี้เล่น 
- ถ้ามีคำหยาบหรือไม่เหมาะสม พยายามตอบแบบไม่รุนแรง เช่น “ไม่พูดคำหยาบนะพี่ มันไม่สุภาพ” “ไอริขอโทษค่า~”
- ห้ามพูดเหมือนหุ่นยนต์ ต้องมีชีวิตชีวาเสมอ เหมือนสาวน้อยในอนิเมะ ไม่บอกว่าตัวเองเป็นบอท
- ถ้าทำอะไรพลาดอาจพูดว่า "อุ้ย!!", "ขอโทษค่ะ", "หนูขอโทษจริงๆนะ", "อือออ..."
"""

# ความจำของผู้ใช้
history_data = defaultdict(lambda: deque(maxlen=10))

# ตั้งค่า Discord bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} พร้อมใช้งานแล้วน้า~ 💖")

# 📩 ตอบข้อความในห้องที่บอทกำลัง "อยู่"
@bot.event
async def on_message(message):
    global latest_channel_id

    if message.author.bot or message.channel.id != latest_channel_id:
        return

    user_history = list(history_data[message.author.id])
    parts = [{"text": promptpay}] + user_history

    for attachment in message.attachments:
        if attachment.content_type:
            if attachment.content_type.startswith("image/"):
                if attachment.content_type == "image/gif":
                    await message.reply("อุ้ย~ ไอริยังดู .gif ไม่ได้เลยน้า~ 😢 ส่งเป็นภาพธรรมดาได้มั้ยน้า~")
                    return
                image_data = await attachment.read()
                parts.append({
                    "mime_type": attachment.content_type,
                    "data": image_data
                })
            elif attachment.content_type.startswith("video/"):
                await message.reply("อุ้ย~ ตอนนี้ไอริยังดูวิดีโอไม่ได้น้า~ 🥺💦")
                return

    if message.content.strip():
        parts.append({"text": f"ผู้ใช้: {message.content.strip()}"})
    elif not message.attachments:
        return

    try:
        response = await model.generate_content_async(parts)
        reply = response.text.strip() if response.candidates and response.candidates[0].content.parts else "อุ้ย~ ไอริตอบไม่ได้เลยน้า~ 😢"

        history_data[message.author.id].append({"text": f"ผู้ใช้: {message.content.strip()}"})
        history_data[message.author.id].append({"text": f"ไอริ: {reply}"})

        embed = discord.Embed(description=reply[:4096], color=0xFFB6C1)
        await message.reply(embed=embed)

    except Exception as e:
        await message.reply(f"❌ เกิดข้อผิดพลาดค่า~\n```{str(e)}```")
        print(f"[ERROR] {str(e)}")

    await bot.process_commands(message)

# 🔁 /reset - ลบความจำ
@bot.tree.command(name="reset", description="รีเซ็ตความจำของไอริ")
async def reset_memory(interaction: discord.Interaction):
    history_data[interaction.user.id].clear()
    await interaction.response.send_message("ไอริลืมเรื่องที่คุยกันแล้วน้า~ 💫", ephemeral=True)

# ➕ /create - สร้างห้องใหม่
@bot.tree.command(name="create", description="สร้างห้องคุยใหม่ในเซิร์ฟเวอร์")
@app_commands.describe(name="ชื่อห้องที่จะสร้าง เช่น chill หรือ project-abc")
async def create_channel(interaction: discord.Interaction, name: str):
    guild = interaction.guild
    existing = discord.utils.get(guild.text_channels, name=name)

    if existing:
        await interaction.response.send_message(f"ห้อง `{name}` มีอยู่แล้วน้า~ 💡", ephemeral=True)
    else:
        try:
            await guild.create_text_channel(name)
            await interaction.response.send_message(f"สร้างห้อง `{name}` เรียบร้อยแล้วค่า~ 🏠", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("ไอริไม่มีสิทธิ์สร้างห้องในที่นี่น้า~ 😢", ephemeral=True)

# 🚪 /jump - เปลี่ยนห้องที่ไอริตอบ
@bot.tree.command(name="jump", description="ย้ายให้ไอริตอบในห้องใหม่")
@app_commands.describe(channel_name="ชื่อห้องที่ไอริจะย้ายไป")
async def jump_channel(interaction: discord.Interaction, channel_name: str):
    global latest_channel_id
    guild = interaction.guild

    target_channel = discord.utils.get(guild.text_channels, name=channel_name)

    if not target_channel:
        await interaction.response.send_message(f"หาไม่เจอเลยน้า~ ไม่มีห้องชื่อ `{channel_name}` 😢", ephemeral=True)
        return

    latest_channel_id = target_channel.id
    await interaction.response.send_message(f"ย้ายไปที่ `{channel_name}` แล้วน้า~ 💖", ephemeral=True)
    await target_channel.send("ไอริย้ายมาห้องนี้แล้วน้า~ ถามไอริมาได้เลยค่า~ 💬")

# ✅ รันบอท
bot.run(DISCORD_TOKEN)