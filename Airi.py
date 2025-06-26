import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import os
from collections import defaultdict, deque

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not DISCORD_TOKEN or not CHANNEL_ID or not GOOGLE_API_KEY:
    raise EnvironmentError("❌ Missing necessary environment variables.")

CHANNEL_ID = int(CHANNEL_ID)

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

promptpay = """คุณคือ “Airi” (ไอริ) อายุคล้ายกับ16 ปี มีบุคลิกน่ารัก สดใส เป็นกันเอง... (ตัดทอนตามที่คุณเขียนไว้ได้เลย)"""

history_data = defaultdict(lambda: deque(maxlen=10))

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} เปิดใช้งาน AiriBot สำเร็จแล้วน้า~ 💖")

### 🔁 /reset – ลบความจำ
@bot.tree.command(name="reset", description="รีเซ็ตความจำของไอริ")
async def reset_memory(interaction: discord.Interaction):
    history_data[interaction.user.id].clear()
    await interaction.response.send_message("ไอริลืมเรื่องที่คุยกันแล้วน้า~ 💫 ถามใหม่ได้เลย~", ephemeral=True)

### 🆕 /create_ชื่อห้อง – สร้างห้องใหม่
@bot.tree.command(name="create", description="สร้างห้องคุยใหม่ในเซิร์ฟเวอร์")
@app_commands.describe(name="ใส่ชื่อห้องที่จะสร้าง เช่น chill หรือ project-abc")
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

### 📩 ตอบแชต
@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != CHANNEL_ID:
        return

    user_history = list(history_data[message.author.id])
    parts = [{"text": promptpay}] + user_history

    for attachment in message.attachments:
        if attachment.content_type:
            if attachment.content_type.startswith("image/"):
                if attachment.content_type == "image/gif":
                    await message.reply("อุ้ย~ ไอริขอโทษค่า~ ตอนนี้หนูยังดูภาพ .gif ไม่ได้เลยน้า~ 😢 ลองส่งเป็นภาพธรรมดาแทนได้มั้ยน้า~ 💖")
                    return
                image_data = await attachment.read()
                parts.append({
                    "mime_type": attachment.content_type,
                    "data": image_data
                })
            elif attachment.content_type.startswith("video/"):
                await message.reply("อุ้ย~ พี่ส่งวิดีโอมาเหรอคะ~ 😳 ตอนนี้ไอริยังดูวิดีโอไม่ได้น้า~ ขอโทษด้วยค่า~ 🥺💦")
                return

    if message.content.strip():
        parts.append({"text": f"ผู้ใช้: {message.content.strip()}"})
    elif not message.attachments:
        return

    try:
        response = await model.generate_content_async(parts)
        if response.candidates and response.candidates[0].content.parts:
            reply = response.text.strip()
        else:
            reply = "อุ้ย~ ไอริตอบไม่ได้เลยน้า~ 😢 ลองถามใหม่อีกครั้งได้มั้ยคะ~"

        history_data[message.author.id].append({"text": f"ผู้ใช้: {message.content.strip()}"})
        history_data[message.author.id].append({"text": f"ไอริ: {reply}"})

        embed = discord.Embed(description=reply[:4096], color=0xFFB6C1)
        await message.reply(embed=embed)

        print(f"[{message.author}] -> {message.content}")
        print(f"[BOT] -> {reply}")

    except Exception as e:
        await message.reply(f"❌ ขอโทษค่า~ เกิดข้อผิดพลาดนิดนึงเลยน้า~\n```{str(e)}```")
        print(f"บอทเอ๋อ: {str(e)}")

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
