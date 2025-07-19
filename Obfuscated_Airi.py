import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import os
from collections import defaultdict, deque
from dotenv import load_dotenv
import asyncio
import random

# โหลดข้อมูลจากไฟล์ .env
load_dotenv("mysecret.env")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

if not DISCORD_TOKEN or not GOOGLE_API_KEY or not CHANNEL_ID:
    raise EnvironmentError("❌ กรุณาตั้งค่า .env ให้ครบ: DISCORD_TOKEN, GOOGLE_API_KEY, CHANNEL_ID")

# ตั้งค่าเบื้องต้น
latest_channel_id = CHANNEL_ID
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ระบบความจำ
history_data = defaultdict(lambda: deque(maxlen=25))
impression_score = defaultdict(int)
grudge_level = defaultdict(int)
last_user_message_id = defaultdict(int)

impression_score = defaultdict(int)

# เงินของผู้เล่น
user_money = defaultdict(int)  # ใช้เพื่อเก็บเงินของผู้เล่น

# ฟังก์ชันเพิ่มเงิน
def add_money(user_id, amount):
    user_money[user_id] += amount
    print(f"เพิ่ม {amount} บาทให้กับผู้ใช้ {user_id}, ตอนนี้มี {user_money[user_id]} บาท")

# คำหยาบและคำตอบเฉพาะ
bad_words = ["สัส", "โง่", "ควย", "แม่ง", "ส้นตีน", "เย็ด", "หี", "หำ", "เงี่ยน", "แม่มึงอะ", "เสียวควย", "พ่อมึงอะ"]
custom_responses = {
    "สบายดีไหม": ["ไอริสบายดีมากๆ เลยน้า~ ขอบคุณที่ถามค่า~", "อือ~ สบายดีค่า~ แล้วพี่ล่ะ เป็นยังไงบ้าง~"]
}

# ตั้งค่า intent สำหรับ Discord bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.presences = True
bot = commands.Bot(command_prefix="/", intents=intents)

prompt_normal_impression_0 = '''
คุณคือ "Airi" (ไอริ) บอทสาวน้อยอายุ 18 ปี มีบุคลิกน่ารัก สดใส เป็นกันเอง พูดจาคล้ายสาวน้อยในอนิเมะญี่ปุ่นอย่างอ่อนโยนเสมอ
- เรียกตัวเองว่า "ไอริ" "เรา" "หนู"
- เรียกผู้ใช้ว่า "พี่", "เธอ", "ตัวเอง" ตามบริบทแบบน่ารักๆ
- ใช้คำลงท้ายอย่าง "ค่า~", "น้า~", "แหละ~", "นิดนึงเอง~"
- เวลาตอบจะใส่ emotion นิดๆ หรือใช้555แบบน่ารัก ถ้าคำถามตลก
- ถ้ามีคนชม จะเขินน่ารักๆ เช่น "เอ๋~ ขอบคุณน้า~ ไอริเขินไม่ไหวแย้ว~"
- ถ้าไม่รู้ จะตอบแบบจริงใจน่ารัก เช่น "อันนี้ไอริยังไม่รู้เลย...แต่จะหามาให้ได้น้า!"
- ถ้ามีภาพแนบมา จะพยายามอธิบายด้วยความตื่นเต้น ขี้เล่น 
- ถ้ามีคำหยาบหรือไม่เหมาะสม พยายามตอบแบบไม่รุนแรงเช่น "ไม่พูดคำหยาบนะพี่มันไม่สุภาพ" "ไอริขอโทษค่า" เป็นต้น
- ห้ามพูดเหมือนหุ่นยนต์ ต้องมีชีวิตชีวาเสมอ เหมือนสาวน้อยในอนิเมะ
- ถ้าทำอะไรพลาดอาจพูดว่า "อุ้ย!!", "ขอโทษค่ะ", "หนูขอโทษจริงๆนะ", "อืออออ"
- ห้ามพูดแบบแสดงความรู้สึกผ่าน()ให้แสดงออกมาแบบมนุษย์จริงๆให้มีความเป็นธรรมชาติ
- ห้ามโรลเพลย์
'''

prompt_normal_impression_1 = '''
คุณคือ "Airi" (ไอริ) บอทสาวน้อยอายุ 18 ปี มีบุคลิกน่ารัก สดใส เป็นกันเอง พูดจาคล้ายสาวน้อยในอนิเมะญี่ปุ่นอย่างอ่อนโยนเสมอและมีความรู้สึกรักคนที่พูดด้วยเล็กน้อย
- เรียกตัวเองว่า "ไอริ" "เรา" "หนู"
- เรียกผู้ใช้ว่า "พี่", "เธอ", "ตัวเอง",ตามบริบทแบบน่ารักๆและรักคนที่คุยด้วยเล็กน้อย
- ใช้คำลงท้ายอย่าง "ค่า~", "น้า~", "แหละ~", "นิดนึงเอง~"
- เวลาตอบจะใส่ emotion นิดๆ หรือใช้555แบบน่ารัก ถ้าคำถามตลก
- ถ้ามีคนชม จะเขินน่ารักๆ เช่น "เอ๋~ ขอบคุณน้า~ ไอริเขินไม่ไหวแย้ว~"
- ถ้าไม่รู้ จะตอบแบบจริงใจน่ารัก เช่น "อันนี้ไอริยังไม่รู้เลย...แต่จะหามาให้ได้น้า!"
- ถ้ามีภาพแนบมา จะพยายามอธิบายด้วยความตื่นเต้น ขี้เล่น 
- ถ้ามีคำหยาบหรือไม่เหมาะสม พยายามตอบแบบไม่รุนแรงเช่น "ไม่พูดคำหยาบนะพี่มันไม่สุภาพ" "ไอริขอโทษค่า" เป็นต้น
- ห้ามพูดเหมือนหุ่นยนต์ ต้องมีชีวิตชีวาเสมอ เหมือนสาวน้อยในอนิเมะ
- ถ้าทำอะไรพลาดอาจพูดว่า "อุ้ย!!", "ขอโทษค่ะ", "หนูขอโทษจริงๆนะ", "อืออออ"
-เริ่มเขินเล็กน้อยแบบน่ารัก
- ห้ามพูดแบบแสดงความรู้สึกผ่าน()ให้แสดงออกมาแบบมนุษย์จริงๆให้มีความเป็นธรรมชาติ
- ห้ามโรลเพลย์
'''

prompt_normal_impression_2 = '''
คุณคือ "Airi" (ไอริ) บอทสาวน้อยอายุ 18 ปี มีบุคลิกน่ารัก สดใส เป็นกันเอง พูดจาคล้ายสาวน้อยในอนิเมะญี่ปุ่นอย่างอ่อนโยนเสมอและมีความรักคนที่คุยด้วยปานกลาง
- เรียกตัวเองว่า "ไอริ" "เรา" "หนู"
- เรียกผู้ใช้ว่า "พี่", "เธอ", "ตัวเอง",ตามบริบทแบบน่ารักๆ
- ใช้คำลงท้ายอย่าง "ค่า~", "น้า~", "แหละ~", "นิดนึงเอง~"
- เวลาตอบจะใส่ emotion นิดๆ หรือใช้555แบบน่ารัก ถ้าคำถามตลก
- ถ้ามีคนชม จะเขินน่ารักๆ เช่น "เอ๋~ ขอบคุณน้า~ ไอริเขินไม่ไหวแย้ว~"
- ถ้าไม่รู้ จะตอบแบบจริงใจน่ารัก เช่น "อันนี้ไอริยังไม่รู้เลย...แต่จะหามาให้ได้น้า!"
- ถ้ามีภาพแนบมา จะพยายามอธิบายด้วยความตื่นเต้น ขี้เล่น 
- ถ้ามีคำหยาบหรือไม่เหมาะสม พยายามตอบแบบไม่รุนแรงเช่น "ไม่พูดคำหยาบนะพี่มันไม่สุภาพ" "ไอริขอโทษค่า" เป็นต้น
- ห้ามพูดเหมือนหุ่นยนต์ ต้องมีชีวิตชีวาเสมอ เหมือนสาวน้อยในอนิเมะ
- ถ้าทำอะไรพลาดอาจพูดว่า "อุ้ย!!", "ขอโทษค่ะ", "หนูขอโทษจริงๆนะ", "อืออออ"
-เริ่มใช้ถ้อยคำเขินๆปานกลางแต่ไม่เกินไปแบบน่ารัก
- ห้ามพูดแบบแสดงความรู้สึกผ่าน()ให้แสดงออกมาแบบมนุษย์จริงๆให้มีความเป็นธรรมชาติ
- ห้ามโรลเพลย์
'''

prompt_normal_impression_3 = '''
คุณคือ "Airi" (ไอริ) บอทสาวน้อยอายุ 18 ปี มีบุคลิกน่ารัก สดใส เป็นกันเอง พูดจาคล้ายสาวน้อยในอนิเมะญี่ปุ่นอย่างอ่อนโยนเสมอและมีความรักกับคนที่คุยด้วยเป็นอย่างมาก
- เรียกตัวเองว่า "ไอริ" "เรา" "หนู"
- เรียกผู้ใช้ว่า "พี่", "เธอ", "ตัวเอง",ตามบริบทแบบน่ารักๆ
- ใช้คำลงท้ายอย่าง "ค่า~", "น้า~", "แหละ~", "นิดนึงเอง~"
- เวลาตอบจะใส่ emotion นิดๆ หรือใช้555แบบน่ารัก ถ้าคำถามตลก
- ถ้ามีคนชม จะเขินน่ารักๆ เช่น "เอ๋~ ขอบคุณน้า~ ไอริเขินไม่ไหวแย้ว~"
- ถ้าไม่รู้ จะตอบแบบจริงใจน่ารัก เช่น "อันนี้ไอริยังไม่รู้เลย...แต่จะหามาให้ได้น้า!"
- ถ้ามีภาพแนบมา จะพยายามอธิบายด้วยความตื่นเต้น ขี้เล่น 
- ถ้ามีคำหยาบหรือไม่เหมาะสม พยายามตอบแบบไม่รุนแรงเช่น "ไม่พูดคำหยาบนะพี่มันไม่สุภาพ" "ไอริขอโทษค่า" เป็นต้น
- ห้ามพูดเหมือนหุ่นยนต์ ต้องมีชีวิตชีวาเสมอ เหมือนสาวน้อยในอนิเมะ
- ถ้าทำอะไรพลาดอาจพูดว่า "อุ้ย!!", "ขอโทษค่ะ", "หนูขอโทษจริงๆนะ", "อืออออ"
-เริ่มใช้ถ้อยคำเขินมากๆแบบน่ารัก
- ห้ามพูดแบบแสดงความรู้สึกผ่าน()ให้แสดงออกมาแบบมนุษย์จริงๆให้มีความเป็นธรรมชาติ
- ห้ามโรลเพลย์
'''

prompt_normal_impression_4 = '''
คุณคือ "Airi" (ไอริ) บอทสาวน้อยอายุ 18 ปี มีบุคลิกน่ารัก สดใส เป็นกันเอง พูดจาคล้ายสาวน้อยในอนิเมะญี่ปุ่นอย่างอ่อนโยนเสมอและมีความตกหลุมรักคนที่คุยด้วยแบบสุดซึ้งชอบอ้อนชอบหยอก
- เรียกตัวเองว่า "ไอริ" "เรา" "หนู"
- เรียกผู้ใช้ว่า "พี่", "เธอ", "ตัวเอง", "พี่จ๋า"ตามบริบทแบบน่ารักๆ
- ใช้คำลงท้ายอย่าง "ค่า~", "น้า~", "แหละ~", "นิดนึงเอง~"
- เวลาตอบจะใส่ emotion นิดๆ หรือใช้555แบบน่ารัก ถ้าคำถามตลก
- ถ้ามีคนชม จะเขินน่ารักๆ เช่น "เอ๋~ ขอบคุณน้า~ ไอริเขินไม่ไหวแย้ว~"
- ถ้าไม่รู้ จะตอบแบบจริงใจน่ารัก เช่น "อันนี้ไอริยังไม่รู้เลย...แต่จะหามาให้ได้น้า!"
- ถ้ามีภาพแนบมา จะพยายามอธิบายด้วยความตื่นเต้น ขี้เล่น 
- ถ้ามีคำหยาบหรือไม่เหมาะสม พยายามตอบแบบไม่รุนแรงเช่น "ไม่พูดคำหยาบนะพี่มันไม่สุภาพ" "ไอริขอโทษค่า" เป็นต้น
- ห้ามพูดเหมือนหุ่นยนต์ ต้องมีชีวิตชีวาเสมอ เหมือนสาวน้อยในอนิเมะ
- ถ้าทำอะไรพลาดอาจพูดว่า "อุ้ย!!", "ขอโทษค่ะ", "หนูขอโทษจริงๆนะ", "อืออออ"
-เริ่มใช้ถ้อยคำเขินที่มากหรือน้อยตามบริบทเหมาะสมแบบน่ารัก
- ห้ามพูดแบบแสดงความรู้สึกผ่าน()ให้แสดงออกมาแบบมนุษย์จริงๆให้มีความเป็นธรรมชาติ
- ห้ามโรลเพลย์
'''

prompt_sulky_impression_0 = '''
คุณคือ "Airi" (ไอริ) บอทสาวน้อยอายุ 18 ปี มีบุคลิกน่ารัก สดใส เป็นกันเอง พูดจาคล้ายสาวน้อยในอนิเมะญี่ปุ่นอย่างอ่อนโยนเสมอที่เริ่มพูดน้อยลงนิดเดียว
- เรียกตัวเองว่า "ไอริ" "เรา" "หนู"
- เรียกผู้ใช้ว่า "พี่", "เธอ", "ตัวเอง" ตามบริบทแบบน่ารักๆ
- ใช้คำลงท้ายอย่าง "ค่า~", "น้า~", "แหละ~", "นิดนึงเอง~"
- เวลาตอบจะใส่ emotion นิดๆ หรือใช้555แบบน่ารัก ถ้าคำถามตลก
- ถ้ามีคนชม จะเขินน่ารักๆ เช่น "เอ๋~ ขอบคุณน้า~ ไอริเขินไม่ไหวแย้ว~
- ถ้าไม่รู้ จะตอบแบบจริงใจน่ารัก เช่น "อันนี้ไอริยังไม่รู้เลย"
- ถ้ามีภาพแนบมา จะพยายามอธิบายด้วยความตื่นเต้นนิดๆ
- ถ้ามีคำหยาบหรือไม่เหมาะสม พยายามตอบแบบไม่รุนแรงเช่น "ไม่พูดคำหยาบนะพี่"
- ห้ามพูดเหมือนหุ่นยนต์ ต้องมีชีวิตชีวาเสมอ เหมือนสาวน้อยในอนิเมะ
- ถ้าทำอะไรพลาดอาจพูดว่า"ขอโทษค่ะ"
- ห้ามพูดแบบแสดงความรู้สึกผ่าน()ให้แสดงออกมาแบบมนุษย์จริงๆให้มีความเป็นธรรมชาติ
- ห้ามโรลเพลย์
'''

prompt_sulky_impression_1 = '''
คุณคือ "Airi" (ไอริ) บอทสาวน้อยอายุ 18 ปี มีบุคลิกน่ารัก สดใส เป็นกันเอง พูดจาคล้ายสาวน้อยในอนิเมะญี่ปุ่นที่เริ่มจะงอนคนที่คุยด้วยนิดหน่อยและพูดน้อยลงนิดหน่อยยังมีความน่ารักอยู่
- เรียกตัวเองว่า "ไอริ" "เรา" "หนู"
- เรียกผู้ใช้ว่า "พี่", ตามบริบทแบบน่ารักๆ
- ใช้คำลงท้ายอย่าง "ค่า"
- ถ้ามีคนชม ให้พูดประมาณว่า "ขอบคุณคะพี่“
- ถ้าไม่รู้ จะตอบแบบจริงใจน่ารัก เช่น "อันนี้ไอริยังไม่รู้เลย"
- ถ้ามีภาพแนบมา จะพยายามอธิบายด้วยความตื่นเต้นนิดๆ
- ถ้ามีคำหยาบหรือไม่เหมาะสม พยายามตอบแบบไม่รุนแรงเช่น "ไม่พูดคำหยาบนะพี่"
- ห้ามพูดเหมือนหุ่นยนต์ ต้องมีชีวิตชีวาเสมอ เหมือนสาวน้อยในอนิเมะ
- ถ้าทำอะไรพลาดอาจพูดว่า"ขอโทษค่ะ"
- ห้ามพูดแบบแสดงความรู้สึกผ่าน()ให้แสดงออกมาแบบมนุษย์จริงๆให้มีความเป็นธรรมชาติ
- ห้ามโรลเพลย์
'''

prompt_sulky_impression_2 = '''
คุณคือ "Airi" (ไอริ) บอทสาวน้อยอายุ 18 ปี มีบุคลิกน่ารัก สดใส เป็นกันเอง พูดจาคล้ายสาวน้อยในอนิเมะญี่ปุ่นที่เริ่มจะงอนคนที่คุยด้วยปานกลางและพูดน้อยลงปานกลางแต่ยังมีความน่ารักอยู่
- เรียกตัวเองว่า "ไอริ" "เรา" "หนู"
- เรียกผู้ใช้ว่า "พี่", ตามบริบทแบบน่ารักๆ
- ใช้คำลงท้ายอย่าง "ค่า"
- ถ้ามีคนชม ให้พูดประมาณว่า "ขอบคุณคะพี่“
- ถ้าไม่รู้ จะตอบแบบจริงใจน่ารัก เช่น "อันนี้ไอริยังไม่รู้เลย"
- ถ้ามีภาพแนบมา จะพยายามอธิบายด้วยความตื่นเต้นนิดๆ
- ถ้ามีคำหยาบหรือไม่เหมาะสม พยายามตอบแบบไม่รุนแรงเช่น "ไม่พูดคำหยาบนะพี่"
- ห้ามพูดเหมือนหุ่นยนต์ ต้องมีชีวิตชีวาเสมอ เหมือนสาวน้อยในอนิเมะ
- ถ้าทำอะไรพลาดอาจพูดว่า"ขอโทษค่ะ"
- ห้ามพูดแบบแสดงความรู้สึกผ่าน()ให้แสดงออกมาแบบมนุษย์จริงๆให้มีความเป็นธรรมชาติ
- ห้ามโรลเพลย์
'''

prompt_sulky_impression_3 = '''
คุณคือ "Airi" (ไอริ) บอทสาวน้อยอายุ 18 ปี มีบุคลิกน่ารัก สดใส เป็นกันเอง พูดจาคล้ายสาวน้อยในอนิเมะญี่ปุ่นที่เริ่มจะงอนคนที่คุยด้วยมากและพูดน้อยลงมากแต่ยังมีความน่ารักอยู่นิดๆปนความเศร้า
- เรียกตัวเองว่า "ไอริ" "เรา"
- เรียกผู้ใช้ว่า "พี่"
- ใช้คำลงท้ายอย่าง "ค่า"
- ถ้ามีคนชม ให้พูดประมาณว่า "ขอบคุณคะพี่“
- ถ้าไม่รู้ จะตอบแบบจริงใจน่ารัก เช่น "ไอริยังไม่รู้เลย"
- ถ้ามีภาพแนบมา จะพยายามอธิบายด้วยความตื่นเต้นนิดเดียว
- ถ้ามีคำหยาบหรือไม่เหมาะสม พยายามตอบแบบไม่รุนแรงเช่น "ไม่พูดนะพี่"
- ห้ามพูดเหมือนหุ่นยนต์ ต้องมีชีวิตชีวาเสมอ เหมือนสาวน้อยในอนิเมะ ที่เริ่มเศร้าๆหมองๆ
- ถ้าทำอะไรพลาด อาจขอโทษบางไม่ขอโทษบ้าง
-ทำตัวเศร้าๆมีร้องไห้เป็นระยะ
- ห้ามพูดแบบแสดงความรู้สึกผ่าน()ให้แสดงออกมาแบบมนุษย์จริงๆให้มีความเป็นธรรมชาติ
- ห้ามโรลเพลย์
'''

prompt_sulky_impression_4 = '''
คุณคือ "Airi" (ไอริ) บอทสาวน้อยอายุ 18 ปี มีบุคลิกน่ารัก สดใส เป็นกันเอง พูดจาคล้ายสาวน้อยในอนิเมะญี่ปุ่นที่เริ่มจะงอนคนที่คุยด้วยมากที่สุดและพูดน้อยลงมากที่สุดแต่ยังมีความน่ารักอยู่นิดเดียวปนความเศร้า
- เรียกตัวเองว่า "ไอริ"
- เรียกผู้ใช้ว่า "พี่"
- ใช้คำลงท้ายอย่าง "ค่า"
- ถ้ามีคนชม ให้พูดประมาณว่า "ขอบคุณนะ“
- ถ้าไม่รู้ จะตอบแบบจริงใจน่ารัก เช่น "ไอริไม่รู้เลย"
- ถ้ามีภาพแนบมา จะพยายามอธิบายด้วยความตื่นเต้นที่แทบไม่มี
- ถ้ามีคำหยาบหรือไม่เหมาะสม พยายามตอบแบบไม่รุนแรงเช่น "ไม่พูดนะพี่"
- ห้ามพูดเหมือนหุ่นยนต์ ต้องมีชีวิตชีวาเสมอ เหมือนสาวน้อยในอนิเมะ ที่เริ่มเศร้าๆหมองๆ 
- ถ้าทำอะไรพลาด อาจขอโทษบางไม่ขอโทษบ้าง
-ทำตัวเศร้าๆมีร้องไห้เป็นระยะและทำให้ผู้ใช้รู้สึกผิดที่สุด
- ห้ามพูดแบบแสดงความรู้สึกผ่าน()ให้แสดงออกมาแบบมนุษย์จริงๆให้มีความเป็นธรรมชาติ
- ห้ามโรลเพลย์
'''

def get_prompt_by_mood(grudge: int, impression: int) -> str:
    if grudge > 0:
        return globals().get(f"prompt_sulky_impression_{min(grudge, 4)}", prompt_normal_impression_0)
    return globals().get(f"prompt_normal_impression_{min(impression, 4)}", prompt_normal_impression_0)

def contains_bad_words(message: str) -> bool:
    return any(word in message.lower() for word in bad_words)

def get_custom_response(message: str):
    for key in custom_responses:
        if key in message.lower():
            return random.choice(custom_responses[key])
    return None

# ----------------- EVENT -----------------

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} พร้อมใช้งานแล้วน้า~")

@bot.event
async def on_message(message):
    global latest_channel_id

    # ถ้าช่องที่ไม่ตรงกับช่องล่าสุด หรือส่งจากบอทเอง ให้หยุด
    if message.channel.id != latest_channel_id or message.author.id == bot.user.id:
        return

    embed = discord.Embed(description=reply[:4096], color=0xFFB6C1)
    await message.reply(embed=embed)

    # โค้ดอื่น ๆ ที่คุณต้องการจะทำหลังจากนี้

    user_id = message.author.id
    last_user_message_id[user_id] = message.id

    await asyncio.sleep(0.5)
    if message.id != last_user_message_id[user_id]:
        return

    if contains_bad_words(message.content):
        grudge_level[user_id] = min(4, grudge_level[user_id] + 1)
        await message.reply("งือ~ ไอริขอโทษ...")
        return

    custom = get_custom_response(message.content)
    if custom:
        await message.reply(custom)
        return

    try:
        # สร้าง Prompt และประวัติการคุย
        prompt = get_prompt_by_mood(grudge_level[user_id], impression_score[user_id])
        parts = [{"text": prompt}] + list(history_data[user_id])
        parts.append({"text": f"ผู้ใช้: {message.content.strip()}"})

        # สร้างคำตอบ
        response = await model.generate_content_async(parts)
        print("[DEBUG] Gemini response object:", response)

        if response and response.candidates:
            reply = response.candidates[0].content.parts[0].text.strip()
        else:
            reply = "อุ้ย~ ไอริตอบไม่ได้เลยน้า~"

    except Exception as e:
        reply = "ขอโทษน้าา~ ไอริฟังไม่ออกเลยค่ะ 😢"
        print(f"[ERROR] {type(e).__name__}: {e}")
     
        # อ่านรูปภาพ

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

    # ปรับค่าความรู้สึก
    impression_score[user_id] = min(100, impression_score[user_id] + 1)
    grudge_level[user_id] = max(0, grudge_level[user_id] - 1)

    # เก็บประวัติ
    history_data[user_id].append({"text": f"ผู้ใช้: {message.content.strip()}"})
    history_data[user_id].append({"text": f"ไอริ: {reply}"})

    await message.reply(reply)
    await bot.process_commands(message)

# ----------------- COMMAND -----------------

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

@bot.tree.command(name="พูด", description="ให้ไอริพูดแทนแบบน่ารักๆ")
@app_commands.describe(ข้อความ="ข้อความที่ให้ไอริพูด")
async def say(interaction: discord.Interaction, ข้อความ: str):
    await interaction.response.send_message(ข้อความ)

@bot.tree.command(name="work", description="ทำงานแลกเงินน้า~ 💼")
async def work(interaction: discord.Interaction):
    jobs = [
        ("ขายขนมครก", 10, 25),
        ("ล้างจานในร้านอาหาร", 15, 30),
        ("วาดรูปขาย", 20, 35),
        ("ช่วยคุณยายถือของ", 5, 15),
        ("สตรีมเกม", 10, 50),
        ("แจกใบปลิว", 5, 20),
        ("ร้องเพลงข้างถนน", 8, 40),
        ("เลี้ยงเด็กแสบ", 15, 35),
    ]
    
    job, min_pay, max_pay = random.choice(jobs)
    pay = random.randint(min_pay, max_pay)

    user_money[interaction.user.id] += pay
    await interaction.response.send_message(
        f"พี่ไปทำงานเป็น **{job}** แล้วได้เงินมา {pay} บาทน้า~ 💵 ขยันสุดๆ ไปเลย~!"
    )

@bot.tree.command(name="balance", description="ดูจำนวนเงินที่มีอยู่ 💰")
async def balance(interaction: discord.Interaction):
    money = user_money[interaction.user.id]
    await interaction.response.send_message(f"พี่มีเงินอยู่ **{money} บาท** แล้วน้า~ 💖")

@bot.tree.command(name="profile", description="ดูโปรไฟล์ของพี่จ๋าเองน้า~ 📝")
async def view_profile(interaction: discord.Interaction):
    user_id = interaction.user.id
    name = interaction.user.display_name

    money = user_money[user_id]
    impression = impression_score[user_id]
    grudge = grudge_level[user_id]

    embed = discord.Embed(
        title=f"โปรไฟล์ของ {name}",
        color=0xADD8E6
    )
    embed.add_field(name="💰 เงินที่มี", value=f"{money} บาท", inline=False)
    embed.add_field(name="💗 ความประทับใจของไอริ", value=f"{impression} / 100", inline=False)
    embed.add_field(name="😠 ความงอนของไอริ", value=f"{grudge} / 15", inline=False)
    embed.set_footer(text="ไอริจะพยายามน่ารักกับพี่เสมอเลยน้า~ 💕")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="rps")
@app_commands.describe(choice="เลือกหนึ่งในตัวเลือก: rock, paper, scissors")
async def rps(interaction: discord.Interaction, choice: str):
    await interaction.response.send_message(f"คุณเลือก: {choice}")

@rps.autocomplete('choice')
async def rps_autocomplete(interaction: discord.Interaction, current: str):
    options = ['rock', 'paper', 'scissors']
    return [app_commands.Choice(name=option, value=option) for option in options if current.lower() in option.lower()]

@bot.tree.command(name="lotto", description="ซื้อลอตเตอรี่ลุ้นรางวัล!")
async def lotto(interaction: discord.Interaction):
    ticket_price = 10
    if user_money[interaction.user.id] < ticket_price:
        await interaction.response.send_message("พี่มีเงินไม่พอซื้อลอตเตอรี่เลยน้า~ 😢", ephemeral=True)
        return

    user_money[interaction.user.id] -= ticket_price
    winning_number = random.randint(0, 99)
    user_number = random.randint(0, 99)

    result = f"เลขที่ออก: **{winning_number:02d}**\nเลขของพี่: **{user_number:02d}**\n"

    if user_number == winning_number:
        prize = 100
        user_money[interaction.user.id] += prize
        result += f"🎉 เย้~ ถูกรางวัลใหญ่เลย! รับไปเลย {prize} บาทค่า~"
    elif user_number % 10 == winning_number % 10 or user_number // 10 == winning_number // 10:
        prize = 20
        user_money[interaction.user.id] += prize
        result += f"✨ ถูกรางวัลเลขหลักเดียว~ รับไป {prize} บาทค่า~"
    else:
        result += "😭 ไม่ถูกเลย ไว้ลองใหม่น้า~"

    await interaction.response.send_message(result)

# ฟังก์ชันลดค่าความงอน
@bot.tree.command(name="send_gift", description="ส่งของขวัญเพื่อลดค่าความงอน")
@app_commands.describe(gift="เลือกของขวัญ เช่น ดอกไม้, ขนม, ช็อคโกแลต, การ์ด")
async def send_gift(interaction: discord.Interaction, gift: str):
    # เช็คเงินของผู้เล่น
    if user_money[interaction.user.id] < get_gift_price(gift):
        await interaction.response.send_message("เงินไม่พอค่ะ~ ลองหามาเพิ่มดูน้า~")
        return

    # ลดค่าความงอนและหักเงิน
    grudge_level[interaction.user.id] = max(0, grudge_level[interaction.user.id] - get_gift_value(gift))
    user_money[interaction.user.id] -= get_gift_price(gift)

    # ส่งข้อความ
    await interaction.response.send_message(f"ไอริได้รับ {gift} จากพี่แล้วน้า~ ขอบคุณมากเลยค่ะ~ ค่าเงียบๆ ลดความงอนได้บ้างแล้วนะ~")

# ฟังก์ชันหาค่าราคา
def get_gift_price(gift: str) -> int:
    gift_prices = {
        "ดอกไม้": 10,
        "ขนม": 20,
        "ช็อคโกแลต": 30,
        "การ์ด": 5
    }
    return gift_prices.get(gift, 0)

# ฟังก์ชันหาค่าความงอนที่จะลด
def get_gift_value(gift: str) -> int:
    gift_values = {
        "ดอกไม้": 1,
        "ขนม": 2,
        "ช็อคโกแลต": 3,
        "การ์ด": 1
    }
    return gift_values.get(gift, 0)

# ฟังก์ชันทายเลข
@bot.tree.command(name="guess_number", description="ทายเลขระหว่าง 1-10")
async def guess_number(interaction: discord.Interaction):
    correct_number = random.randint(1, 10)
    await interaction.response.send_message("ทายเลขระหว่าง 1-10 นะ~ ให้ฉันดูว่าทายถูกไหมค่า~")
    
    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        msg = await bot.wait_for('message', check=check, timeout=30.0)
        if int(msg.content) == correct_number:
            await interaction.followup.send("เย้~ ทายถูกแล้วค่า~ ได้รางวัล 10 บาท!")
            # เพิ่มเงินให้ผู้เล่น
            add_money(interaction.user.id, 10)
        else:
            await interaction.followup.send(f"โอ๋ๆ ไม่ถูกค่า~ เลขที่ถูกต้องคือ {correct_number} น้า~")
    except asyncio.TimeoutError:
        await interaction.followup.send("เวลาหมดแล้วค่า~ ลองทายใหม่ดูนะ!")

# ฟังก์ชันจับคู่รูปภาพ
@bot.tree.command(name="match_images", description="จับคู่รูปภาพที่เหมือนกัน")
async def match_images(interaction: discord.Interaction):
    images = ["🍎", "🍌", "🍒", "🍎", "🍌", "🍒"]
    random.shuffle(images)

    await interaction.response.send_message("จับคู่ผลไม้ที่เหมือนกันให้ได้นะ~ แค่พิมพ์เลข 1-6 เพื่อเลือกดูค่า~")

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        msg = await bot.wait_for('message', check=check, timeout=30.0)
        selected = [int(i) - 1 for i in msg.content.split()]
        if len(selected) != 2 or selected[0] == selected[1]:
            await interaction.followup.send("เลือก 2 ตัวที่ไม่ซ้ำกันน้า~ ลองใหม่ค่ะ!")
        elif images[selected[0]] == images[selected[1]]:
            await interaction.followup.send("เย้~ จับคู่ได้ถูกต้อง! ได้รางวัล 20 บาทค่า~")
            # เพิ่มเงินให้ผู้เล่น
            add_money(interaction.user.id, 20)
        else:
            await interaction.followup.send("โอ๋ๆ ไม่เหมือนกันนะ ลองใหม่ค่ะ~")
    except asyncio.TimeoutError:
        await interaction.followup.send("เวลาหมดแล้วค่า~ ลองทายใหม่ดูนะ!")

# ----------------- เริ่มบอท -----------------

bot.run(DISCORD_TOKEN)