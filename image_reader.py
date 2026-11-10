# image_reader.py (加入觀察節點)
import io
import base64
import requests
from pathlib import Path
from typing import Union
from PIL import Image
import config

def load_image_reader_prompt() -> str:
    prompt_path = config.PROMPTS_DIR / "image_reader_prompt.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"找不到提示詞檔案：{prompt_path}")

def extract_health_info(image_input: Union[str, Path, Image.Image]) -> str:
    api_key = config.get_gemini_api_key()
    if not api_key:
        raise ValueError("找不到 GEMINI_API_KEY，請確認 .env 設定是否正確。")

    print("  [觀察節點 1] 圖片載入與格式轉換中...")
    if isinstance(image_input, (str, Path)):
        img = Image.open(image_input)
    elif isinstance(image_input, Image.Image):
        img = image_input
    else:
        raise TypeError("不支援的圖片輸入格式。")

    if img.mode != "RGB":
        img = img.convert("RGB")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    print("  [觀察節點 2] 圖片已成功轉為 Base64，準備發送請求。")

    prompt_text = load_image_reader_prompt()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL_NAME}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt_text}, {"inline_data": {"mime_type": "image/png", "data": img_base64}}]}]
    }

    print("  [觀察節點 3] 🚀 正在上傳資料至 Google 伺服器並等待 AI 解析 (設定 Timeout 120 秒，請耐心等候)...")
    
    # 這裡就是程式會卡住等待的地方
    response = requests.post(url, json=payload, timeout=120)
    
    print(f"  [觀察節點 4] 📥 收到伺服器回應！(狀態碼: {response.status_code})")

    if response.status_code != 200:
        raise RuntimeError(f"Gemini API 呼叫失敗 ({response.status_code})：{response.text}")

    data = response.json()
    try:
        result_text = data["candidates"][0]["content"]["parts"][0]["text"]
        print("  [觀察節點 5] 成功解讀並提取衛教重點！")
        return result_text.strip()
    except (KeyError, IndexError):
        raise RuntimeError(f"無法從 AI 回應中提取文字：{data}")