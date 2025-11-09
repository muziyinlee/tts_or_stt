import streamlit as st
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import os
import subprocess
from pydub import AudioSegment
import tempfile
import json
import io
import base64
import time
import random

# ---------------------- 主密钥管理器 ----------------------
class MasterKeyManager:
    def __init__(self, keys_file: str = "master_keys.json"):
        self.keys_file = keys_file
        self.master_keys = self._load_master_keys()
    
    def _load_master_keys(self) -> list:
        """从JSON文件加载主密钥池"""
        try:
            if os.path.exists(self.keys_file):
                with open(self.keys_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("master_keys", [])
            else:
                st.error(f"主密钥文件 {self.keys_file} 不存在")
                return []
        except Exception as e:
            st.error(f"加载主密钥文件失败: {e}")
            return []
    
    def get_random_master_key(self) -> str:
        """随机获取一个主密钥"""
        if not self.master_keys:
            raise ValueError("主密钥池为空，请检查 master_keys.json 文件")
        return random.choice(self.master_keys)

# ---------------------- 密钥管理系统集成 ----------------------
class KeyManagementClient:
    def __init__(self, base_url="http://localhost:8503"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
    
    def validate_and_deduct(self, sub_key: str, amount: float = 1.0) -> dict:
        """验证子密钥并扣除余额"""
        try:
            response = requests.post(
                f"{self.api_url}/validate_and_deduct",
                json={"sub_key": sub_key, "amount": amount},
                timeout=10
            )
            result = response.json()
            # 确保余额字段是两位小数
            if result.get("success") and "new_balance" in result:
                result["new_balance"] = float(f"{result['new_balance']:.2f}")
            return result
        except Exception as e:
            return {"success": False, "error": f"密钥服务连接失败: {str(e)}"}
    
    def get_balance(self, sub_key: str) -> dict:
        """查询子密钥余额"""
        try:
            response = requests.post(
                f"{self.api_url}/get_balance",
                json={"sub_key": sub_key},
                timeout=10
            )
            result = response.json()
            # 确保余额字段是两位小数
            if result.get("success") and "balance" in result:
                result["balance"] = float(f"{result['balance']:.2f}")
            return result
        except Exception as e:
            return {"success": False, "error": f"密钥服务连接失败: {str(e)}"}

# 初始化主密钥管理器和密钥客户端
master_key_manager = MasterKeyManager()
kms_client = KeyManagementClient()

# ---------------------- 页面基础配置 ----------------------
st.set_page_config(
    page_title="SiliconFlow 语音工具",
    page_icon="🔊",
    layout="centered",
    initial_sidebar_state="expanded"
)

# 检查 FFmpeg 是否可用
def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

ffmpeg_available = check_ffmpeg()

# 应用标题和介绍
st.title("🔊 SiliconFlow 语音工具")

# 添加关于此工具的说明框（放在标题下方）
with st.expander("ℹ️ 关于此工具", expanded=False):
    st.markdown("""
    <style>
    a.siliconflow-link {
        color: red !important;
        font-weight: bold !important;
        text-decoration: none !important;
    }
    a.siliconflow-link:hover {
        text-decoration: none !important;
    }
    .stProgress > div > div > div > div {
        background-color: #FF4B4B;
    }
    </style> 
    #### 功能介绍：
    1. **语音转文字** - 将音频转换为文字稿
    2. **文字转语音** - 将文本内容转换为音频
    
    #### 使用说明
    - 需要有效的子密钥（从管理员处获取）
    - 子密钥仅用于计费和访问控制
    - 需要稳定的网络连接，推荐使用PC
    - 语音转文字功能推荐使用mp3音频
    
    #### 获取帮助
    如遇问题，请检查：
    - 子密钥是否正确且有效
    - 网络连接是否正常
    - 输入内容是否符合要求
    - 密钥余额是否充足
    """, unsafe_allow_html=True)

# 初始化会话状态
if 'current_cost' not in st.session_state:
    st.session_state.current_cost = 0.0
if 'transcribed_text' not in st.session_state:
    st.session_state.transcribed_text = ""
if 'transcription_done' not in st.session_state:
    st.session_state.transcription_done = False
if 'copy_success' not in st.session_state:
    st.session_state.copy_success = False
if 'current_file_name' not in st.session_state:
    st.session_state.current_file_name = None
if 'converted_audio' not in st.session_state:
    st.session_state.converted_audio = None
if 'conversion_performed' not in st.session_state:
    st.session_state.conversion_performed = False
if 'generated_audio' not in st.session_state:
    st.session_state.generated_audio = None
if 'generation_done' not in st.session_state:
    st.session_state.generation_done = False
if 'current_text' not in st.session_state:
    st.session_state.current_text = ""
if 'current_model' not in st.session_state:
    st.session_state.current_model = "FunAudioLLM/CosyVoice2-0.5B"
if 'current_balance' not in st.session_state:
    st.session_state.current_balance = None
if 'balance_query_result' not in st.session_state:
    st.session_state.balance_query_result = None
if 'balance_error' not in st.session_state:
    st.session_state.balance_error = None
# 新增会话状态用于控制余额查询按钮
if 'transcription_in_progress' not in st.session_state:
    st.session_state.transcription_in_progress = False
if 'tts_generation_in_progress' not in st.session_state:
    st.session_state.tts_generation_in_progress = False
# 新增会话状态用于存储预估费用
if 'estimated_cost' not in st.session_state:
    st.session_state.estimated_cost = None


# ---------------------- 侧边栏导航 ----------------------
st.sidebar.title("导航栏")
app_mode = st.sidebar.radio(
    "选择功能",
    ["语音转文字", "文字转语音"],
    index=0
)

# 共用配置 - 子密钥
st.sidebar.header("🔑 访问控制")
sub_key = st.sidebar.text_input(
    label="子密钥",
    type="password",
    help="输入从管理员处获取的子密钥",
    key="sub_key_input"
)

# 余额查询功能 - 使用 session state 避免刷新
if sub_key:
    # 检查是否正在转录中或生成中
    is_transcribing = st.session_state.get('transcription_in_progress', False)
    is_tts_generating = st.session_state.get('tts_generation_in_progress', False)
    is_operation_in_progress = is_transcribing or is_tts_generating
    
    if st.sidebar.button("查询余额", key="check_balance", disabled=is_operation_in_progress):
        with st.spinner("查询中..."):
            result = kms_client.get_balance(sub_key)
            if result["success"]:
                st.session_state.current_balance = result["balance"]
                st.session_state.balance_query_result = f"💰 当前余额: {result['balance']:.2f}"
                st.session_state.balance_error = None
            else:
                st.session_state.balance_error = f"查询失败: {result['error']}"
                st.session_state.balance_query_result = None
    
    # 如果正在操作中，显示提示
    if is_operation_in_progress:
        st.sidebar.info("⏳ 任务中，停止查询")
    
    # 显示查询结果（从 session state 读取）
    if hasattr(st.session_state, 'balance_query_result') and st.session_state.balance_query_result:
        st.sidebar.success(st.session_state.balance_query_result)
    if hasattr(st.session_state, 'balance_error') and st.session_state.balance_error:
        st.sidebar.error(st.session_state.balance_error)

# 分割线
st.sidebar.markdown("---")

# ---------------------- 语音转文字功能 ----------------------
if app_mode == "语音转文字":
    if not ffmpeg_available:
        st.warning("⚠️ FFmpeg 未安装或未在系统路径中找到。音频格式转换功能将不可用。")
        
        with st.expander("如何安装 FFmpeg"):
            st.markdown("""
            #### 安装 FFmpeg 指南
            
            **Windows:**  
            1. 访问 [FFmpeg 官网](https://ffmpeg.org/download.html#build-windows)  
            2. 下载 Windows 版本  
            3. 解压文件并将 `bin` 文件夹添加到系统 PATH 环境变量中  
            
            **macOS:**  
            ```bash
            # 使用 Homebrew 安装
            brew install ffmpeg
            ```
            
            **Linux (Ubuntu/Debian):**  
            ```bash
            sudo apt update
            sudo apt install ffmpeg
            ```
            
            安装完成后，请重启此应用。
            """)

    st.header("🎙️ 语音转文字")
    
    # 语音转文字专用配置
    st.sidebar.header("🎙️ 转录配置")
    model = st.sidebar.selectbox(
        label="选择转录模型",
        options=["FunAudioLLM/SenseVoiceSmall"],
        disabled=True
    )

    # 添加格式转换选项（仅在FFmpeg可用时启用）
    if ffmpeg_available:
        convert_format = st.sidebar.checkbox(
            "自动转换格式到MP3",
            value=True,
            help="自动将FLAC和M4A等格式转换为MP3格式，提高转录成功率"
        )
    else:
        st.sidebar.write("⚠️ 格式转换功能不可用（需要FFmpeg）")
        convert_format = False

    st.sidebar.markdown("""
    **📌 支持上传的音频格式：**  
    - 直接支持：MP3、WAV  
    - 需要转换：FLAC、M4A（自动转换为MP3）  
    - 建议：单个文件大小不超过100MB  
    - 时长：建议单次转录音频时长≤30分钟
    """)

    # 音频上传区
    st.subheader("1. 上传音频文件")
    audio_file = st.file_uploader(
        label="选择音频文件（支持MP3/WAV/FLAC/M4A）",
        type=["mp3", "wav", "flac", "m4a"],
        accept_multiple_files=False,
        key="audio_uploader"
    )

    # 检测文件变化并重置转录状态
    if audio_file and audio_file.name != st.session_state.current_file_name:
        st.session_state.transcribed_text = ""
        st.session_state.transcription_done = False
        st.session_state.copy_success = False
        st.session_state.current_file_name = audio_file.name
        st.session_state.converted_audio = None
        st.session_state.conversion_performed = False

    # 显示已上传的音频信息（若有）
    if audio_file:
        st.audio(audio_file, format=audio_file.type)
        
        # 检查文件类型
        file_ext = audio_file.name.lower().split('.')[-1]
        
        if file_ext in ['mp3', 'wav']:
            st.success(f"✅ 文件上传成功！  \n格式：{file_ext.upper()}（直接支持）")
        elif file_ext in ['flac', 'm4a']:
            st.info(f"📋 文件上传成功！  \n格式：{file_ext.upper()}（将自动转换为MP3）")
        else:
            st.warning(f"⚠️ 文件上传成功！  \n格式：{file_ext.upper()}（未知格式，可能无法转录）")
        
        st.write(f"文件名：{audio_file.name}")
        st.write(f"文件大小：{round(audio_file.size / (1024*1024), 2)} MB")
        
        # 提前计算并显示预估费用
        file_size_mb = audio_file.size / (1024 * 1024)
        estimated_cost = file_size_mb * 0.50
        estimated_cost = max(estimated_cost, 0.10)  # 最低 ¥0.10
        
        # 保存预估费用到session state
        st.session_state.estimated_cost = estimated_cost
        
        # 显示费用信息
        st.info(f"💰 预估费用: ¥{estimated_cost:.2f} (按文件大小计算：¥0.50/MB，最低 ¥0.10)")

    # 格式转换功能
    def convert_audio_format(audio_file, target_format="mp3"):
        """将音频文件转换为目标格式"""
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio_file.name.split('.')[-1]}") as temp_input:
                temp_input.write(audio_file.getvalue())
                temp_input_path = temp_input.name
            
            # 创建输出临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{target_format}") as temp_output:
                temp_output_path = temp_output.name
            
            # 使用pydub进行格式转换
            audio = AudioSegment.from_file(temp_input_path)
            audio.export(temp_output_path, format=target_format)
            
            # 读取转换后的文件
            with open(temp_output_path, "rb") as f:
                converted_data = f.read()
            
            # 清理临时文件
            os.unlink(temp_input_path)
            os.unlink(temp_output_path)
                
            return converted_data, f"converted.{target_format}"
        except Exception as e:
            # 清理可能残留的临时文件
            if 'temp_input_path' in locals() and os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
            if 'temp_output_path' in locals() and os.path.exists(temp_output_path):
                os.unlink(temp_output_path)
                
            st.error(f"音频格式转换失败: {str(e)}")
            return None, None

    # 转录功能区
    st.subheader("2. 开始语音转文字")
    
    # 费用说明
    st.info("💡 未转录完成请勿刷新页面，否则将转录失败，且失败扣除的费用将无法返还")
    
    # 检查是否正在进行转录
    is_transcribing = st.session_state.get('transcription_in_progress', False)
    
    transcribe_btn = st.button(
        label="🚀 启动转录" if not is_transcribing else "⏳ 转录进行中...",
        disabled=not (sub_key and audio_file) or is_transcribing,
        key="transcribe_btn"
    )

    if transcribe_btn and not is_transcribing:
        # 立即设置转录进行中状态并重新渲染
        st.session_state.transcription_in_progress = True
        st.rerun()
    
    # 如果转录正在进行，显示处理逻辑
    if st.session_state.transcription_in_progress:
        # 确保我们有音频文件
        if not audio_file:
            st.error("音频文件丢失，请重新上传")
            st.session_state.transcription_in_progress = False
            st.rerun()
        
        # 使用之前计算的费用
        actual_cost = st.session_state.estimated_cost
        
        # 显示费用信息
        st.info(f"📊 音频文件大小: {audio_file.size / (1024 * 1024):.2f} MB | 实际费用: ¥{actual_cost:.2f}")

        # 先验证子密钥并扣除费用
        with st.spinner("🔑 验证子密钥中..."):
            deduction_result = kms_client.validate_and_deduct(sub_key, amount=actual_cost)
            
            if not deduction_result["success"]:
                st.error(f"❌ {deduction_result['error']}")
                if "余额不足" in deduction_result['error']:
                    st.info("💡 请前往密钥管理系统充值或使用其他有效子密钥")
                    # 显示等待信息
                    wait_info = st.info("⏳ 10秒后自动刷新...")
                    time.sleep(10)  # 等待10秒
                    wait_info.empty()  # 清除等待信息
                    
                # 重置转录状态
                st.session_state.transcription_in_progress = False
                st.rerun()
            
            # 保存当前费用用于可能的退款
            st.session_state.current_cost = actual_cost
    
        # 确定最终要使用的音频文件
        final_audio = audio_file
        final_filename = audio_file.name
        conversion_performed = False
        
        # 检查文件扩展名
        file_ext = audio_file.name.lower().split('.')[-1]
        
        # 如果是FLAC或M4A文件且选择了自动转换
        if file_ext in ['flac', 'm4a'] and convert_format and ffmpeg_available:
            with st.spinner(f"🔄 正在转换{file_ext.upper()}到MP3格式..."):
                converted_data, converted_name = convert_audio_format(audio_file, "mp3")
                if converted_data:
                    st.session_state.converted_audio = converted_data
                    final_audio = converted_data
                    final_filename = converted_name
                    conversion_performed = True
                    st.session_state.conversion_performed = True
                    st.success(f"✅ {file_ext.upper()}格式已成功转换为MP3")
        
        # 获取一个随机的主密钥
        try:
            siliconflow_master_key = master_key_manager.get_random_master_key()
        except ValueError as e:
            st.error(f"❌ {str(e)}")
            # 重置转录状态
            st.session_state.transcription_in_progress = False
            st.rerun()
        
        # 转录处理 - 使用主密钥调用SiliconFlow API
        api_url = "https://api.siliconflow.cn/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {siliconflow_master_key}",  # 使用随机选择的主密钥
        }

        try:
            # 构建请求体
            if conversion_performed:
                # 处理转换后的音频数据
                multipart_data = MultipartEncoder(
                    fields={
                        "file": (final_filename, final_audio, "audio/mpeg"),
                        "model": model
                    }
                )
            else:
                # 处理原始上传的文件
                multipart_data = MultipartEncoder(
                    fields={
                        "file": (final_filename, final_audio.getvalue(), final_audio.type),
                        "model": model
                    }
                )
                
            headers["Content-Type"] = multipart_data.content_type

            # 发送请求
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for percent in range(0, 101, 10):
                progress_bar.progress(percent)
                status_text.text(f"🔄 转录中... {percent}%")
                time.sleep(0.1)  # 模拟进度
                
            response = requests.post(
                url=api_url,
                headers=headers,
                data=multipart_data,
                timeout=300
            )

            progress_bar.progress(100)
            status_text.text("")

            if response.status_code == 200:
                result = response.json()
                st.session_state.transcribed_text = result.get("text", "")
                st.session_state.transcription_done = True
                st.success("🎉 转录完成！")
                
                # 显示转换状态
                if conversion_performed:
                    st.info(f"📝 注：{file_ext.upper()}格式已自动转换为MP3进行转录")
            else:
                st.error(f"❌ 转录失败！  \n错误码：{response.status_code}  \n错误信息：{response.text}")
                if "unsupported format" in response.text.lower():
                    st.info("💡 检测到格式不支持错误，请尝试启用'自动转换格式到MP3'选项")
                
                # 如果API调用失败，退还费用
                with st.spinner("🔄 正在退还费用..."):
                    refund_result = kms_client.validate_and_deduct(sub_key, amount=-st.session_state.current_cost)
                
                if refund_result["success"]:
                    st.session_state.current_balance = refund_result.get("new_balance")
                    st.success(f"💰 已成功退还费用！当前余额: {st.session_state.current_balance:.2f}")
                else:
                    st.warning(f"⚠️ 退款失败: {refund_result['error']}，请联系管理员")

        except Exception as e:
            st.error(f"❌ 程序执行出错！  \n错误信息：{str(e)}")
            
            # 如果出现异常，退还费用
            with st.spinner("🔄 正在退还费用..."):
                refund_result = kms_client.validate_and_deduct(sub_key, amount=-st.session_state.current_cost)
            
            if refund_result["success"]:
                st.session_state.current_balance = refund_result.get("new_balance")
                st.success(f"💰 已成功退还费用！当前余额: {st.session_state.current_balance:.2f}")
            else:
                st.warning(f"⚠️ 退款失败: {refund_result['error']}，请联系管理员")
        
        finally:
            # 无论成功或失败，都重置转录状态
            st.session_state.transcription_in_progress = False
            # 重新渲染页面以更新按钮状态
            st.rerun()

    # 显示转录结果
    if st.session_state.transcription_done and st.session_state.transcribed_text:
        st.subheader("3. 转录结果")

        text_area_key = "transcription_result"
        st.text_area(
            label="转录文字稿 (可手动选择并复制文本)",
            value=st.session_state.transcribed_text,
            height=300,
            disabled=False,
            key=text_area_key,
            help="使用鼠标选择文本，然后按Ctrl+C(Windows/Linux)或Cmd+C(Mac)复制"
        )

        # 添加下载按钮
        st.download_button(
            label="📥 下载文本",
            data=st.session_state.transcribed_text,
            file_name="transcription.txt",
            mime="text/plain",
            key="download_transcription"
        )

    # 格式问题说明
    with st.expander("ℹ️ 关于音频格式转录问题的说明"):
        st.markdown("""
        #### 为什么某些格式需要转换？
        
        SiliconFlow API 可能对某些音频格式的支持有限。以下是常见格式的支持情况：
        
        - **MP3**: ✅ 广泛支持，无需转换
        - **WAV**: ✅ 广泛支持，无需转换
        - **FLAC**: ⚠️ 可能需要转换为MP3
        - **M4A**: ⚠️ 可能需要转换为MP3
        - 移动设备可能无法上传MP3以外的音频
        
        #### 解决方案
        - 启用"自动转换格式到MP3"选项（推荐）
        - 或者使用本地工具预先将音频转换为MP3/WAV格式
        
        #### 技术细节
        某些格式转录失败通常与音频编码或容器格式有关，而不是文件扩展名本身。
        转换为MP3可以确保使用广泛兼容的格式进行转录。
        """)

# ---------------------- 文字转语音功能 ----------------------
else:
    st.header("🔊 文字转语音")
    
    # 文字转语音专用配置
    st.sidebar.header("🔊 语音合成配置")
    
    # 模型选择（支持两个官方模型）
    model = st.sidebar.selectbox(
        label="选择语音合成模型",
        options=["FunAudioLLM/CosyVoice2-0.5B", "fnlp/MOSS-TTSD-v0.5"],
        index=0,
        help="选择用于语音合成的模型（不同模型支持的语音风格不同）",
        key="tts_model_select"
    )

    # 当模型切换时，重置语音选择状态
    if model != st.session_state.current_model:
        st.session_state.current_model = model
        st.session_state.generated_audio = None
        st.session_state.generation_done = False
        st.session_state.current_text = ""  # 切换模型时清空文本输入

    # 为每个模型绑定对应的系统预设语音（严格遵循文档）
    if model == "FunAudioLLM/CosyVoice2-0.5B":
        # CosyVoice2-0.5B 系统预设语音及描述
        voice_options = [
            ("FunAudioLLM/CosyVoice2-0.5B:alex", "沉稳男声"),
            ("FunAudioLLM/CosyVoice2-0.5B:benjamin", "低沉男声"),
            ("FunAudioLLM/CosyVoice2-0.5B:charles", "磁性男声"),
            ("FunAudioLLM/CosyVoice2-0.5B:david", "欢快男声"),
            ("FunAudioLLM/CosyVoice2-0.5B:anna", "沉稳女声"),
            ("FunAudioLLM/CosyVoice2-0.5B:bella", "激情女声"),
            ("FunAudioLLM/CosyVoice2-0.5B:claire", "温柔女声"),
            ("FunAudioLLM/CosyVoice2-0.5B:diana", "欢快女声")
        ]
    else:  # fnlp/MOSS-TTSD-v0.5
        # MOSS-TTSD-v0.5 系统预设语音及描述（根据官方文档）
        voice_options = [
            ("fnlp/MOSS-TTSD-v0.5:alex", "沉稳男声"),
            ("fnlp/MOSS-TTSD-v0.5:benjamin", "低沉男声"),
            ("fnlp/MOSS-TTSD-v0.5:charles", "磁性男声"),
            ("fnlp/MOSS-TTSD-v0.5:david", "欢快男声"),
            ("fnlp/MOSS-TTSD-v0.5:anna", "沉稳女声"),
            ("fnlp/MOSS-TTSD-v0.5:bella", "激情女声"),
            ("fnlp/MOSS-TTSD-v0.5:claire", "温柔女声"),
            ("fnlp/MOSS-TTSD-v0.5:diana", "欢快女声")
        ]

    # 语音选择（带描述，提升用户体验）
    if model == "FunAudioLLM/CosyVoice2-0.5B":
        voice_index = st.sidebar.selectbox(
            label="选择语音风格",
            options=range(len(voice_options)),
            format_func=lambda x: f"{voice_options[x][0].split(':')[-1]} ({voice_options[x][1]})",
            index=0,
            help=f"当前模型 {model} 支持的预设语音及风格描述",
            key="tts_voice_select1"
        )
    else:  # fnlp/MOSS-TTSD-v0.5
        voice_index = st.sidebar.selectbox(
            label="选择语音风格",
            options=range(len(voice_options)),
            format_func=lambda x: f"{voice_options[x][0].split(':')[-1]} ({voice_options[x][1]})",
            index=0,
            help=f"当前模型 {model} 支持的预设语音及风格描述",
            key="tts_voice_select2"
        )
        
    voice = voice_options[voice_index][0]  # 获取选中的语音ID

    speed = st.sidebar.slider(
        label="语速",
        min_value=0.5,
        max_value=2.0,
        value=1.0,
        step=0.1,
        help="调整语音的播放速度（0.5倍-2.0倍）",
        key="tts_speed_slider"
    )

    format_option = st.sidebar.selectbox(
        label="输出格式",
        options=["mp3", "wav"],
        index=0,
        help="选择生成的音频文件格式（mp3兼容性最佳）",
        key="tts_format_select"
    )

    st.sidebar.markdown("""
    **📌 使用说明：**  
    - 输入要转换为语音的文本内容（建议不超过2000字）
    - 选择模型和语音风格（不同模型支持的风格不同）
    - 调整语速和输出格式
    - 点击"生成语音"按钮等待合成完成
    - 可播放生成的语音或下载保存
    """)

    # 文本输入区
    st.subheader("1. 输入文本内容")
    input_text = st.text_area(
        label="输入要转换为语音的文本",
        height=150,
        placeholder="请输入中文或英文文本（例如：欢迎使用SiliconFlow文字转语音工具）...",
        help="支持中文和英文，单次输入建议不超过2000字符",
        key="tts_text_input"
    )

    # 检测文本变化并重置生成状态
    if input_text != st.session_state.current_text:
        st.session_state.generated_audio = None
        st.session_state.generation_done = False
        st.session_state.current_text = input_text

    # 显示文本统计信息和预估费用
    if input_text:
        char_count = len(input_text)
        # 计算文本字节数和预估费用
        text_bytes = len(input_text.encode('utf-8'))
        estimated_cost = (text_bytes / 1_000_000) * 50
        estimated_cost = max(estimated_cost, 0.10)  # 最低 ¥0.10
        
        # 保存预估费用到session state
        st.session_state.estimated_cost = estimated_cost
        
        # 超过800字符给出警告
        if char_count > 800:
            st.warning(f"文本长度：{char_count} 个字符（超过2000字符，可能影响生成速度）")
        else:
            st.info(f"文本长度：{char_count} 个字符")
            
        # 显示预估费用
        st.info(f"💰 预估费用: ¥{estimated_cost:.2f} (按照 ¥50/百万 UTF-8 字节，最低 ¥0.10)")

    # 语音生成功能区
    st.subheader("2. 生成语音")
    
    # 费用说明
    st.info("💡 未生成完成请勿刷新页面，否则将生成失败，且失败扣除的费用将无法返还")
    
    # 检查是否正在生成语音
    is_tts_generating = st.session_state.get('tts_generation_in_progress', False)
    
    generate_btn = st.button(
        label="🚀 生成语音" if not is_tts_generating else "⏳ 生成进行中...",
        disabled=not (sub_key and input_text) or is_tts_generating,
        type="primary",  # 突出显示生成按钮
        key="tts_generate_btn"
    )

    if generate_btn and not is_tts_generating:
        # 立即设置生成进行中状态并重新渲染
        st.session_state.tts_generation_in_progress = True
        st.rerun()
    
    # 如果生成正在进行，显示处理逻辑
    if st.session_state.tts_generation_in_progress:
        # 确保我们有输入文本
        if not input_text:
            st.error("文本内容丢失，请重新输入")
            st.session_state.tts_generation_in_progress = False
            st.rerun()
        
        # 使用之前计算的费用
        actual_cost = st.session_state.estimated_cost
        
        # 显示费用信息
        st.info(f"📊 文本统计: {len(input_text)} 字符, {len(input_text.encode('utf-8'))} UTF-8 字节")
        st.info(f"💰 实际费用: ¥{actual_cost:.2f} (按照 ¥50/百万 UTF-8 字节)")
    
        # 先验证子密钥并扣除费用
        with st.spinner("🔑 验证子密钥中..."):
            deduction_result = kms_client.validate_and_deduct(sub_key, amount=actual_cost)
            
            if not deduction_result["success"]:
                st.error(f"❌ {deduction_result['error']}")
                if "余额不足" in deduction_result['error']:
                    st.info("💡 请前往密钥管理系统充值或使用其他有效子密钥")
                    # 显示等待信息
                    wait_info = st.info("⏳ 10秒后自动刷新...")
                    time.sleep(10)  # 等待10秒
                    wait_info.empty()  # 清除等待信息
                # 重置生成状态
                st.session_state.tts_generation_in_progress = False
                st.rerun()
        
        # 保存当前费用用于可能的退款
        st.session_state.current_cost = actual_cost

        # 获取一个随机的主密钥
        try:
            siliconflow_master_key = master_key_manager.get_random_master_key()
        except ValueError as e:
            st.error(f"❌ {str(e)}")
            # 重置生成状态
            st.session_state.tts_generation_in_progress = False
            st.rerun()

        # 使用主密钥调用SiliconFlow API
        api_url = "https://api.siliconflow.cn/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {siliconflow_master_key}",  # 使用随机选择的主密钥
            "Content-Type": "application/json"
        }

        # 根据模型调整请求参数
        if model == "FunAudioLLM/CosyVoice2-0.5B":
            payload = {
                "model": model,
                "input": input_text,
                "voice": voice,
                "speed": speed,
                "response_format": format_option
            }
        else:  # fnlp/MOSS-TTSD-v0.5
            payload = {
                "model": model,
                "input": input_text,
                "voice": voice,
                "speed": speed,
                "response_format": format_option
            }

        try:
            # 显示真实加载状态（替代模拟进度条）
            with st.spinner("🔄 正在生成语音，请稍候...（文本越长耗时越久）"):
                response = requests.post(
                    url=api_url,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=300  # 5分钟超时设置
                )

            # 处理API响应
            if response.status_code == 200:
                # 保存生成的音频数据
                st.session_state.generated_audio = response.content
                st.session_state.generation_done = True
                st.success("🎉 语音生成完成！")
            else:
                # 尝试解析错误信息（API可能返回JSON格式错误）
                try:
                    error_detail = response.json().get("error", {}).get("message", "未知错误")
                except:
                    error_detail = response.text
                st.error(f"❌ 语音生成失败！\n错误码：{response.status_code}\n错误信息：{error_detail}")
                
                # 如果API调用失败，退还费用
                with st.spinner("🔄 正在退还费用..."):
                    refund_result = kms_client.validate_and_deduct(sub_key, amount=-st.session_state.current_cost)
                
                if refund_result["success"]:
                    st.session_state.current_balance = refund_result.get("new_balance")
                    st.success(f"💰 已成功退还费用！当前余额: {st.session_state.current_balance:.2f}")
                else:
                    st.warning(f"⚠️ 退款失败: {refund_result['error']}，请联系管理员")

        except requests.exceptions.Timeout:
            st.error("❌ 请求超时！请检查网络或尝试缩短文本长度后重试")
            
            # 如果超时，退还费用
            with st.spinner("🔄 正在退还费用..."):
                refund_result = kms_client.validate_and_deduct(sub_key, amount=-st.session_state.current_cost)
            
            if refund_result["success"]:
                st.session_state.current_balance = refund_result.get("new_balance")
                st.success(f"💰 已成功退还费用！当前余额: {st.session_state.current_balance:.2f}")
            else:
                st.warning(f"⚠️ 退款失败: {refund_result['error']}，请联系管理员")
                
        except requests.exceptions.ConnectionError:
            st.error("❌ 网络连接错误！请检查你的网络设置")
            
            # 如果连接错误，退还费用
            with st.spinner("🔄 正在退还费用..."):
                refund_result = kms_client.validate_and_deduct(sub_key, amount=-st.session_state.current_cost)
            
            if refund_result["success"]:
                st.session_state.current_balance = refund_result.get("new_balance")
                st.success(f"💰 已成功退还费用！当前余额: {st.session_state.current_balance:.2f}")
            else:
                st.warning(f"⚠️ 退款失败: {refund_result['error']}，请联系管理员")
                
        except Exception as e:
            st.error(f"❌ 程序执行出错！\n错误信息：{str(e)}")
            
            # 如果出现异常，退还费用
            with st.spinner("🔄 正在退还费用..."):
                refund_result = kms_client.validate_and_deduct(sub_key, amount=-st.session_state.current_cost)
            
            if refund_result["success"]:
                st.session_state.current_balance = refund_result.get("new_balance")
                st.success(f"💰 已成功退还费用！当前余额: {st.session_state.current_balance:.2f}")
            else:
                st.warning(f"⚠️ 退款失败: {refund_result['error']}，请联系管理员")
        
        finally:
            # 无论成功或失败，都重置生成状态
            st.session_state.tts_generation_in_progress = False
            # 重新渲染页面以更新按钮状态
            st.rerun()

    # 显示生成的语音
    if st.session_state.generation_done and st.session_state.generated_audio:
        st.subheader("3. 生成的语音")
        
        # 显示音频播放器
        st.audio(st.session_state.generated_audio, format=f"audio/{format_option}")
        
        # 提供下载链接
        st.download_button(
            label=f"📥 下载音频 ({format_option.upper()})",
            data=st.session_state.generated_audio,
            file_name=f"tts.{format_option}",
            mime=f"audio/{format_option}",
            type="secondary",
            key="tts_download_btn"
        )

    # 使用说明
    with st.expander("ℹ️ 功能说明与模型差异"):
        st.markdown("""
        #### 语音风格说明    
          `alex`(沉稳男声)、`benjamin`(低沉男声)、`charles`(磁性男声)、`david`(欢快男声)、  
          `anna`(沉稳女声)、`bella`(激情女声)、`claire`(温柔女声)、`diana`(欢快女声)
        
        #### 使用限制
        - 单次文本输入没有上限，但是尽量不超过2000字符
        - 生成时间取决于文本长度和网络状况（通常10-30秒）
        - 需确保子密钥有效且余额充足
        """)