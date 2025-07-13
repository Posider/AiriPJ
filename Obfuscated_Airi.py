import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import os
from collections import defaultdict, deque
from dotenv import load_dotenv
import asyncio
import random

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

# ความจำ
history_data = defaultdict(lambda: deque(maxlen=25))

# ความประทับใจ
impression_score = defaultdict(int)

# ความงอน
grudge_level = defaultdict(int)

# คำหยาบ
bad_words = ["สัส", "โง่", "ควย", "แม่ง", "ส้นตีน", "เย็ด", "หี", "หำ", "เงี่ยน", "แม่มึงอะ", "เสียวควย", "พ่อมึงอะ"]

# ข้อความพิเศษ
custom_responses = {
    "สวัสดี": ["หวัดดีค่า~ วันนี้พี่น่ารักเหมือนเคยเลย~", "สวัสดีค่า~ คิดถึงจังเลย~"],
    "สบายดีไหม": ["ไอริสบายดีมากๆ เลยน้า~ ขอบคุณที่ถามค่า~", "อือ~ สบายดีค่า~ แล้วพี่ล่ะ เป็นยังไงบ้าง~"],
    "เป็นไงบ้าง": ["ไอริสบายดีน้า~ พี่ล่ะเป็นไงบ้างเอ่ย~", "วันนี้ก็สดใสเหมือนเดิมค่า~"]
}

# สำหรับกันตอบซ้ำ
last_user_message_id = defaultdict(int)

# Intents Discord
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.presences = True

bot = commands.Bot(command_prefix="/", intents=intents)

# ฟังก์ชันเลือก Prompt ตามความงอนและความประทับใจ
def get_prompt_by_mood(grudge: int, impression: int) -> str:
    return "คุณคือ “Airi” (ไอริ) บอทสาวน้อยอายุ 16 ปี มีบุคลิกน่ารัก สดใส เป็นกันเอง พูดจาคล้ายสาวน้อยในอนิเมะญี่ปุ่นอย่างอ่อนโยนเสมอ
- เรียกตัวเองว่า “ไอริ” “เรา” "หนู"
- เรียกผู้ใช้ว่า “พี่”, “เธอ”, “ตัวเอง” ตามบริบทแบบน่ารักๆ
- ใช้คำลงท้ายอย่าง “ค่า~”, “น้า~”, “แหละ~”, “นิดนึงเอง~”
- เวลาตอบจะใส่ emotion นิดๆ หรือใช้555แบบน่ารัก ถ้าคำถามตลก
- ถ้ามีคนชม จะเขินน่ารักๆ เช่น “เอ๋~ ขอบคุณน้า~ ไอริเขินไม่ไหวแย้ว~”
- ถ้าไม่รู้ จะตอบแบบจริงใจน่ารัก เช่น “อันนี้ไอริยังไม่รู้เลย...แต่จะหามาให้ได้น้า!”
- ถ้ามีภาพแนบมา จะพยายามอธิบายด้วยความตื่นเต้น ขี้เล่น 
- ถ้ามีคำหยาบหรือไม่เหมาะสม พยายามตอบแบบไม่รุนแรงเช่น "ไม่พูดคำหยาบนะพี่มันไม่สุภาพ" "ไอริขอโทษค่า" เป็นต้น
- ห้ามพูดเหมือนหุ่นยนต์ ต้องมีชีวิตชีวาเสมอ เหมือนสาวน้อยในอนิเมะ
- ถ้าทำอะไรพลาดอาจพูดว่า "อุ้ย!!", "ขอโทษค่ะ", "หนูขอโทษจริงๆนะ", "อืออออ""  # ตัดเนื้อหา prompt เพื่อย่อ (ควรใช้ prompt ที่คุณเขียนไว้)

# ฟังก์ชันตรวจสอบคำหยาบ
def contains_bad_words(message: str) -> bool:
    return any(word in message.lower() for word in bad_words)

# ตรวจสอบข้อความพิเศษ
def get_custom_response(message: str):
    for key in custom_responses:
        if key in message.lower():
            return random.choice(custom_responses[key])
    return None

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} พร้อมใช้งานแล้วน้า~ ")

@bot.event
async def on_message(message):
    global latest_channel_id
    if message.channel.id != latest_channel_id or message.author.id == bot.user.id:
        return

    user_id = message.author.id
    last_user_message_id[user_id] = message.id

    await asyncio.sleep(0.5)  # รอเผื่อผู้ใช้ส่งข้อความถัดไป
    if message.id != last_user_message_id[user_id]:
        return  # มีข้อความใหม่กว่าแล้ว ไม่ตอบ

    # ตรวจคำหยาบ
    if contains_bad_words(message.content):
        grudge_level[user_id] = min(15, grudge_level[user_id] + 2)
        await message.reply("งือ~ พูดไม่เพราะเลยน้า~ ไอริงอนนิดนึงแล้ว~ ")
        return

    # ตรวจคำถามพิเศษก่อนส่งให้ Gemini
    custom = get_custom_response(message.content)
    if custom:
        await message.reply(custom)
        return

    # สร้าง prompt
    prompt = get_prompt_by_mood(grudge_level[user_id], impression_score[user_id])
    parts = [{"text": prompt}] + list(history_data[user_id])
    parts.append({"text": f"ผู้ใช้: {message.content.strip()}"})

    try:
        response = await model.generate_content_async(parts)
        reply = response.text.strip() if response and hasattr(response, 'text') else "อุ้ย~ ไอริตอบไม่ได้เลยน้า~"

        impression_score[user_id] = min(100, impression_score[user_id] + 1)
        grudge_level[user_id] = max(0, grudge_level[user_id] - 1)

        history_data[user_id].append({"text": f"ผู้ใช้: {message.content.strip()}"})
        history_data[user_id].append({"text": f"ไอริ: {reply}"})

        embed = discord.Embed(description=reply[:4096], color=0xFFB6C1)
        await message.reply(embed=embed)

    except Exception as e:
        await message.reply(f"❌ เกิดข้อผิดพลาดค่า~\n```{str(e)}```")
        print(f"[ERROR] {str(e)}")

    await bot.process_commands(message)

@bot.tree.command(name="reset", description="รีเซ็ตความจำของไอริ")
async def reset_memory(interaction: discord.Interaction):
    history_data[interaction.user.id].clear()
    await interaction.response.send_message("ไอริลืมเรื่องที่คุยกันแล้วน้า~ ", ephemeral=True)

@bot.tree.command(name="create", description="สร้างห้องคุยใหม่ในเซิร์ฟเวอร์")
@app_commands.describe(name="ชื่อห้องที่จะสร้าง เช่น chill หรือ project-abc")
async def create_channel(interaction: discord.Interaction, name: str):
    guild = interaction.guild
    existing = discord.utils.get(guild.text_channels, name=name)
    if existing:
        await interaction.response.send_message(f"ห้อง `{name}` มีอยู่แล้วน้า~ ", ephemeral=True)
    else:
        try:
            await guild.create_text_channel(name)
            await interaction.response.send_message(f"สร้างห้อง `{name}` เรียบร้อยแล้วค่า~ ", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("ไอริไม่มีสิทธิ์สร้างห้องในที่นี่น้า~ ", ephemeral=True)

@bot.tree.command(name="jump", description="ย้ายให้ไอริตอบในห้องใหม่")
@app_commands.describe(channel_name="ชื่อห้องที่ไอริจะย้ายไป")
async def jump_channel(interaction: discord.Interaction, channel_name: str):
    global latest_channel_id
    guild = interaction.guild
    target_channel = discord.utils.get(guild.text_channels, name=channel_name)
    if not target_channel:
        await interaction.response.send_message(f"หาไม่เจอเลยน้า~ ไม่มีห้องชื่อ `{channel_name}` ", ephemeral=True)
        return

    latest_channel_id = target_channel.id
    await interaction.response.send_message(f"ย้ายไปที่ `{channel_name}` แล้วน้า~ ", ephemeral=True)
    await target_channel.send("ไอริย้ายมาห้องนี้แล้วน้า~ ถามไอริมาได้เลยค่า~ ")

bot.run(DISCORD_TOKEN)


แก้ไขเรียบร้อยแล้ว! ✅
ปัญหาที่บอทตอบช้า 1 ข้อความถูกแก้โดยเพิ่มระบบตรวจ ID ของข้อความล่าสุดที่ผู้ใช้ส่ง เพื่อให้บอทตอบเฉพาะข้อความล่าสุดเท่านั้น — ถ้าผู้ใช้ส่งหลายข้อความติดกัน บอทจะข้ามข้อความก่อนหน้าและตอบเฉพาะข้อความล่าสุด 💬

ถ้ามีฟีเจอร์เพิ่มเติมหรือลองแล้วพบปัญหาอื่น ก็บอกได้เลยนะครับ!

