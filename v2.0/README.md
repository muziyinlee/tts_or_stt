# tts or stt v2.0
需要安装ffmpeg  
python需要3.8以上

#### 基于 Siliconflow api token
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
streamlit run kms_web_interface.py --server.port 8502
python kms_api_server.py
```

或者直接运行 start.bat 输入：1 全部启动

#### 说明
v2.0是中间件子密钥程序，通过子密钥API来连接siliconflow API token  
tts_or_stt.py localhost:8501 是主页  
kms_web_interface.py localhost:8502 是子密钥管理  
kms_api_server localhost:8503 是中间服务器  

- .streamlit/secrets.toml 是子密钥管理页面的用户名和密码
```
[admin_auth]
username = ""
password = ""
```

- master_keys.json 设置Siliconflow api token为主密钥（可设置多个）
- 使用前优先设置才能创建子密钥
```
{
  "master_keys": [
    "sk-key1",
    "sk-key2"
  ]
}
```

- keys.json 储存子密钥（会自动创建）

#### 子密钥扣费说明
- 音频转文字 是根据音频大小来计算的：¥0.50/MB，每次最低扣除 ¥0.10
- 文字转音频 是按照字符数来计算的： ¥50/百万 UTF-8 字节，每次最低扣除 ¥0.10
