# test_phase2.py
from PIL import Image, ImageDraw, ImageFont
import image_reader
import script_generator
import config


def create_sample_flyer(filename="sample_flyer.png"):
    """自動繪製一張簡單的測試用衛教單張圖片"""
    img = Image.new("RGB", (800, 600), color=(255, 250, 240))
    draw = ImageDraw.Draw(img)

    # 嘗試載入 Windows 內建的微軟正黑體，若無則使用預設字型
    try:
        font_title = ImageFont.truetype("msjhbd.ttc", 36)
        font_body = ImageFont.truetype("msjh.ttc", 24)
    except Exception:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()

    text_lines = [
        "【馬偕溫馨衛教：高血壓長者居家血壓測量須知】",
        "",
        "一、正確測量原則（722 原則）：",
        "  - 7：連續測量 7 天",
        "  - 2：早上起床後、晚上睡覺前各量 1 次",
        "  - 2：每次量 2 遍，中間間隔 1 分鐘，取平均值",
        "",
        "二、血壓控制目標值：",
        "  - 居家血壓應控制在 130 / 80 mmHg 以下",
        "  - 若收縮壓超過 180 mmHg 或伴隨胸悶、劇烈頭痛，請立即就醫！",
        "",
        "三、日常注意事項：",
        "  1. 量血壓前請先靜坐休息 5 分鐘，不可憋尿、剛喝完咖啡或抽菸。",
        "  2. 降血壓藥必須每天按時服用，血壓正常也不可自行停藥或減藥！",
        "  3. 飲食請採低鹽飲食（每日食鹽少於 6 公克），多吃蔬果。"
    ]

    y = 40
    for i, line in enumerate(text_lines):
        font = font_title if i == 0 else font_body
        color = (180, 30, 30) if i == 0 else (30, 30, 30)
        draw.text((40, y), line, fill=color, font=font)
        y += 45 if i == 0 else 32

    img.save(filename)
    print(f"🖼️ 已自動產生測試用衛教圖片：{filename}")
    return filename


if __name__ == "__main__":
    print("=== 🧠 Phase 2：AI 視覺與雙人劇本引擎測試 ===")

    # 1. 產生測試圖片（你也可以把這裡換成你自己電腦裡的真實衛教單張 JPG/PNG 路徑）
    test_image_path = create_sample_flyer()

    # 2. 測試步驟一：圖片重點提取
    print("\n⏳ [1/2] 正在呼叫 image_reader 解析衛教圖片重點（約需 5~10 秒）...")
    extracted_text = image_reader.extract_health_info(test_image_path)
    print("\n✅ 【圖片解析結果】：")
    print("-" * 50)
    print(extracted_text)
    print("-" * 50)

    # 3. 測試步驟二：生成雙人對談劇本 (測試設定：75-84歲中老期長者 + 溫馨親切語氣)
    test_age = "75-84"
    test_tone = "warm"
    print(f"\n⏳ [2/2] 正在呼叫 script_generator 生成雙人劇本 (設定：{config.AGE_GROUPS[test_age]['label']} / {config.TONE_STYLES[test_tone]['label']})（約需 10~20 秒）...")
    
    script_data = script_generator.generate_podcast_script(
        extracted_info=extracted_text,
        age_key=test_age,
        tone_key=test_tone
    )

    # 4. 印出劇本與統計字數
    print(f"\n✅ 【成功生成 Podcast 劇本】標題：{script_data['title']}")
    print("=" * 60)
    total_chars = 0
    for idx, line in enumerate(script_data["dialogue"], 1):
        role_label = config.VOICE_CONFIG[line["speaker"]]["role_name"]
        print(f"[{idx:02d}] {role_label} ({line['speaker']})：{line['text']}\n")
        total_chars += len(line["text"])
    print("=" * 60)
    print(f"📊 劇本統計：共 {len(script_data['dialogue'])} 句對談，總字數 {total_chars} 字。")