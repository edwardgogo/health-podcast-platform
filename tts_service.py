# tts_service.py (基於你的版本進行微調與穩固防護)
import re
import asyncio
import edge_tts
from pathlib import Path
from typing import List, Dict
import config


def sanitize_text_for_tts(text: str) -> str:
    """
    【雙重保險消毒器】
    在送往 Edge-TTS 前，強制把可能破壞微軟 SSML XML 解析的特殊符號轉為中文或移除。
    """
    if not text:
        return ""
    
    # 1. 將常見數學與醫療符號強制轉為中文口語，避免破壞 XML 標籤
    replacements = {
        "<": "小於",
        ">": "大於",
        "≤": "小於等於",
        "≥": "大於等於",
        "&": "和",
        "%": "百分之",
        "~": "到",
        "～": "到",
        "/": "每",
        "+": "加",
    }
    for sym, word in replacements.items():
        text = text.replace(sym, word)

    # 2. 移除括號內的舞台指示，例如 (笑)、（點頭）、[停頓]
    text = re.sub(r"[\(（\[【].*?[\)）\]】]", "", text)

    # 3. 移除 Markdown 符號（如星號 ** 等）、引號、破折號與所有非中英數及基礎標點的怪異字元 (包含 Emoji)
    text = re.sub(r"[*#_`~—-]+", "", text)
    text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9，。、？！：；「」\s]", "", text)

    # 4. 壓縮多餘空白
    text = re.sub(r"\s+", "，", text).strip("， ")
    return text


async def _generate_all_lines_async(dialogue: List[Dict], tts_rate: str) -> List[Path]:
    """
    【核心修復】在『單一非同步事件迴圈』中依序處理所有台詞，
    避免在 for 迴圈中反覆呼叫 asyncio.run() 導致微軟封鎖或 Socket 崩潰。
    """
    audio_paths = []

    for idx, line in enumerate(dialogue):
        speaker = line.get("speaker", "Doctor")
        raw_text = line.get("text", "")
        
        # 先進行文字消毒
        clean_text = sanitize_text_for_tts(raw_text)
        
        # 如果消毒後沒有半個中文字或英數字（例如只有標點符號），直接跳過不合成，防止 NoAudioReceived
        if not re.search(r"[\u4e00-\u9fa5a-zA-Z0-9]", clean_text):
            print(f"  ⚠️ 第 {idx+1} 句消毒後無有效發音字元，已略過。原始內容：{raw_text}")
            continue

        voice_id = config.VOICE_CONFIG.get(speaker, config.VOICE_CONFIG["Doctor"])["voice_id"]
        output_filename = config.TEMP_AUDIO_DIR / f"line_{idx:03d}_{speaker}.mp3"

        # 單句最多重試 5 次的容錯機制
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                communicate = edge_tts.Communicate(
                    text=clean_text,
                    voice=voice_id,
                    rate=tts_rate
                )
                await communicate.save(str(output_filename))
                
                # 【修正點】確認檔案真實存在且大小大於 100 Bytes（確實為有效音訊而非錯誤封包）
                if output_filename.exists() and output_filename.stat().st_size > 100:
                    audio_paths.append(output_filename)
                    break
                else:
                    raise RuntimeError("產生的音檔大小異常或小於 100 Bytes")
                    
            except Exception as e:
                print(f"  ⚠️ [TTS 警告] 第 {idx+1} 句合成失敗 (嘗試 {attempt}/{max_retries})：{e}")
                print(f"     👉 問題台詞內容：「{clean_text}」 (語速: {tts_rate}, 聲線: {voice_id})")
                if attempt < max_retries:
                    # 指數退避等待 1.5 秒後重試
                    await asyncio.sleep(1.5 * attempt)
                else:
                    raise RuntimeError(f"第 {idx+1} 句台詞「{clean_text[:20]}...」連續合成失敗：{e}")

        # 關鍵緩衝：每句合成完休息 0.25 秒，溫和對待微軟伺服器，避免觸發頻率限制
        await asyncio.sleep(0.25)

    return audio_paths


def generate_script_audio(script_data: Dict, age_key: str = config.DEFAULT_AGE_GROUP) -> List[Path]:
    """
    對外接口：全程只啟動一次 asyncio 事件迴圈，處理整份劇本。
    """
    age_cfg = config.AGE_GROUPS.get(age_key, config.AGE_GROUPS[config.DEFAULT_AGE_GROUP])
    tts_rate = age_cfg["tts_rate"]
    dialogue = script_data.get("dialogue", [])

    if not dialogue:
        raise ValueError("劇本中沒有任何對話內容可供合成！")

    # 全程只呼叫這一次 asyncio.run()！ 
    return asyncio.run(_generate_all_lines_async(dialogue, tts_rate))