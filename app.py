# app.py (支援即時顯示逐字稿 + 階段性容錯保存版)
import time
from PIL import Image
import streamlit as st

import config
import session_manager
import image_reader
import script_generator
import tts_service
import audio_processor

# ==========================================
# 1. 網頁基本設定
# ==========================================
st.set_page_config(
    page_title="長者溫馨衛教 Podcast 生成平台",
    page_icon="🏥",
    layout="centered"
)

session_manager.init_session()
session_manager.cleanup_old_audio_files()

# ==========================================
# 2. 注入輕量 CSS (單行標題 & 逐字稿對話框美化)
# ==========================================
st.markdown(
    """
    <style>
    .clean-title {
        font-size: clamp(1.35rem, 3.2vw, 2.05rem);
        font-weight: 800;
        white-space: nowrap;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        margin: 10px 0 20px 0;
    }
    .script-card {
        background-color: #F8FAFC;
        border-left: 5px solid #3B82F6;
        padding: 14px 18px;
        border-radius: 10px;
        margin-bottom: 12px;
        font-size: 1.1rem;
        line-height: 1.75;
    }
    .script-card.nurse {
        background-color: #FDF2F8;
        border-left: 5px solid #EC4899;
    }
    </style>
    <div class="clean-title">
        <span>🏥</span>
        <span>暖心醫聲館｜長輩專屬的健康廣播電台</span>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    醫院發的衛教單內容密密麻麻，長輩看不清楚也不想看嗎？沒關係！只要把衛教單拍下來，傳給「暖心醫聲館」，系統就會自動把它轉換成一段 3～5 分鐘的『雙人聊天廣播』。讓林醫師和小陳護理師親口唸給長輩聽，您還能直接把錄音檔下載傳到家裡的 LINE 群組，讓長輩用『聽』的也能輕鬆顧健康！
    """
)
st.divider()

# ==========================================
# 3. 步驟一：上傳衛教文宣圖片
# ==========================================
st.subheader("📸 第一步：上傳衛教文宣圖片")

uploaded_file = st.file_uploader(
    "請選擇或拖曳清晰的衛教單張照片（支援 JPG、PNG 格式，上限 10MB）",
    type=config.ALLOWED_IMAGE_TYPES
)

preview_image = None
if uploaded_file is not None:
    is_valid, msg = session_manager.validate_uploaded_file(uploaded_file)
    if not is_valid:
        st.error(msg)
    else:
        preview_image = Image.open(uploaded_file)
        with st.expander("👁️ 點此預覽您上傳的衛教單張", expanded=True):
            st.image(preview_image, use_container_width=True)

st.divider()

# ==========================================
# 4. 步驟二：選擇客製化偏好（年齡分層 & 語氣風格）
# ==========================================
st.subheader("⚙️ 第二步：設定您/聽眾屬性與補充資訊")

col1, col2 = st.columns(2)

with col1:
    age_options = list(config.AGE_GROUPS.keys())
    default_age_idx = age_options.index(config.DEFAULT_AGE_GROUP)
    selected_age_key = st.selectbox(
        "👴 目標您/聽眾年齡層",
        options=age_options,
        index=default_age_idx,
        format_func=lambda k: config.AGE_GROUPS[k]["label"]
    )

with col2:
    tone_options = list(config.TONE_STYLES.keys())
    default_tone_idx = tone_options.index(config.DEFAULT_TONE_STYLE)
    selected_tone_key = st.selectbox(
        "💬 衛教廣播對談語氣風格",
        options=tone_options,
        index=default_tone_idx,
        format_func=lambda k: config.TONE_STYLES[k]["label"]
    )

# 🌟 新增：專屬的病史與關注點補充欄位
extra_info_text = st.text_area(
    "📝 補充健康背景或關注焦點（選填）",
    placeholder="例如：長輩有糖尿病史，或最近特別在意失眠問題。系統將會把這些資訊巧妙融入對談中給予關懷..."
)

st.divider()



# ==========================================
# 5. 步驟三：一鍵啟動後台 AI 流水線
# ==========================================
st.subheader("🎧 第三步：開始製作專屬衛教 Podcast")

start_btn = st.button(
    "✨ 一鍵生成衛教 Podcast 音檔與逐字稿",
    type="primary",
    use_container_width=True,
    disabled=(preview_image is None)
)

if start_btn and preview_image is not None:
    can_run, limit_msg = session_manager.check_rate_limit()
    if not can_run:
        st.warning(limit_msg)
    else:
        st.session_state.current_audio_path = None
        
        with st.status("🚀 暖心醫聲館正在為您製作專屬衛教 Podcast（全程約需 40～90 秒，請稍後，勿關閉網頁）...", expanded=True) as status:
            try:
                st.write("🔍 **[1/3] 林醫師正在仔細閱讀衛教單張上的文字與數據...**")
                extracted_text = image_reader.extract_health_info(preview_image)
                st.session_state.extracted_info = extracted_text
                st.write("✅ 衛教單張重點提取完成！")

                age_label = config.AGE_GROUPS[selected_age_key]["label"]
                st.write(f"✍️ **[2/3] 小陳護理師正在為「{age_label}」編寫劇本...**")
                
                # 🌟 關鍵修改：將 extra_info_text 傳遞給劇本生成器
                script_data = script_generator.generate_podcast_script(
                    extracted_info=extracted_text,
                    age_key=selected_age_key,
                    tone_key=selected_tone_key,
                    extra_info=extra_info_text
                )
                # 立即保存劇本！即使第 3 步語音失敗，網頁下方也能立刻檢視逐字稿
                st.session_state.current_script = script_data
                st.write(f"✅ 廣播主題《{script_data['title']}》逐字稿編寫完成（共 {len(script_data['dialogue'])} 句對談）！")

                # --- 階段 3：單一迴圈語音合成 ---
                st.write("🎙️ **[3/3] 林醫師與小陳護理師正在錄音~**")
                temp_audio_files = tts_service.generate_script_audio(
                    script_data=script_data,
                    age_key=selected_age_key
                )
                
                output_filename = f"podcast_{int(time.time())}.mp3"
                final_mp3_path = audio_processor.stitch_and_export(
                    audio_paths=temp_audio_files,
                    output_filename=output_filename,
                    age_key=selected_age_key
                )
                st.write("✅ 廣播錄音完成！")

                session_manager.record_generation_success(
                    audio_path=final_mp3_path,
                    script_data=script_data,
                    extracted_info=extracted_text
                )

                status.update(label="🎉 衛教 Podcast 與逐字稿製作大功告成！請在下方收聽與閱讀。", state="complete", expanded=False)

            except Exception as e:
                status.update(label="❌ 語音合成階段發生異常（但已為您保留生成的逐字稿）", state="error", expanded=True)
                st.error(f"系統異常訊息：{e}\n\n💡 您可以先在下方檢視 AI 生成的「雙人對談逐字稿」，檢查是否有異常字元，或稍候重試。")

# ==========================================
# 6. 成果展示區：音檔播放器 ＋ 預設直接展開的雙人逐字稿
# ==========================================
if st.session_state.current_script:
    script = st.session_state.current_script
    audio_path = st.session_state.current_audio_path

    st.divider()
    st.subheader(f"📻 衛教廣播主題：《{script['title']}》")

    # 如果音檔也成功產出，顯示播放器與下載按鈕
    if audio_path:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        st.audio(audio_bytes, format="audio/mp3")

        st.download_button(
            label="📥 點此下載 MP3 音檔（可傳送至 LINE 給朋友/長輩反覆收聽）",
            data=audio_bytes,
            file_name=f"{script['title']}.mp3",
            mime="audio/mp3",
            use_container_width=True
        )
    else:
        st.warning("⚠️ 語音檔案尚未完成合成，但您可先閱讀下方已生成的完整衛教逐字稿：")

    # 直接在主畫面醒目展示「雙人對談逐字稿」，方便使用者與開發者檢視
    st.markdown("### 📖 節目完整逐字稿（大字好讀版）")
    for idx, line in enumerate(script["dialogue"], 1):
        speaker = line["speaker"]
        role_name = config.VOICE_CONFIG[speaker]["role_name"]
        icon = "👨‍⚕️" if speaker == "Doctor" else "👩‍⚕️"
        card_class = "script-card" if speaker == "Doctor" else "script-card nurse"
        
        st.markdown(
            f'<div class="{card_class}"><b>{idx}. {icon} {role_name}：</b>{line["text"]}</div>',
            unsafe_allow_html=True
        )

    # 原始衛教重點摘要則維持收合，保持版面整潔
    if st.session_state.extracted_info:
        with st.expander("🩺 點此查看暖心醫聲館從圖片提取的「原始衛教單張重點」"):
            st.markdown(st.session_state.extracted_info)

# ==========================================
# 頁尾：隱私保護與醫療免責聲明
# ==========================================
st.divider()  # 加入一條視覺分隔線

# 隱私提醒 (使用黃色警告框，提高警覺)
st.warning(
    "🔒 **隱私保護提醒**\n\n"
    "請勿上傳含有病人姓名、病歷號、身分證字號、聯絡方式或其他可識別個人資訊（PII/PHI）的文件。"
)

# 免責聲明 (使用藍色提示框，呈現專業感)
st.info(
    "⚕️ **醫療免責聲明**\n\n"
    "本平台由 AI 輔助生成衛教內容，僅供衛教溝通與設計參考，不具備實質醫療診斷或處方效力。所有臨床決策與衛教實務，請務必以醫療專業人員之最終評估與指導為準。"
)