# audio_processor.py
import os
from pathlib import Path
from pydub import AudioSegment
import config
from typing import List

def stitch_and_export(audio_paths: List[Path], output_filename: str, age_key: str = config.DEFAULT_AGE_GROUP) -> Path:
    """
    將多段對話音軌縫合，自動插入符合高齡者吸收節奏的換氣停頓，
    輸出為單一 MP3，並自動清理暫存檔案。
    """
    # 1. 根據年齡取得對應的停頓毫秒數 (pause_ms)
    age_cfg = config.AGE_GROUPS.get(age_key, config.AGE_GROUPS[config.DEFAULT_AGE_GROUP])
    pause_ms = age_cfg["pause_ms"]
    
    # 建立一段純空白的音軌作為換氣間隔
    silence = AudioSegment.silent(duration=pause_ms)
    
    # 建立一個空的音軌基底準備拼接
    combined_audio = AudioSegment.empty()
    
    # 2. 依序讀取暫存音檔並縫合
    for path in audio_paths:
        if path.exists():
            segment = AudioSegment.from_mp3(str(path))
            # 將台詞與停頓空白加進主音軌中
            combined_audio += segment + silence
            
    # 3. 匯出最終 Podcast 音檔 (存放於根目錄)
    final_output_path = config.BASE_DIR / output_filename
    combined_audio.export(str(final_output_path), format="mp3", bitrate="128k")
    
    # 4. 環保機制：清理 temp_audio 資料夾中的碎片檔案
    for path in audio_paths:
        try:
            if path.exists():
                os.remove(path)
        except Exception as e:
            print(f"⚠️ 無法刪除暫存檔 {path}：{e}")
            
    return final_output_path