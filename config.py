# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# 1. 載入本機 .env 檔案中的環境變數
load_dotenv()

# ==========================================
# 專案路徑與資料夾設定
# ==========================================
BASE_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "prompts"
TEMP_AUDIO_DIR = BASE_DIR / "temp_audio"

# 確保 prompts 與 暫存音檔資料夾 存在
PROMPTS_DIR.mkdir(exist_ok=True)
TEMP_AUDIO_DIR.mkdir(exist_ok=True)

# ==========================================
# AI 模型設定 (Gemini API)
# ==========================================
def get_gemini_api_key() -> str:
    """
    安全取得 Gemini API Key：
    優先讀取本機環境變數 (.env)，若未來部署至 Streamlit 雲端則自動支援讀取 st.secrets
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            pass
    return api_key or ""

# 使用支援多模態(圖片理解)且反應快速、免費額度高的 Gemini 3.5 Flash 模型
GEMINI_MODEL_NAME = "gemini-3.5-flash"

# ==========================================
# 聽眾年齡分層設定 (對應企畫書 5.1 節)
# 包含：顯示名稱、語速調整(Edge-TTS rate)、停頓毫秒數、劇本生成指引
# ==========================================
AGE_GROUPS = {
    "18-64": {
        "label": "18–64 歲（一般成人／青壯年）",
        "tts_rate": "+0%",          # 正常語速
        "pause_ms": 300,            # 句間停頓 0.3 秒
        "target_words": "1100~1400", # 約 3~5 分鐘正常語速字數
        "style_guide": "語氣自然流暢，可適度保留常見醫療名詞並加以解釋，重在自我健康管理與生活效率。"
    },
    "65-74": {
        "label": "65–74 歲（初老期長者）",
        "tts_rate": "-3%",          # 微幅放慢 5%
        "pause_ms": 400,            # 句間停頓 0.4 秒
        "target_words": "950~1200",
        "style_guide": "稱呼親切（如：各位大哥大姐、伯伯阿姨），將所有醫療專有名詞轉為生活化比喻，減少英文縮寫，強調日常保養。"
    },
    "75-84": {
        "label": "75–84 歲（中老期長者）",
        "tts_rate": "-6%",         # 明顯放慢 12%，方便聽覺吸收
        "pause_ms": 500,            # 句間停頓 0.5 秒
        "target_words": "850~1050",
        "style_guide": "稱呼溫暖（如：阿公阿嬤、長輩朋友），句子要短、重點要重複叮嚀兩次以上，多用具體的日常動作指導（例如：飯後散步、看藥袋顏色），語氣極具耐心。"
    },
    "85+": {
        "label": "85 歲以上（高齡期長者／家屬照護）",
        "tts_rate": "-12%",         # 慢速清晰播報
        "pause_ms": 650,            # 句間停頓 0.65 秒，給予充足反應時間
        "target_words": "750~950",
        "style_guide": "用詞極度精簡白話、充滿安撫與陪伴感，一次只講一個核心動作；同時在對話中自然穿插『提醒身旁照顧的家屬要注意什麼』的雙向叮嚀。"
    }
}

# 預設選擇的年齡層（第一階段主打長者，預設 65-74 歲）
DEFAULT_AGE_GROUP = "65-74"

# ==========================================
# 語氣風格設定 (對應企畫書 5.2 節)
# ==========================================
TONE_STYLES = {
    "warm": {
        "label": "溫馨親切（像家人與鄰居醫師的關懷叮嚀）",
        "prompt_desc": "對話充滿溫暖、同理心與人情味，常使用鼓勵與關懷的語助詞，像熟識多年的家庭醫師與護理師在跟病人閒聊家常中帶出衛教重點。"
    },
    "professional": {
        "label": "專業簡要（條理分明、重點清晰不拖泥帶水）",
        "prompt_desc": "對話結構嚴謹、條理清晰，由醫師清楚列出第一點、第二點注意事項，護理師負責總結與複誦關鍵數字，讓聽眾能快速掌握核心醫療指令。"
    },
    "encouraging": {
        "label": "活潑鼓勵（破除醫療恐懼、建立正向康復信心）",
        "prompt_desc": "語氣陽光正向、充滿活力，特別針對容易擔心或對醫療有恐懼的聽眾，透過輕鬆的問答破除迷思，不斷給予肯定與安心感。"
    }
}

DEFAULT_TONE_STYLE = "warm"

# ==========================================
# 雙人 Podcast 角色與台灣語音 (Edge-TTS) 設定
# ==========================================
VOICE_CONFIG = {
    "Doctor": {
        "role_name": "林醫師",
        "voice_id": "zh-TW-HsiaoYuNeural",     # 微軟台灣沉穩女聲
        "pitch": "+0Hz"
    },
    "Nurse": {
        "role_name": "小陳護理師",
        "voice_id": "zh-TW-HsiaoChenNeural",  # 微軟台灣親切女聲 (曉臻)
        "pitch": "+0Hz"
    }
}

# ==========================================
# 系統安全與防濫用設定 (對應企畫書 6.3 節)
# ==========================================
ALLOWED_IMAGE_TYPES = ["jpg", "jpeg", "png"]
MAX_IMAGE_SIZE_MB = 10               # 單張圖片上傳上限 10 MB
MAX_GENERATIONS_PER_SESSION = 5      # 單一使用者工作階段最多生成 5 次 (保護 API 額度)
COOLDOWN_SECONDS = 30                # 每次生成之間的冷卻時間 (秒)


# ==========================================
# Phase 1 環境自我檢測腳本
# ==========================================
if __name__ == "__main__":
    import shutil
    print("=== 🏥 長者衛教 Podcast 平台：Phase 1 環境自我檢測 ===")
    
    # 1. 檢查 API Key
    key = get_gemini_api_key()
    if key:
        print(f"✅ [成功] 已讀取到 Gemini API Key (前六碼: {key[:6]}...)")
    else:
        print("❌ [失敗] 尚未讀取到有效的 GEMINI_API_KEY，請檢查 .env 檔案是否設定正確！")

    # 2. 檢查 FFmpeg 是否安裝成功
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print(f"✅ [成功] 系統已偵測到 FFmpeg 工具 ({ffmpeg_path})")
    else:
        print("❌ [失敗] 系統找不到 FFmpeg！請確認步驟 1 是否安裝成功，或重新啟動 VS Code。")

    # 3. 檢查設定檔參數
    print(f"✅ [成功] 載入 {len(AGE_GROUPS)} 種年齡分層設定：{[v['label'] for v in AGE_GROUPS.values()]}")
    print(f"✅ [成功] 載入雙人聲線：{VOICE_CONFIG['Doctor']['role_name']} ({VOICE_CONFIG['Doctor']['voice_id']}) & {VOICE_CONFIG['Nurse']['role_name']} ({VOICE_CONFIG['Nurse']['voice_id']})")
    print("======================================================")