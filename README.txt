GoYolo Trip: ไฟล์เชื่อมหน้า planner_confirmed ไปหน้าจัดตารางทริป

1) สำรอง app.py และ templates/planner_confirmed.html เดิมก่อน
2) นำ app.py จากชุดนี้ไปแทน app.py เดิม (เป็นสำเนาจาก app(3).py ที่เพิ่ม route และ import json)
3) นำ templates/planner_confirmed.html ไปแทนไฟล์เดิม
4) วาง templates/trip_customizer.html และ templates/trip_customized_confirmed.html ในโฟลเดอร์ templates เดียวกัน
5) รัน Flask ใหม่ แล้วไปที่ Planner > ยืนยันข้อมูลเบื้องต้น > กด “จัดตารางทริปของฉัน”

ข้อจำกัด: ตัวเลือกสถานที่/ที่พักใช้ข้อมูลที่มีในโปรเจกต์เท่าที่พบ; หากฐานข้อมูลไม่มีรายการที่พัก จะมีที่พักตัวอย่างให้เลือก และการยืนยันตารางนี้ยังไม่ใช่การจองจริง
