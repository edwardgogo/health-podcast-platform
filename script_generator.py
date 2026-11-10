# script_generator.py (純淨 REST API 版 + 支援額外病史補充功能)
import json
import requests
from typing import Dict
import config
import time


def load_script_prompt_template() -> str:
    """從 prompts 資料夾讀取劇本生成模板"""
    prompt_path = config.PROMPTS_DIR / "script_prompt.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"找不到提示詞檔案：{prompt_path}")

# 🌟 參數列新增 extra_info: str = ""
def generate_podcast_script(extracted_info: str, age_key: str, tone_key: str, extra_info: str = "") -> dict:
    """
    接收圖片解析後的衛教重點，結合『年齡分層』與『語氣風格』參數，
    透過標準 REST API 強制要求 Gemini 回傳結構化 JSON 雙人劇本。
    """
    api_key = config.get_gemini_api_key()
    if not api_key:
        raise ValueError("找不到 GEMINI_API_KEY，請確認 .env 設定是否正確。")

    # 1. 取得對應的年齡與語氣設定參數
    age_cfg = config.AGE_GROUPS.get(age_key, config.AGE_GROUPS[config.DEFAULT_AGE_GROUP])
    tone_cfg = config.TONE_STYLES.get(tone_key, config.TONE_STYLES[config.DEFAULT_TONE_STYLE])

    doctor_name = config.VOICE_CONFIG["Doctor"]["role_name"]
    nurse_name = config.VOICE_CONFIG["Nurse"]["role_name"]

    # 🌟 處理額外補充資訊：如果有填寫，就組裝成一段獨立的提示詞區塊
    extra_info_section = ""
    if extra_info and extra_info.strip():
        extra_info_section = f"""
【特別關注與補充病史】
使用者補充了以下患者背景與需求：{extra_info.strip()}
(請務必將上述背景自然融入衛教對談中，例如由醫師或護理師主動提及該病史，讓長輩感到專屬的關懷與針對性的建議。)
"""

    # 2. 將參數動態注入到劇本 Prompt 模板中 (此處不再使用純檔案模板，改用程式內建構)
    final_prompt = f"""你現在是一位充滿同理心的台灣家醫科醫師（{doctor_name}）與資深衛教護理師（{nurse_name}）。
請根據以下從醫療衛教單張提取出的重點資訊，為「{age_cfg['label']}」的聽眾編寫一段雙人對談 Podcast 劇本。

【聽眾與語氣設定】
- 目標聽眾：{age_cfg['label']}（溝通原則：{age_cfg['style_guide']}）
- 對談語氣：{tone_cfg['label']}（{tone_cfg['prompt_desc']}）
- 目標總字數：約精簡至 8 到 12 個來回對話（節奏明快，聚焦核心衛教觀念）
{extra_info_section}
【⚠️ 語音合成（TTS）專用純文字鐵律 — 違反將導致系統崩潰】
1. 絕對禁止出現任何特殊符號、數學符號或標記語言：嚴禁使用 <, >, &, *, #, ~, —, /, %, +, =, () 等符號。
2. 所有數字、百分比、醫療單位與比較符號，必須 100% 轉換為「繁體中文國字口語讀音」。
3. 絕對禁止出現任何 Emoji 表情符號、英文縮寫（除非極常見且需拆開唸），也禁止在台詞中加入動作提示。
4. 每一句台詞只允許使用最基本的中文標點符號：逗號（，）、句號（。）、頓號（、）、問號（？）與驚嘆號（！）。
5. 每一句台詞都必須包含實際可發音的中文字，不可只輸出標點符號。

【衛教單張核心資訊】
{extracted_info}

請嚴格依照指定的 JSON Schema 格式輸出劇本。
"""

    # 3. 定義原生 JSON Schema (取代原本的 Pydantic 模型，效果 100% 相同)
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "title": {
                "type": "STRING",
                "description": "這集衛教 Podcast 的溫馨標題"
            },
            "dialogue": {
                "type": "ARRAY",
                "description": "醫師與護理師交替對談的完整劇本清單，建議約 8 到 12 個來回對話",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "speaker": {
                            "type": "STRING",
                            "enum": ["Doctor", "Nurse"],
                            "description": "說話者的角色代號，只能是 Doctor 或 Nurse"
                        },
                        "text": {
                            "type": "STRING",
                            "description": "該角色的純口語台詞內容，不可包含任何括號動作提示或特殊符號"
                        }
                    },
                    "required": ["speaker", "text"]
                }
            }
        },
        "required": ["title", "dialogue"]
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL_NAME}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {"parts": [{"text": final_prompt}]}
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
            "temperature": 0.7
        }
    }

    # 4. 發送請求並解析 JSON 
    max_retries = 3
    response = None
    
    for attempt in range(1, max_retries + 1):
        response = requests.post(url, json=payload, timeout=90)
        
        if response.status_code == 200:
            break  # 成功取得回應，跳出重試迴圈
            
        elif response.status_code == 503:
            print(f"  ⚠️ Gemini 伺服器塞車中 (503)，等待 {attempt * 2} 秒後進行第 {attempt + 1} 次重試...")
            if attempt < max_retries:
                time.sleep(attempt * 2)  # 第一次等 2 秒，第二次等 4 秒
                continue
            else:
                raise RuntimeError("Gemini API 伺服器目前極度壅塞 (503)，已達最大重試次數，請稍候幾分鐘再試。")
                
        else:
            # 遇到 503 以外的錯誤 (例如 400 參數錯誤、429 額度用盡) 則直接報錯
            raise RuntimeError(f"Gemini API 劇本生成失敗 ({response.status_code})：{response.text}")

    data = response.json()
    try:
        json_text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(json_text)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise RuntimeError(f"解析劇本 JSON 失敗：{e}\n原始回應：{data}")