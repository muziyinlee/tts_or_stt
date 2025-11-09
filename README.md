# tts_or_stt
tts or stt

需要安装ffmpeg  
python需要3.8以上

#### 基于siliconflow
- FunAudioLLM/SenseVoiceSmall
- FunAudioLLM/CosyVoice2-0.5B
- 理论支持中文（含方言：粤语、四川话、上海话、天津话等）、英文、日语、韩语，支持跨语言和混合语言场景


#### 启动
- 安装依赖
```
pip install -r requirements.txt
```

- windows命令行
```
streamlit run tts_or_stt.py --server.port 8501
```
或直接运行 start.bat
