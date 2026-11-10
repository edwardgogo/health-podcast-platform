import time
from PIL import Image
import streamlit as st

import config
import session_manager
import image_reader
import script_generator
import tts_service
import audio_processor
import uuid
import qrcode
import json
import io
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

# ==========================================
# Google Drive 專屬連線函式
# ==========================================
def get_drive_service():
    """初始化並回傳 Google Drive 服務機器人"""
    creds_json = json.loads(st.secrets["GCP_JSON"])
    creds = Credentials.from_service_account_info(
        creds_json, scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(service, filename, mime_type, file_bytes):
    """上傳單一檔案至 Google Drive"""
    folder_id = st.secrets["DRIVE_FOLDER_ID"]
    file_metadata = {'name': filename, 'parents': [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()

def download_from_drive(service, filename):
    """根據檔名從 Google Drive 搜尋並下載暫存檔案"""
    folder_id = st.secrets["DRIVE_FOLDER_ID"]
    query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])
    
    if not items:
        return None
        
    file_id = items[0]['id']
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    return fh.getvalue()

# ==========================================
# 網址參數偵測與介面切換
# ==========================================
query_params = st.query_params
patient_id = query_params.get("id")

if patient_id:
    # 📱 模式 A：病患掃碼進入 (Patient View)
    st.set_page_config(page_title="您的專屬衛教資訊", page_icon="🏥", layout="centered")
    st.title("🏥 您的專屬衛教資訊")
    
    with st.spinner("正在安全載入您的專屬衛教資料..."):
        service = get_drive_service()
        
        # 嘗試從雲端硬碟抓取對應的 3 個檔案
        audio_bytes = download_from_drive(service, f"{patient_id}.mp3")
        image_bytes = download_from_drive(service, f"{patient_id}.png")
        text_bytes = download_from_drive(service, f"{patient_id}.txt")
    
    if audio_bytes:
        # 1. 顯示海報
        if image_bytes:
            st.image(image_bytes, caption="衛教單張", use_container_width=True)
        
        # 2. 播放音檔
        st.subheader("🎧 衛教語音說明")
        st.audio(audio_bytes, format="audio/mp3")
        
        # 3. 顯示逐字稿
        if text_bytes:
            transcript = text_bytes.decode("utf-8")
            with st.expander("📖 查看語音逐字稿", expanded=False):
                st.write(transcript)
    else:
        st.error("找不到此衛教檔案，連結可能已失效或被醫療機構移除。")

else:
    # ==========================================
    # 👨‍⚕️ 模式 B：醫護人員生成介面 (Doctor View)
    # ==========================================
    st.set_page_config(
        page_title="長者溫馨衛教 Podcast 生成平台",
        page_icon="🏥",
        layout="centered"
    )

    session_manager.init_session()
    session_manager.cleanup_old_audio_files()

    # (省略部分樣式，保留你的 CSS 與標題)
    st.markdown("""
        <style>
        .clean-title { font-size: clamp(1.35rem, 3.2vw, 2.05rem); font-weight: 800; white-space: nowrap; display: flex; align-items: center; justify-content: center; gap: 10px; margin: 10px 0 20px 0; }
        .script-card { background-color: #F8FAFC; border-left: 5px solid #3B82F6; padding: 14px 18px; border-radius: 10px; margin-bottom: 12px; font-size: 1.1rem; line-height: 1.75; }
        .script-card.nurse { background-color: #FDF2F8; border-left: 5px solid #EC4899; }
        </style>
        <div class="clean-title"><span>🏥</span><span>暖心醫聲館｜長輩專屬的健康廣播電台</span></div>
    """, unsafe_allow_html=True)
    st.markdown("醫院發的衛教單內容密密麻麻，長輩看不清楚也不想看嗎？沒關係！只要把衛教單拍下來，傳給「暖心醫聲館」，系統就會自動把它轉換成一段 3～5 分鐘的『雙人聊天廣播』。讓林醫師和小陳護理師親口唸給長輩聽，您還能直接把錄音檔下載傳到家裡的 LINE 群組，讓長輩用『聽』的也能輕鬆顧健康！")
    st.divider()

    # 步驟一與步驟二
    st.subheader("📸 第一步：上傳衛教文宣圖片")
    uploaded_file = st.file_uploader("請選擇或拖曳清晰的衛教單張照片（支援 JPG、PNG 格式，上限 10MB）", type=config.ALLOWED_IMAGE_TYPES)
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
    st.subheader("⚙️ 第二步：設定您/聽眾屬性與補充資訊")
    col1, col2 = st.columns(2)
    with col1:
        age_options = list(config.AGE_GROUPS.keys())
        selected_age_key = st.selectbox("👴 目標您/聽眾年齡層", options=age_options, index=age_options.index(config.DEFAULT_AGE_GROUP), format_func=lambda k: config.AGE_GROUPS[k]["label"])
    with col2:
        tone_options = list(config.TONE_STYLES.keys())
        selected_tone_key = st.selectbox("💬 衛教廣播對談語氣風格", options=tone_options, index=tone_options.index(config.DEFAULT_TONE_STYLE), format_func=lambda k: config.TONE_STYLES[k]["label"])
    extra_info_text = st.text_area("📝 補充健康背景或關注焦點（選填）", placeholder="例如：長輩有糖尿病史，或最近特別在意失眠問題。系統將會把這些資訊巧妙融入對談中給予關懷...")
    st.divider()

    # 步驟三：啟動
    st.subheader("🎧 第三步：開始製作專屬衛教 Podcast")
    start_btn = st.button("✨ 一鍵生成衛教 Podcast 音檔與逐字稿", type="primary", use_container_width=True, disabled=(preview_image is None))

    if start_btn and preview_image is not None:
        can_run, limit_msg = session_manager.check_rate_limit()
        if not can_run:
            st.warning(limit_msg)
        else:
            st.session_state.current_audio_path = None
            # 每次生成新的，清空舊的 QR Code
            st.session_state.pop("share_url", None)
            st.session_state.pop("qr_buf", None)
            
            with st.status("🚀 暖心醫聲館正在為您製作專屬衛教 Podcast（全程約需 40～90 秒，請稍後，勿關閉網頁）...", expanded=True) as status:
                try:
                    st.write("🔍 **[1/4] 林醫師正在仔細閱讀衛教單張上的文字與數據...**")
                    extracted_text = image_reader.extract_health_info(preview_image)
                    st.session_state.extracted_info = extracted_text

                    age_label = config.AGE_GROUPS[selected_age_key]["label"]
                    st.write(f"✍️ **[2/4] 小陳護理師正在為「{age_label}」編寫劇本...**")
                    script_data = script_generator.generate_podcast_script(extracted_text, selected_age_key, selected_tone_key, extra_info_text)
                    st.session_state.current_script = script_data

                    st.write("🎙️ **[3/4] 林醫師與小陳護理師正在錄音~**")
                    temp_audio_files = tts_service.generate_script_audio(script_data, selected_age_key)
                    final_mp3_path = audio_processor.stitch_and_export(temp_audio_files, f"podcast_{int(time.time())}.mp3", selected_age_key)

                    session_manager.record_generation_success(final_mp3_path, script_data, extracted_text)

                    # 🌟 關鍵修正：將上傳與產 QR Code 的動作移入生成流程內，避免重複執行 🌟
                    st.write("🔄 **[4/4] 正在將檔案加密傳送至 Google 雲端備份...**")
                    service = get_drive_service()
                    unique_id = str(uuid.uuid4().hex)[:8]

                    # 處理要上傳的三個檔案內容
                    img_bytes = uploaded_file.getvalue()
                    transcript_text = "\n".join([f"{line['speaker']}: {line['text']}" for line in script_data["dialogue"]])
                    with open(final_mp3_path, "rb") as f:
                        audio_bytes = f.read()

                    upload_to_drive(service, f"{unique_id}.png", "image/png", img_bytes)
                    upload_to_drive(service, f"{unique_id}.txt", "text/plain", transcript_text.encode("utf-8"))
                    upload_to_drive(service, f"{unique_id}.mp3", "audio/mp3", audio_bytes)
                    
                    # ⚠️ 產出專屬網址與 QR Code (請將下方網址替換為你的真實網址)
                    base_url = "https://health-podcast-platform-wfdm4gu9bockve4yxpaysv.streamlit.app/" 
                    share_url = f"{base_url}?id={unique_id}"
                    
                    qr = qrcode.QRCode(box_size=10, border=4)
                    qr.add_data(share_url)
                    qr.make(fit=True)
                    img_qr = qr.make_image(fill_color="black", back_color="white")
                    buf = io.BytesIO()
                    img_qr.save(buf, format="PNG")
                    
                    # 存入記憶體供下方畫面顯示
                    st.session_state.share_url = share_url
                    st.session_state.qr_buf = buf.getvalue()

                    status.update(label="🎉 衛教 Podcast 與逐字稿製作大功告成！請在下方收聽與閱讀。", state="complete", expanded=False)

                except Exception as e:
                    status.update(label="❌ 處理階段發生異常", state="error", expanded=True)
                    st.error(f"系統異常訊息：{e}")

    # ==========================================
    # 6. 成果展示區：音檔播放器 ＋ 雙人逐字稿 ＋ QR Code
    # ==========================================
    if st.session_state.current_script:
        script = st.session_state.current_script
        audio_path = st.session_state.current_audio_path

        st.divider()
        st.subheader(f"📻 衛教廣播主題：《{script['title']}》")

        if audio_path:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            st.audio(audio_bytes, format="audio/mp3")
            st.download_button(
                label="📥 點此下載 MP3 音檔", data=audio_bytes, file_name=f"{script['title']}.mp3", mime="audio/mp3", use_container_width=True
            )

        # 🌟 顯示 QR Code 小卡 (從記憶體中讀取，不會因為點擊其他按鈕消失)
        if "share_url" in st.session_state and "qr_buf" in st.session_state:
            st.divider()
            st.subheader("📲 病患專屬衛教小卡")
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(st.session_state.qr_buf, caption="請病患掃描此 QR Code")
            with col2:
                st.markdown(f"**專屬連結：**\n[{st.session_state.share_url}]({st.session_state.share_url})")
                st.info("醫護人員提示：此檔案已備份至指定 Google Drive，病患掃描後將直接看見專屬播放介面。")

        st.markdown("### 📖 節目完整逐字稿（大字好讀版）")
        for idx, line in enumerate(script["dialogue"], 1):
            speaker = line["speaker"]
            role_name = config.VOICE_CONFIG[speaker]["role_name"]
            icon = "👨‍⚕️" if speaker == "Doctor" else "👩‍⚕️"
            card_class = "script-card" if speaker == "Doctor" else "script-card nurse"
            st.markdown(f'<div class="{card_class}"><b>{idx}. {icon} {role_name}：</b>{line["text"]}</div>', unsafe_allow_html=True)

        if st.session_state.extracted_info:
            with st.expander("🩺 點此查看暖心醫聲館從圖片提取的「原始衛教單張重點」"):
                st.markdown(st.session_state.extracted_info)

# ==========================================
# 頁尾：隱私保護與醫療免責聲明
# ==========================================
st.divider() 
st.warning("🔒 **隱私保護提醒**\n\n請勿上傳含有病人姓名、病歷號、身分證字號、聯絡方式或其他可識別個人資訊（PII/PHI）的文件。")
st.info("⚕️ **醫療免責聲明**\n\n本平台由 AI 輔助生成衛教內容，僅供衛教溝通與設計參考，不具備實質醫療診斷或處方效力。所有臨床決策與衛教實務，請務必以醫療專業人員之最終評估與指導為準。")