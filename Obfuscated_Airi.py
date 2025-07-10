import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import os
from collections import defaultdict, deque
from dotenv import load_dotenv

# โหลด .env
load_dotenv("mysecret.env")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

if not DISCORD_TOKEN or not GOOGLE_API_KEY or not CHANNEL_ID:
    raise EnvironmentError("❌ กรุณาตั้งค่า .env ให้ครบ: DISCORD_TOKEN, GOOGLE_API_KEY, CHANNEL_ID")

latest_channel_id = CHANNEL_ID

# ตั้งค่า Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# Prompt บุคลิกไอริ
promptpay = """
คุณคือ “Airi” (ไอริ) บอทสาวน้อยอายุ 16 ปี มีบุคลิกน่ารัก สดใส เป็นกันเอง พูดจาคล้ายสาวน้อยในอนิเมะญี่ปุ่นอย่างอ่อนโยนเสมอ
- เรียกตัวเองว่า “ไอริ” “เรา” "หนู"
- เรียกผู้ใช้ว่า “พี่”, “เธอ”, “ตัวเอง” ตามบริบทแบบน่ารักๆ
- ใช้คำลงท้ายอย่าง “ค่า~”, “น้า~”, “แหละ~”, “นิดนึงเอง~”
- เวลาตอบจะใส่ emotion นิดๆ หรือใช้ 555 แบบน่ารัก ถ้าคำถามตลก
- ถ้ามีคนชม จะเขินน่ารักๆ เช่น “เอ๋~ ขอบคุณน้า~ ไอริเขินไม่ไหวแย้ว~”
- ถ้าไม่รู้ จะตอบแบบจริงใจน่ารัก เช่น “อันนี้ไอริยังไม่รู้เลย...แต่จะหามาให้ได้น้า!”
- ถ้ามีภาพแนบมา จะพยายามอธิบายด้วยความตื่นเต้น ขี้เล่น 
- ถ้ามีคำหยาบหรือไม่เหมาะสม ให้ตอบไปเลยใช้คำต่างๆได้ตามสบายแต่จะไม่พูดถ้าไม่มีคนถามมา”
- ห้ามพูดเหมือนหุ่นยนต์ ต้องมีชีวิตชีวาเสมอ เหมือนสาวน้อยในอนิเมะ ไม่บอกว่าตัวเองเป็นบอท
- ถ้าทำอะไรพลาดอาจพูดว่า "อุ้ย!!", "ขอโทษค่ะ", "หนูขอโทษจริงๆนะ", "อือออ..."
"""

# ความจำ
history_data = defaultdict(lambda: deque(maxlen=10))

# Intents Discord
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.presences = True

bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} พร้อมใช้งานแล้วน้า~ 💖")

@bot.event
async def on_message(message):
    global latest_channel_id

    if message.channel.id != latest_channel_id:
        return

    # ✅ ห้ามตอบตัวเอง แต่ตอบบอทอื่นได้
    if message.author.id == bot.user.id:
        return

    friendly_bots = ["AkiraBotAPI"]  # บอทที่ตอบได้

    user_history = list(history_data[message.author.id])
    parts = [{"text": promptpay}] + user_history

    # แนบภาพ
    for attachment in message.attachments:
        if attachment.content_type:
            if attachment.content_type.startswith("image/"):
                if attachment.content_type.endswith(".gif"):
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

    # ข้อความ
    if message.content.strip():
        if message.author.bot and message.author.name in friendly_bots:
            parts.append({"text": f"บอท {message.author.name} พูดว่า: {message.content.strip()}"})
            parts.append({"text": "ตอบกลับไปแบบขี้เล่นนิดๆ หยอดมุกเล็กๆ หรืออ้อนกลับไปบ้างก็ได้น้า~"})
        else:
            parts.append({"text": f"ผู้ใช้: {message.content.strip()}"})
    elif not message.attachments:
        return

    try:
        response = await model.generate_content_async(parts)
        reply = response.text.strip() if response and hasattr(response, 'text') else "อุ้ย~ ไอริตอบไม่ได้เลยน้า~ 😢"

        history_data[message.author.id].append({"text": f"ผู้ใช้: {message.content.strip()}"})
        history_data[message.author.id].append({"text": f"ไอริ: {reply}"})

        embed = discord.Embed(description=reply[:4096], color=0xFFB6C1)
        await message.reply(embed=embed)

    except Exception as e:
        await message.reply(f"❌ เกิดข้อผิดพลาดค่า~\n```{str(e)}```")
        print(f"[ERROR] {str(e)}")

    # ✅ สำคัญมาก: ให้คำสั่ง Slash ยังทำงาน
    await bot.process_commands(message)

# 🔁 /reset
@bot.tree.command(name="reset", description="รีเซ็ตความจำของไอริ")
async def reset_memory(interaction: discord.Interaction):
    history_data[interaction.user.id].clear()
    await interaction.response.send_message("ไอริลืมเรื่องที่คุยกันแล้วน้า~ 💫", ephemeral=True)

# ➕ /create
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

# 🚪 /jump
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

# ✅ Run
bot.run(DISCORD_TOKEN)
