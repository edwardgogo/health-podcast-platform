# test_phase3.py
import config
import tts_service
import audio_processor

if __name__ == "__main__":
    print("=== 🎙️ Phase 3：雙軌語音合成與音訊後製測試 ===")
    
    # 直接模擬一段從 Phase 2 傳遞過來的 JSON 劇本資料
    mock_script = {
        "title": "高血壓日常保養（模擬測試）",
        "dialogue": [
            {"speaker": "Doctor", "text": "阿公阿嬤大家好，我是林醫師。今天要教大家怎麼正確量血壓喔。"},
            {"speaker": "Nurse", "text": "沒錯！量血壓的時候，記得要先坐在有靠背的椅子上，安靜休息五分鐘。"},
            {"speaker": "Doctor", "text": "量完之後，如果收縮壓超過一百三十毫米汞柱，就要特別注意，記得把數字寫在血壓本上。"}
        ]
    }
    
    # 設定測試對象為 85 歲以上長者 (語速最慢、停頓最長)
    test_age = "85+"
    
    print(f"\n⏳ [1/2] 正在呼叫 tts_service 逐句生成男女聲片段（設定：{config.AGE_GROUPS[test_age]['label']}）...")
    temp_files = tts_service.generate_script_audio(mock_script, test_age)
    print(f"✅ 成功產出 {len(temp_files)} 段暫存音軌！")
    
    print("\n⏳ [2/2] 正在呼叫 audio_processor 縫合音軌、插入停頓並清理垃圾...")
    final_mp3 = audio_processor.stitch_and_export(temp_files, "test_podcast.mp3", test_age)
    
    print("\n🎉 測試大功告成！")
    print(f"👉 請到左側檔案總管點擊開啟播放：{final_mp3.name}")