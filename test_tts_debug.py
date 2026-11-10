# test_tts_debug.py (獨立語音管線診斷補丁)
import asyncio
import time
from pathlib import Path
import config
import tts_service

def run_diagnostic():
    print("=" * 50)
    print("🔍 [語音管線診斷補丁] 開始執行...")
    print("=" * 50)

    # 1. 檢查暫存目錄是否存在
    print(f"[檢查 1] 暫存音訊目錄：{config.TEMP_AUDIO_DIR}")
    if not config.TEMP_AUDIO_DIR.exists():
        config.TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        print("  -> 已自動建立暫存目錄。")
    else:
        print("  -> 目錄狀態正常。")

    # 2. 模擬一筆包含各種邊界情況的真實劇本
    test_script = {
        "title": "診斷測試節目",
        "dialogue": [
            {"speaker": "Doctor", "text": "各位大哥大姐大家好，我是林醫師。"},
            {"speaker": "Nurse", "text": "護理師來囉！今天我們要來談談血壓小於一百三十的保養方法。"},
            {"speaker": "Doctor", "text": "沒錯，記得量血壓前要安靜休息五分鐘喔。"}
        ]
    }

    # 3. 測試目標年齡層 (預設用 65-74)
    target_age = "65-74"
    age_cfg = config.AGE_GROUPS.get(target_age, config.AGE_GROUPS[config.DEFAULT_AGE_GROUP])
    print(f"[檢查 2] 讀取年齡設定：{age_cfg['label']} (語速: {age_cfg['tts_rate']}, 停頓: {age_cfg['pause_ms']}ms)")

    # 4. 嘗試執行 tts_service 的單句或整批合成
    print("[檢查 3] 正在呼叫 tts_service.generate_script_audio()...")
    start_time = time.time()
    
    try:
        audio_paths = tts_service.generate_script_audio(test_script, target_age)
        elapsed = time.time() - start_time
        print(f"  🎉 成功！耗時 {elapsed:.2f} 秒，共產出 {len(audio_paths)} 個音軌片段：")
        for p in audio_paths:
            print(f"     - {p.name} (大小: {p.stat().st_size} bytes)")
    except Exception as e:
        print(f"  ❌ 捕獲到具體異常錯誤：")
        import traceback
        traceback.print_exc()
        return

    print("=" * 50)
    print("🏁 診斷完結：如果這個獨立測試順利通過，代表管線本身沒問題；")
    print("   若在網頁端依然失敗，問題將指向 Streamlit 非同步執行緒或 UI 狀態交接。")
    print("=" * 50)

if __name__ == "__main__":
    run_diagnostic()
    