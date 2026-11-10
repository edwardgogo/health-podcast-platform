# session_manager.py
import os
import time
from pathlib import Path
from typing import Tuple
import streamlit as st
import config


def init_session():
    """
    【目的：初始化網頁的短期記憶】
    當使用者第一次打開網頁時，在他的專屬記憶區 (st.session_state) 建立預設變數。
    """
    if "generation_count" not in st.session_state:
        st.session_state.generation_count = 0      # 紀錄該使用者已經生成了幾次
    if "last_generation_time" not in st.session_state:
        st.session_state.last_generation_time = 0.0 # 紀錄上一次點擊生成的時間點
    if "current_audio_path" not in st.session_state:
        st.session_state.current_audio_path = None  # 儲存最新產出的 MP3 路徑
    if "current_script" not in st.session_state:
        st.session_state.current_script = None      # 儲存最新產出的雙人劇本文字
    if "extracted_info" not in st.session_state:
        st.session_state.extracted_info = None      # 儲存圖片解析出的衛教重點


def validate_uploaded_file(uploaded_file) -> Tuple[bool, str]:
    """
    【目的：檔案安檢門】
    檢查使用者上傳的檔案是否為合法的 JPG/PNG，且大小不超過 config 設定的上限 (10MB)。
    """
    if uploaded_file is None:
        return False, "請先上傳一張衛教文宣圖片！"

    # 1. 檢查副檔名
    file_ext = uploaded_file.name.split(".")[-1].lower()
    if file_ext not in config.ALLOWED_IMAGE_TYPES:
        return False, f"不支援的檔案格式（.{file_ext}）！請上傳 JPG 或 PNG 格式的圖片。"

    # 2. 檢查檔案大小 (uploaded_file.size 單位是 Bytes，除以 1024*1024 轉為 MB)
    file_size_mb = uploaded_file.size / (1024 * 1024)
    if file_size_mb > config.MAX_IMAGE_SIZE_MB:
        return False, f"圖片檔案過大（{file_size_mb:.1f} MB）！請上傳小於 {config.MAX_IMAGE_SIZE_MB} MB 的圖片。"

    return True, "檔案檢查通過"


def check_rate_limit() -> Tuple[bool, str]:
    """
    【目的：防濫用保全系統】
    檢查使用者是否超過單次瀏覽的生成次數上限，或還在冷卻時間內。
    """
    # 1. 檢查總次數上限
    if st.session_state.generation_count >= config.MAX_GENERATIONS_PER_SESSION:
        return False, f"⚠️ 您在本次使用中已達到生成上限（{config.MAX_GENERATIONS_PER_SESSION} 次），請稍後再試，把免費資源留給更多有需要的長輩喔！"

    # 2. 檢查冷卻時間 (Cooldown)
    elapsed = time.time() - st.session_state.last_generation_time
    if st.session_state.last_generation_time > 0 and elapsed < config.COOLDOWN_SECONDS:
        remaining = int(config.COOLDOWN_SECONDS - elapsed)
        return False, f"⏳ 系統正在讓語音引擎稍微休息一下，請等待 {remaining} 秒後再點擊生成！"

    return True, "允許執行"


def record_generation_success(audio_path: Path, script_data: dict, extracted_info: str):
    """
    【目的：更新記憶】
    當 Podcast 成功產出後，把結果存進記憶區，並將使用次數 +1、更新最後生成時間。
    """
    st.session_state.generation_count += 1
    st.session_state.last_generation_time = time.time()
    st.session_state.current_audio_path = str(audio_path)
    st.session_state.current_script = script_data
    st.session_state.extracted_info = extracted_info


def cleanup_old_audio_files(max_age_seconds: int = 3600):
    """
    【目的：自動環保清潔工】
    每次有人使用網站時，順手檢查專案目錄下有沒有超過 1 小時 (3600秒) 的舊 podcast_*.mp3 檔案，
    有的話自動刪除，避免雲端伺服器硬碟被塞滿。
    """
    now = time.time()
    for mp3_file in config.BASE_DIR.glob("podcast_*.mp3"):
        try:
            if now - mp3_file.stat().st_mtime > max_age_seconds:
                os.remove(mp3_file)
        except Exception:
            pass