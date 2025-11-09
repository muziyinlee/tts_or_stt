# kms_api_server.py - 独立的密钥管理API服务器
import uuid
import time
import hashlib
import json
import os
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, List
from flask import Flask, request, jsonify
from flask_cors import CORS

class MasterKeyManager:
    def __init__(self, keys_file: str = "master_keys.json"):
        self.keys_file = keys_file
        self.master_keys = self._load_master_keys()
    
    def _load_master_keys(self) -> List[str]:
        """从JSON文件加载主密钥池"""
        try:
            if os.path.exists(self.keys_file):
                with open(self.keys_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("master_keys", [])
            else:
                # 如果文件不存在，创建一个空的示例文件
                default_keys = {
                    "master_keys": [
                        "sk-your-default-master-key-here-replace-in-production"
                    ]
                }
                with open(self.keys_file, 'w', encoding='utf-8') as f:
                    json.dump(default_keys, f, indent=2)
                print(f"警告: 主密钥文件不存在，已创建示例文件 {self.keys_file}")
                print("请编辑该文件并添加实际的主密钥")
                return default_keys["master_keys"]
        except Exception as e:
            print(f"加载主密钥文件失败: {e}")
            return []
    
    def validate_master_key(self, key: str) -> bool:
        """验证主密钥是否有效"""
        return key in self.master_keys
    
    def add_master_key(self, new_key: str) -> bool:
        """添加新的主密钥"""
        if new_key not in self.master_keys:
            self.master_keys.append(new_key)
            return self._save_master_keys()
        return False
    
    def remove_master_key(self, key: str) -> bool:
        """移除主密钥"""
        if key in self.master_keys:
            self.master_keys.remove(key)
            return self._save_master_keys()
        return False
    
    def _save_master_keys(self) -> bool:
        """保存主密钥到文件"""
        try:
            with open(self.keys_file, 'w', encoding='utf-8') as f:
                json.dump({"master_keys": self.master_keys}, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存主密钥文件失败: {e}")
            return False

class KeyManagementSystem:
    def __init__(self, storage_file: str = "keys.json"):
        self.storage_file = storage_file
        self.keys = self._load_keys()
    
    def _load_keys(self) -> Dict:
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 转换所有余额为Decimal类型
                    for key_info in data.values():
                        if isinstance(key_info.get("balance"), (int, float)):
                            key_info["balance"] = float(self._round_decimal(Decimal(str(key_info["balance"]))))
                    return data
        except Exception as e:
            print(f"加载密钥文件失败: {e}")
        return {}
    
    def _save_keys(self):
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.keys, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存密钥文件失败: {e}")
            return False
    
    def _generate_sub_key(self) -> str:
        key_base = f"sk-{uuid.uuid4().hex}{int(time.time())}"
        return hashlib.sha256(key_base.encode()).hexdigest()[:32]
    
    def _round_decimal(self, value: Decimal) -> Decimal:
        """四舍五入到小数点后两位"""
        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def _to_decimal(self, value) -> Decimal:
        """转换为Decimal并四舍五入"""
        if isinstance(value, Decimal):
            return self._round_decimal(value)
        return self._round_decimal(Decimal(str(value)))
    
    def create_sub_key(self, balance: float = 100.00, description: str = "") -> Optional[str]:
        sub_key = self._generate_sub_key()
        
        balance_decimal = self._to_decimal(balance)
        
        self.keys[sub_key] = {
            "balance": float(balance_decimal),  # 存储为浮点数，但已经是精确的两位小数
            "created_time": time.time(),
            "description": description,
            "is_active": True,
            "used_amount": 0.0,
            "last_used": None
        }
        
        if self._save_keys():
            return sub_key
        return None
    
    def update_balance(self, sub_key: str, new_balance: float) -> bool:
        """更新子密钥余额"""
        if sub_key not in self.keys:
            return False
        
        new_balance_decimal = self._to_decimal(new_balance)
        self.keys[sub_key]["balance"] = float(new_balance_decimal)
        return self._save_keys()
    
    def deduct_balance(self, sub_key: str, amount: float) -> bool:
        """扣除余额（支持负数金额用于退款）"""
        if sub_key not in self.keys:
            return False
        
        if not self.keys[sub_key]["is_active"]:
            return False
        
        current_balance = Decimal(str(self.keys[sub_key]["balance"]))
        amount_decimal = self._to_decimal(amount)
        
        # 支持负数金额（退款）
        if amount_decimal < 0:
            new_balance = current_balance - amount_decimal  # 减去负数等于加
            self.keys[sub_key]["used_amount"] = float(Decimal(str(self.keys[sub_key]["used_amount"])) + amount_decimal)
        else:
            # 正常扣款
            if current_balance < amount_decimal:
                return False
            new_balance = current_balance - amount_decimal
            self.keys[sub_key]["used_amount"] = float(Decimal(str(self.keys[sub_key]["used_amount"])) + amount_decimal)
        
        # 四舍五入并存储
        self.keys[sub_key]["balance"] = float(self._round_decimal(new_balance))
        self.keys[sub_key]["last_used"] = time.time()
        return self._save_keys()
    
    def get_balance(self, sub_key: str) -> Optional[float]:
        if sub_key in self.keys and self.keys[sub_key]["is_active"]:
            # 返回时确保是两位小数
            balance = self.keys[sub_key]["balance"]
            return float(self._round_decimal(Decimal(str(balance))))
        return None
    
    def validate_key(self, sub_key: str) -> bool:
        return (sub_key in self.keys and 
                self.keys[sub_key]["is_active"] and 
                self.keys[sub_key]["balance"] > 0)
    
    def list_keys(self) -> Dict:
        # 确保返回的余额都是精确到两位小数
        result = {}
        for key, info in self.keys.items():
            result[key] = info.copy()
            result[key]["balance"] = float(self._round_decimal(Decimal(str(info["balance"]))))
        return result
    
    def deactivate_key(self, sub_key: str) -> bool:
        """停用子密钥"""
        if sub_key in self.keys:
            self.keys[sub_key]["is_active"] = False
            return self._save_keys()
        return False
    
    def activate_key(self, sub_key: str) -> bool:
        """激活子密钥"""
        if sub_key in self.keys:
            self.keys[sub_key]["is_active"] = True
            return self._save_keys()
        return False
    
    def delete_key(self, sub_key: str) -> bool:
        """删除子密钥"""
        if sub_key in self.keys:
            del self.keys[sub_key]
            return self._save_keys()
        return False

# 初始化主密钥管理器和密钥管理系统
master_key_manager = MasterKeyManager()
kms = KeyManagementSystem()

# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

@app.route('/api/validate_and_deduct', methods=['POST'])
def api_validate_and_deduct():
    """验证密钥并扣除余额（支持负数退款）"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "缺少请求数据"})
        
        sub_key = data.get('sub_key')
        amount = data.get('amount', 1.0)
        
        if not sub_key:
            return jsonify({"success": False, "error": "缺少子密钥"})
        
        # 检查密钥是否存在和是否活跃
        if sub_key not in kms.keys or not kms.keys[sub_key]["is_active"]:
            return jsonify({"success": False, "error": "密钥无效"})
        
        # 使用Decimal进行精确比较
        current_balance = Decimal(str(kms.keys[sub_key]["balance"]))
        amount_decimal = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # 如果是扣款（正数），检查余额是否足够
        if amount_decimal > 0 and current_balance < amount_decimal:
            return jsonify({"success": False, "error": "余额不足"})
        
        # 执行扣款或退款
        if kms.deduct_balance(sub_key, float(amount_decimal)):
            new_balance = kms.get_balance(sub_key)
            return jsonify({
                "success": True, 
                "new_balance": new_balance,
                "action": "refund" if amount_decimal < 0 else "deduct"
            })
        else:
            return jsonify({"success": False, "error": "操作失败"})
            
    except Exception as e:
        return jsonify({"success": False, "error": f"服务器错误: {str(e)}"})

@app.route('/api/get_balance', methods=['POST'])
def api_get_balance():
    """查询余额"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "缺少请求数据"})
        
        sub_key = data.get('sub_key')
        
        if not sub_key:
            return jsonify({"success": False, "error": "缺少子密钥"})
        
        balance = kms.get_balance(sub_key)
        if balance is not None:
            return jsonify({"success": True, "balance": balance})
        else:
            return jsonify({"success": False, "error": "密钥不存在或已停用"})
            
    except Exception as e:
        return jsonify({"success": False, "error": f"服务器错误: {str(e)}"})

@app.route('/api/create_key', methods=['POST'])
def api_create_key():
    """创建新密钥"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "缺少请求数据"})
        
        master_key = data.get('master_key')
        balance = data.get('balance', 100.00)
        description = data.get('description', '')
        
        if not master_key_manager.validate_master_key(master_key):
            return jsonify({"success": False, "error": "主密钥验证失败"})
        
        # 确保余额是两位小数
        balance_decimal = Decimal(str(balance)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        sub_key = kms.create_sub_key(float(balance_decimal), description)
        if sub_key:
            return jsonify({"success": True, "sub_key": sub_key, "balance": float(balance_decimal)})
        else:
            return jsonify({"success": False, "error": "密钥创建失败"})
            
    except Exception as e:
        return jsonify({"success": False, "error": f"服务器错误: {str(e)}"})

@app.route('/api/list_keys', methods=['POST'])
def api_list_keys():
    """列出所有密钥"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "缺少请求数据"})
        
        master_key = data.get('master_key')
        
        if not master_key_manager.validate_master_key(master_key):
            return jsonify({"success": False, "error": "主密钥验证失败"})
        
        keys = kms.list_keys()
        return jsonify({"success": True, "keys": keys})
            
    except Exception as e:
        return jsonify({"success": False, "error": f"服务器错误: {str(e)}"})

@app.route('/api/update_balance', methods=['POST'])
def api_update_balance():
    """更新密钥余额"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "缺少请求数据"})
        
        master_key = data.get('master_key')
        sub_key = data.get('sub_key')
        new_balance = data.get('new_balance')
        
        if not master_key_manager.validate_master_key(master_key):
            return jsonify({"success": False, "error": "主密钥验证失败"})
        
        if not sub_key or new_balance is None:
            return jsonify({"success": False, "error": "缺少必要参数"})
        
        # 确保新余额是两位小数
        new_balance_decimal = Decimal(str(new_balance)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if kms.update_balance(sub_key, float(new_balance_decimal)):
            return jsonify({"success": True, "new_balance": float(new_balance_decimal)})
        else:
            return jsonify({"success": False, "error": "更新失败"})
            
    except Exception as e:
        return jsonify({"success": False, "error": f"服务器错误: {str(e)}"})

@app.route('/api/delete_key', methods=['POST'])
def api_delete_key():
    """删除子密钥"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "缺少请求数据"})
        
        master_key = data.get('master_key')
        sub_key = data.get('sub_key')
        
        if not master_key_manager.validate_master_key(master_key):
            return jsonify({"success": False, "error": "主密钥验证失败"})
        
        if not sub_key:
            return jsonify({"success": False, "error": "缺少子密钥"})
        
        if kms.delete_key(sub_key):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "删除失败"})
            
    except Exception as e:
        return jsonify({"success": False, "error": f"服务器错误: {str(e)}"})

# 主密钥管理API
@app.route('/api/master_keys/list', methods=['POST'])
def api_list_master_keys():
    """列出主密钥（仅显示数量，不显示具体密钥）"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "缺少请求数据"})
        
        master_key = data.get('master_key')
        
        if not master_key_manager.validate_master_key(master_key):
            return jsonify({"success": False, "error": "主密钥验证失败"})
        
        return jsonify({
            "success": True, 
            "total_keys": len(master_key_manager.master_keys),
            "keys_count": len(master_key_manager.master_keys)
        })
            
    except Exception as e:
        return jsonify({"success": False, "error": f"服务器错误: {str(e)}"})

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "healthy", 
        "service": "Key Management API",
        "timestamp": time.time(),
        "total_keys": len(kms.keys),
        "master_keys_count": len(master_key_manager.master_keys)
    })

if __name__ == '__main__':
    print("=" * 50)
    print("密钥管理API服务器启动")
    print("=" * 50)
    print("地址: http://localhost:8503")
    print(f"主密钥池: {len(master_key_manager.master_keys)} 个密钥")
    print("API端点:")
    print("  - POST /api/validate_and_deduct - 验证并扣除余额")
    print("  - POST /api/get_balance - 查询余额")
    print("  - POST /api/create_key - 创建新密钥")
    print("  - POST /api/list_keys - 列出所有密钥")
    print("  - POST /api/update_balance - 更新余额")
    print("  - POST /api/delete_key - 删除密钥")
    print("  - POST /api/master_keys/list - 列出主密钥数量")
    print("  - GET  /health - 健康检查")
    print("=" * 50)
    app.run(host='0.0.0.0', port=8503, debug=False)