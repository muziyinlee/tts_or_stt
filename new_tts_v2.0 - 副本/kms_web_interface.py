# kms_web_interface.py - 密钥管理Web界面
import streamlit as st
import requests
import time
import json
import os
import random

# 管理员登录配置 - 从 secrets 读取
ADMIN_CONFIG = {
    "username": st.secrets["admin_auth"]["username"],
    "password": st.secrets["admin_auth"]["password"],
    "session_timeout": 24 * 3600  # 24小时超时
}

# 主密钥管理器
class MasterKeyManager:
    def __init__(self, keys_file: str = "master_keys.json"):
        self.keys_file = keys_file
        self.master_keys = self._load_master_keys()
    
    def _load_master_keys(self):
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
    
    def validate_master_key(self, key: str) -> bool:
        """验证主密钥是否有效"""
        return key in self.master_keys

# 初始化主密钥管理器
master_key_manager = MasterKeyManager()

# 页面配置
st.set_page_config(
    page_title="密钥管理系统",
    page_icon="🔑",
    layout="wide"
)

# API客户端
class KMSClient:
    def __init__(self, base_url="http://localhost:8503"):
        self.base_url = base_url
    
    def create_key(self, master_key: str, balance: float, description: str):
        response = requests.post(
            f"{self.base_url}/api/create_key",
            json={
                "master_key": master_key,
                "balance": balance,
                "description": description
            }
        )
        return response.json()
    
    def list_keys(self, master_key: str):
        response = requests.post(
            f"{self.base_url}/api/list_keys",
            json={"master_key": master_key}
        )
        return response.json()
    
    def validate_and_deduct(self, sub_key: str, amount: float = 1.0):
        response = requests.post(
            f"{self.base_url}/api/validate_and_deduct",
            json={"sub_key": sub_key, "amount": amount}
        )
        return response.json()
    
    def get_balance(self, sub_key: str):
        response = requests.post(
            f"{self.base_url}/api/get_balance",
            json={"sub_key": sub_key}
        )
        return response.json()
    
    def update_balance(self, master_key: str, sub_key: str, new_balance: float):
        response = requests.post(
            f"{self.base_url}/api/update_balance",
            json={
                "master_key": master_key,
                "sub_key": sub_key,
                "new_balance": new_balance
            }
        )
        return response.json()
    
    def delete_key(self, master_key: str, sub_key: str):
        """删除子密钥"""
        response = requests.post(
            f"{self.base_url}/api/delete_key",
            json={
                "master_key": master_key,
                "sub_key": sub_key
            }
        )
        return response.json()
    
    def list_master_keys(self, master_key: str):
        """列出主密钥数量"""
        response = requests.post(
            f"{self.base_url}/api/master_keys/list",
            json={"master_key": master_key}
        )
        return response.json()

# 初始化客户端
kms_client = KMSClient()

# 持久化会话管理
class SessionManager:
    def __init__(self):
        self.session_file = ".streamlit/session.json"
    
    def save_session(self, authenticated, login_time, selected_master_key):
        """保存会话状态到文件"""
        try:
            session_data = {
                "authenticated": authenticated,
                "login_time": login_time,
                "selected_master_key": selected_master_key,
                "last_update": time.time()
            }
            os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            st.error(f"保存会话失败: {e}")
            return False
    
    def load_session(self):
        """从文件加载会话状态"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                # 检查会话是否过期
                current_time = time.time()
                if current_time - session_data.get("login_time", 0) > ADMIN_CONFIG["session_timeout"]:
                    self.clear_session()
                    return False, 0, None
                
                return (session_data.get("authenticated", False), 
                       session_data.get("login_time", 0), 
                       session_data.get("selected_master_key", None))
            return False, 0, None
        except Exception as e:
            st.error(f"加载会话失败: {e}")
            return False, 0, None
    
    def clear_session(self):
        """清除会话状态"""
        try:
            if os.path.exists(self.session_file):
                os.remove(self.session_file)
            return True
        except Exception as e:
            st.error(f"清除会话失败: {e}")
            return False

# 初始化会话管理器
session_manager = SessionManager()

# 主应用
def main():
    st.title("🔑 SiliconFlow 密钥管理系统")
    
    # 显示主密钥池状态
    st.sidebar.info(f"🔐 主密钥池: {len(master_key_manager.master_keys)} 个密钥")
    
    # 初始化会话状态 - 从持久化存储加载
    if 'session_initialized' not in st.session_state:
        # 从文件加载会话状态
        authenticated, login_time, selected_master_key = session_manager.load_session()
        
        st.session_state.authenticated = authenticated
        st.session_state.login_time = login_time
        st.session_state.selected_master_key = selected_master_key
        st.session_state.session_initialized = True
    
    # 检查会话超时
    if st.session_state.authenticated and st.session_state.login_time > 0:
        current_time = time.time()
        if current_time - st.session_state.login_time > ADMIN_CONFIG["session_timeout"]:
            st.session_state.authenticated = False
            st.session_state.selected_master_key = None
            st.session_state.login_time = 0
            session_manager.clear_session()
            st.warning("登录已超时，请重新登录")
            st.rerun()
    
    if not st.session_state.authenticated:
        st.subheader("管理员登录")
        
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("用户名", value="")
        with col2:
            password = st.text_input("密码", type="password")
        
        if st.button("登录"):
            if username == ADMIN_CONFIG["username"] and password == ADMIN_CONFIG["password"]:
                st.session_state.authenticated = True
                st.session_state.login_time = time.time()
                # 设置默认选中的主密钥
                if master_key_manager.master_keys:
                    st.session_state.selected_master_key = master_key_manager.master_keys[0]
                
                # 保存会话状态
                session_manager.save_session(
                    st.session_state.authenticated,
                    st.session_state.login_time,
                    st.session_state.selected_master_key
                )
                
                st.success("登录成功！")
                st.rerun()
            else:
                st.error("用户名或密码错误！")
        return
    
    # 显示当前登录状态
    st.sidebar.success(f"✅ 已登录 - 用户: {ADMIN_CONFIG['username']}")
    
    # 主密钥选择器
    if st.session_state.authenticated and master_key_manager.master_keys:
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔑 选择主密钥")
        
        # 创建主密钥选项（显示前8位和后8位以便识别）
        key_options = []
        for key in master_key_manager.master_keys:
            display_name = f"{key[:8]}...{key[-8:]}" if len(key) > 16 else key
            key_options.append((key, display_name))
        
        # 创建选择框
        selected_key_display = st.sidebar.selectbox(
            "选择用于API调用的主密钥",
            options=[opt[0] for opt in key_options],
            format_func=lambda x: next((opt[1] for opt in key_options if opt[0] == x), x),
            key="master_key_selector"
        )
        
        # 更新选中的主密钥并保存
        if selected_key_display != st.session_state.selected_master_key:
            st.session_state.selected_master_key = selected_key_display
            session_manager.save_session(
                st.session_state.authenticated,
                st.session_state.login_time,
                st.session_state.selected_master_key
            )
        
        st.sidebar.info(f"当前使用: {selected_key_display[:8]}...")
        
        # 显示主密钥池状态
        st.sidebar.markdown(f"**主密钥池:** {len(master_key_manager.master_keys)} 个可用")
        
        # 测试主密钥按钮
        if st.sidebar.button("测试当前主密钥"):
            # 使用占位符显示测试状态
            test_placeholder = st.sidebar.empty()
            test_placeholder.info("🔄 测试中...")
            try:
                # 简单的API测试
                test_response = requests.get(
                    "https://api.siliconflow.cn/v1/models",
                    headers={"Authorization": f"Bearer {st.session_state.selected_master_key}"},
                    timeout=5
                )
                if test_response.status_code == 200:
                    test_placeholder.success("✅ 主密钥有效")
                else:
                    test_placeholder.error(f"❌ 主密钥无效 (状态码: {test_response.status_code})")
            except Exception as e:
                test_placeholder.error(f"❌ 测试失败: {str(e)}")
        
        # 随机轮换按钮
        if st.sidebar.button("随机切换主密钥"):
            new_key = random.choice(master_key_manager.master_keys)
            st.session_state.selected_master_key = new_key
            session_manager.save_session(
                st.session_state.authenticated,
                st.session_state.login_time,
                st.session_state.selected_master_key
            )
            st.sidebar.success(f"已随机切换到: {new_key[:8]}...")
            st.rerun()
    
    # 检查是否已选择主密钥
    if not st.session_state.selected_master_key:
        st.warning("⚠️ 请先在侧边栏选择一个主密钥")
        return
    
    # 主功能界面
    tab1, tab2, tab3 = st.tabs(["创建密钥", "管理密钥", "系统信息"])
    
    with tab1:
        st.subheader("创建新子密钥")
        
        # 显示当前使用的主密钥
        current_key_index = master_key_manager.master_keys.index(st.session_state.selected_master_key) + 1
        st.info(f"**当前使用的主密钥:** 主密钥 {current_key_index} ({st.session_state.selected_master_key[:8]}...)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            balance = st.number_input("设置余额", min_value=0.0, value=10.0, step=10.0, format="%.2f")
            description = st.text_input("密钥描述", placeholder="例如：测试用密钥、项目A专用等")
        
        with col2:
            st.info("""**创建说明：**
            - 密钥描述有助于识别用途
            - 新密钥将立即生效
            """)
        
        if st.button("🎯 生成子密钥", type="primary"):
            with st.spinner("正在生成密钥..."):
                result = kms_client.create_key(st.session_state.selected_master_key, balance, description)
                
            if result["success"]:
                st.success("子密钥创建成功！")
                st.text_area("新子密钥", result["sub_key"], height=100)
                st.info(f"**初始余额:** {result['balance']:.2f}")
                st.info("**请妥善保存此密钥，页面刷新后将无法再次查看完整密钥**")
            else:
                st.error(f"密钥创建失败：{result['error']}")
    
    with tab2:
        st.subheader("密钥管理")
        
        # 显示当前使用的主密钥
        current_key_index = master_key_manager.master_keys.index(st.session_state.selected_master_key) + 1
        st.info(f"**当前使用的主密钥:** 主密钥 {current_key_index} ({st.session_state.selected_master_key[:8]}...)")
        
        # 获取所有密钥
        with st.spinner("加载密钥列表中..."):
            result = kms_client.list_keys(st.session_state.selected_master_key)
        
        if not result["success"]:
            st.error(f"加载失败：{result['error']}")
            return
        
        keys = result.get("keys", {})
        
        if not keys:
            st.info("暂无子密钥")
        else:
            # 总体统计
            total_keys = len(keys)
            active_keys = sum(1 for k in keys.values() if k['is_active'])
            total_balance = sum(float(k['balance']) for k in keys.values())
            total_used = sum(float(k.get('used_amount', 0)) for k in keys.values())
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("总密钥数", total_keys)
            col2.metric("活跃密钥", active_keys)
            col3.metric("总余额", f"{total_balance:.2f}")
            col4.metric("总使用量", f"{total_used:.2f}")
            
            st.markdown("---")
            
            # 密钥详情
            for key_id, key_info in keys.items():
                with st.expander(f"密钥: {key_id[:16]}... | 余额: {float(key_info['balance']):.2f} | 状态: {'✅ 活跃' if key_info['is_active'] else '❌ 停用'}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**完整密钥:** `{key_id}`")
                        st.write(f"**描述:** {key_info.get('description', '无')}")
                        st.write(f"**创建时间:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(key_info['created_time']))}")
                        st.write(f"**已使用:** {float(key_info.get('used_amount', 0)):.2f}")
                        if key_info.get('last_used'):
                            st.write(f"**最后使用:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(key_info['last_used']))}")
                    
                    with col2:
                        # 余额管理
                        new_balance = st.number_input(
                            "新余额", 
                            value=float(key_info['balance']),
                            key=f"balance_{key_id}",
                            min_value=0.00,
                            format="%.2f"
                        )
                        if st.button("更新余额", key=f"update_balance_{key_id}"):
                            update_result = kms_client.update_balance(st.session_state.selected_master_key, key_id, new_balance)
                            if update_result["success"]:
                                st.success("余额更新成功！")
                                st.rerun()
                            else:
                                st.error(f"更新失败：{update_result['error']}")
                        
                        # 测试密钥按钮
                        if st.button("测试密钥", key=f"test_{key_id}"):
                            test_result = kms_client.validate_and_deduct(key_id, 0)  # 扣除0，只验证
                            if test_result["success"]:
                                st.success("密钥有效！")
                            else:
                                st.error(f"密钥无效：{test_result['error']}")
                        
                        # 删除密钥按钮
                        st.markdown("---")
                        if st.button("🗑️ 删除密钥", key=f"delete_{key_id}", type="secondary"):
                            delete_result = kms_client.delete_key(st.session_state.selected_master_key, key_id)
                            if delete_result["success"]:
                                st.success("密钥删除成功！")
                                st.rerun()
                            else:
                                st.error(f"删除失败：{delete_result['error']}")

    with tab3:
        st.subheader("系统信息")
        
        # 显示当前使用的主密钥
        current_key_index = master_key_manager.master_keys.index(st.session_state.selected_master_key) + 1
        st.info(f"**当前使用的主密钥:** 主密钥 {current_key_index} ({st.session_state.selected_master_key[:8]}...)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("系统状态")
            
            # 健康检查
            try:
                health_response = requests.get("http://localhost:8503/health", timeout=5)
                if health_response.status_code == 200:
                    health_data = health_response.json()
                    st.success("✅ API服务器运行正常")
                    st.write(f"- 服务状态: {health_data.get('status', 'unknown')}")
                    st.write(f"- 子密钥总数: {health_data.get('total_keys', 0)}")
                    st.write(f"- 主密钥数量: {health_data.get('master_keys_count', 0)}")
                    st.write(f"- 最后检查: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    st.error("❌ API服务器异常")
            except Exception as e:
                st.error(f"❌ 无法连接到API服务器: {str(e)}")
            
            # 主密钥池信息
            st.info("主密钥池状态")
            st.write(f"- 可用主密钥: {len(master_key_manager.master_keys)} 个")
            
            # 列出所有主密钥（隐藏完整内容）
            with st.expander("查看主密钥列表（隐藏完整内容）"):
                for i, key in enumerate(master_key_manager.master_keys):
                    is_current = key == st.session_state.selected_master_key
                    prefix = "✅ " if is_current else "  "
                    st.text(f"{prefix}主密钥 {i+1}: {key[:12]}...{key[-12:]}")
            
            # 列出主密钥数量（通过API）
            if st.button("刷新主密钥信息"):
                result = kms_client.list_master_keys(st.session_state.selected_master_key)
                if result["success"]:
                    st.write(f"- API服务器报告: {result.get('total_keys', 0)} 个主密钥")
                else:
                    st.write(f"- API服务器查询失败: {result.get('error', '未知错误')}")
        
        with col2:
            st.info("使用说明")
            st.markdown("""**系统功能:**
            - 🔑 创建和管理子密钥
            - 💰 设置和调整密钥余额
            - 📊 监控密钥使用情况
            - 🗑️ 删除不需要的密钥
            
            **安全特性:**
            - 主密钥池管理，提高安全性
            - 支持多个主密钥轮换使用
            - 密钥信息加密存储
            
            **主密钥管理:**
            - 在侧边栏选择要使用的主密钥
            - 可测试主密钥有效性
            - 支持随机切换主密钥
            
            **注意事项:**
            - 请妥善保管主密钥
            - 定期轮换主密钥以提高安全性
            - 监控密钥使用情况，防止滥用
            """)
        
        # 退出登录
        st.markdown("---")
        if st.button("🚪 退出登录"):
            st.session_state.authenticated = False
            st.session_state.selected_master_key = None
            st.session_state.login_time = 0
            session_manager.clear_session()
            st.success("已退出登录")
            st.rerun()

if __name__ == "__main__":
    main()