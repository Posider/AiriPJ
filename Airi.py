import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import os
from collections import defaultdict, deque

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not DISCORD_TOKEN or not GOOGLE_API_KEY:
    raise EnvironmentError("❌ Missing necessary environment variables.")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

promptpay = """คุณคือ “Airi” (ไอริ) บอทสาวน้อยอายุ 16 ปี...
(ย่อไว้เพื่อความกระชับ – ใช้เหมือนเดิมได้เลยค่า~)
"""

history_data = defaultdict(lambda: deque(maxlen=10))
latest_channel_id = None  # 👈 จำห้องล่าสุดที่ใช้บอท

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} เปิดใช้งาน AiriBot สำเร็จแล้วน้า~ 💖")

@bot.tree.command(name="reset", description="รีเซ็ตความจำของไอริ")
async def reset_memory(interaction: discord.Interaction):
    history_data[interaction.user.id].clear()
    await interaction.response.send_message("ไอริลืมเรื่องที่คุยกันแล้วน้า~ 💫 ถามใหม่ได้เลย~", ephemeral=True)

@bot.tree.command(name="create", description="สร้างห้องคุยใหม่ในเซิร์ฟเวอร์")
@app_commands.describe(name="ใส่ชื่อห้องที่จะสร้าง เช่น chill หรือ project-abc")
async def create_channel(interaction: discord.Interaction, name: str):
    global latest_channel_id
    guild = interaction.guild
    existing = discord.utils.get(guild.text_channels, name=name)

    if existing:
        await interaction.response.send_message(f"ห้อง `{name}` มีอยู่แล้วน้า~ 💡", ephemeral=True)
        latest_channel_id = existing.id  # อัปเดตห้องล่าสุดแม้มีอยู่แล้ว
    else:
        try:
            channel = await guild.create_text_channel(name)
            latest_channel_id = channel.id  # 🧠 จำห้องใหม่ไว้
            await interaction.response.send_message(f"สร้างห้อง `{name}` เรียบร้อยแล้วค่า~ 🏠", ephemeral=True)
            await channel.send("ไอริมาถึงแล้วน้า~ 💖 พร้อมคุยกับพี่แล้วค่า~")
        except discord.Forbidden:
            await interaction.response.send_message("ไอริไม่มีสิทธิ์สร้างห้องในที่นี่น้า~ 😢", ephemeral=True)

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
                    await message.reply("อุ้ย~ ไอริขอโทษค่า~ ตอนนี้หนูยังดูภาพ .gif ไม่ได้เลยน้า~ 😢")
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
        await message.reply(f"❌ ขอโทษค่า~ เกิดข้อผิดพลาดนิดนึงเลยน้า~\n```{str(e)}```")
        print(f"[ERROR] {str(e)}")

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)