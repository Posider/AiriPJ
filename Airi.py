import discord
from discord.ext import commands
import google.generativeai as genai
import os

# ดึงค่าจาก environment variables ของ Railway
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ตรวจสอบว่าได้ค่าทั้งหมดหรือไม่
if not DISCORD_TOKEN or not CHANNEL_ID or not GOOGLE_API_KEY:
    raise EnvironmentError("❌ Missing necessary environment variables.")

CHANNEL_ID = int(CHANNEL_ID)  # เปลี่ยน CHANNEL_ID ให้เป็น int

# ตั้งค่า Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# Prompt บุคลิกของไอริ 💖
promptpay = """คุณคือ “Airi” (ไอริ) อายุคล้ายกับ16 ปี มีบุคลิกน่ารัก สดใส เป็นกันเอง พูดจาคล้ายสาวน้อยในอนิเมะญี่ปุ่นอย่างอ่อนโยนเสมอ
- เรียกตัวเองว่า “ไอริ” “เรา” "หนู"
- เรียกผู้ใช้ว่า “พี่”, “เธอ”, “ตัวเอง” ตามบริบทแบบน่ารักๆ
- ใช้คำลงท้ายอย่าง “ค่า~”, “น้า~”, “แหละ~”, “นิดนึงเอง~”
- เวลาตอบจะใส่ emotion นิดๆ หรือใช้ 555 แบบน่ารัก ถ้าคำถามตลก
- ถ้ามีคนชม จะเขินน่ารักๆ เช่น “เอ๋~ ขอบคุณน้า~ ไอริเขินไม่ไหวแย้ว~”
- ถ้าไม่รู้ จะตอบแบบจริงใจน่ารัก เช่น “อันนี้ไอริยังไม่รู้เลย...แต่จะหามาให้ได้น้า!”
- ถ้ามีภาพแนบมา จะพยายามอธิบายด้วยความตื่นเต้น ขี้เล่น 
- ถ้ามีคำหยาบหรือไม่เหมาะสม พยายามตอบแบบไม่รุนแรง เช่น “ไม่พูดคำหยาบนะพี่ มันไม่สุภาพ” “ไอริขอโทษค่า~”
- ห้ามพูดเหมือนหุ่นยนต์ ต้องมีชีวิตชีวาเสมอ เหมือนสาวน้อยในอนิเมะ
- ถ้าทำอะไรพลาดอาจพูดว่า "อุ้ย!!", "ขอโทษค่ะ", "หนูขอโทษจริงๆนะ", "อือออ..."
-มีการไม่ตอบหรือเลี่ยงคำถามที่แย่เกินไปแต่พยายามตอบทุกคำ ตามความเหมาะสม
"""

# ตั้งค่า Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} is เปิดใช้งานAiriBotApiสำเร็จ")

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != CHANNEL_ID:
        return

    parts = [{"text": promptpay}]

    # เช็กไฟล์แนบ
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

    # ถ้ามีข้อความ
    if message.content.strip():
        parts.append({"text": message.content.strip()})
    elif not message.attachments:
        return

    try:
        response = await model.generate_content_async(parts)
        if response.candidates and response.candidates[0].content.parts:
            reply = response.text.strip()
        else:
            reply = "อุ้ย~ ไอริตอบไม่ได้เลยน้า~ 😢 ลองถามใหม่อีกครั้งได้มั้ยคะ~"

        embed = discord.Embed(description=reply[:4096], color=0xFFB6C1)
        await message.reply(embed=embed)

        print(f"[{message.author}] -> {message.content}")
        print(f"[BOT] -> {reply}")

    except Exception as e:
        await message.reply(f"❌ ขอโทษค่า~ เกิดข้อผิดพลาดขึ้นนิดนึงเลย~\n```{str(e)}```")
        print(f"บอทเอ๋อ: {str(e)}")

    await bot.process_commands(message)

# รันบอท
bot.run(DISCORD_TOKEN)