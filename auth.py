import os
import json
import requests
import hashlib
import uuid
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.fernet import Fernet
import winreg

class MinecraftAuth:
    def __init__(self):
        self.auth_server = "https://authserver.mojang.com"
        self.littleskin_api = "https://littleskin.cn/api/yggdrasil"
        # self.base_dir = "PMCL"
        # self.profiles_dir = os.path.join(self.base_dir, "profiles")
        # self.config_dir = os.path.join(self.base_dir, "config")
        # self.config_file = os.path.join(self.config_dir, "auth_config.json")
        # self.key_file = os.path.join(self.config_dir, "auth_key.key")
        # os.makedirs(self.profiles_dir, exist_ok=True)
        # os.makedirs(self.config_dir, exist_ok=True)
        self._init_encryption()
        
    def _init_encryption(self):
        """初始化加密密钥（如需可迁移到注册表，否则可用内存密钥/默认密钥）"""
        # 这里建议直接用内存密钥或硬编码密钥，避免本地文件
        key = b'0123456789abcdef0123456789abcdef'  # 示例固定密钥，实际可更安全
        self.cipher = Fernet(base64.urlsafe_b64encode(key))
    
    def _encrypt_password(self, password):
        """加密密码"""
        return self.cipher.encrypt(password.encode()).decode()
    
    def _decrypt_password(self, encrypted_password):
        """解密密码"""
        return self.cipher.decrypt(encrypted_password.encode()).decode()
    
    def _save_config(self, config):
        # 已弃用本地文件，仅保留注册表逻辑
        pass
    
    def _load_config(self):
        # 已弃用本地文件，仅保留注册表逻辑
        return {"auto_login": None, "remembered_accounts": []}
    
    def set_auto_login(self, username):
        """设置自动登录账号"""
        config = self._load_config()
        config["auto_login"] = username
        self._save_config(config)
    
    def get_auto_login(self):
        """获取自动登录账号"""
        config = self._load_config()
        return config.get("auto_login")
    
    def remember_account(self, username, password, account_type):
        """记住账号密码"""
        config = self._load_config()
        remembered = {
            "username": username,
            "password": self._encrypt_password(password),
            "type": account_type
        }
        
        # 检查是否已存在
        for i, acc in enumerate(config["remembered_accounts"]):
            if acc["username"] == username:
                config["remembered_accounts"][i] = remembered
                break
        else:
            config["remembered_accounts"].append(remembered)
        
        self._save_config(config)
    
    def get_remembered_account(self, username):
        """获取记住的账号信息"""
        config = self._load_config()
        for acc in config["remembered_accounts"]:
            if acc["username"] == username:
                return {
                    "username": acc["username"],
                    "password": self._decrypt_password(acc["password"]),
                    "type": acc["type"]
                }
        return None
    
    def remove_remembered_account(self, username):
        """删除记住的账号"""
        config = self._load_config()
        config["remembered_accounts"] = [acc for acc in config["remembered_accounts"] 
                                       if acc["username"] != username]
        self._save_config(config)
    
    def mojang_login(self, email, password, remember=False):
        """正版登录"""
        try:
            # 获取访问令牌
            data = {
                "agent": {
                    "name": "Minecraft",
                    "version": 1
                },
                "username": email,
                "password": password,
                "requestUser": True
            }
            
            response = requests.post(f"{self.auth_server}/authenticate", json=data)
            if response.status_code != 200:
                return False, "登录失败：邮箱或密码错误"
            
            auth_data = response.json()
            
            # 保存认证信息
            profile = {
                "type": "mojang",
                "access_token": auth_data["accessToken"],
                "client_token": auth_data["clientToken"],
                "uuid": auth_data["selectedProfile"]["id"],
                "name": auth_data["selectedProfile"]["name"]
            }
            
            self._save_profile(profile)
            
            # 记住密码
            if remember:
                self.remember_account(email, password, "mojang")
            
            return True, profile
            
        except Exception as e:
            return False, f"登录失败：{str(e)}"
    
    def offline_login(self, username, remember=False):
        """离线登录"""
        try:
            # 生成离线UUID
            offline_uuid = str(uuid.uuid3(uuid.NAMESPACE_URL, f"OfflinePlayer:{username}"))
            
            profile = {
                "type": "offline",
                "uuid": offline_uuid,
                "name": username
            }
            
            self._save_profile(profile)
            
            # 记住账号
            if remember:
                self.remember_account(username, "", "offline")
            
            return True, profile
            
        except Exception as e:
            return False, f"登录失败：{str(e)}"
    
    def littleskin_login(self, email, password, remember=False):
        """LittleSkin登录"""
        try:
            # 获取访问令牌
            data = {
                "agent": {
                    "name": "Minecraft",
                    "version": 1
                },
                "username": email,
                "password": password,
                "requestUser": True
            }
            
            response = requests.post(f"{self.littleskin_api}/authserver/authenticate", json=data)
            if response.status_code != 200:
                return False, "登录失败：邮箱或密码错误"
            
            auth_data = response.json()
            
            # 保存认证信息
            profile = {
                "type": "littleskin",
                "access_token": auth_data["accessToken"],
                "client_token": auth_data["clientToken"],
                "uuid": auth_data["selectedProfile"]["id"],
                "name": auth_data["selectedProfile"]["name"]
            }
            
            self._save_profile(profile)
            
            # 记住密码
            if remember:
                self.remember_account(email, password, "littleskin")
            
            return True, profile
            
        except Exception as e:
            return False, f"登录失败：{str(e)}"
    
    def _save_profile(self, profile):
        """保存登录信息"""
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\\PMCL\\Profiles")
            username = profile.get('name', '')
            winreg.SetValueEx(key, username, 0, winreg.REG_SZ, json.dumps(profile, ensure_ascii=False))
            winreg.CloseKey(key)
        except Exception as e:
            print("写入注册表账号失败：", e)
    
    def get_saved_profiles(self):
        profiles = []
        # 1. 先尝试从注册表读取
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\PMCL\\Profiles")
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    profile = json.loads(value)
                    profiles.append(profile)
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except Exception:
            pass
        # 2. 如果注册表没有内容，尝试读取本地profiles并导入
        if not profiles:
            profiles_dir = os.path.join('PMCL', 'profiles')
            if os.path.exists(profiles_dir):
                for filename in os.listdir(profiles_dir):
                    if filename.endswith('.json'):
                        path = os.path.join(profiles_dir, filename)
                        with open(path, 'r', encoding='utf-8') as f:
                            profile = json.load(f)
                            profiles.append(profile)
                # 写入注册表
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\\PMCL\\Profiles")
                for profile in profiles:
                    username = profile.get('name', '')
                    winreg.SetValueEx(key, username, 0, winreg.REG_SZ, json.dumps(profile, ensure_ascii=False))
                winreg.CloseKey(key)
                print("[INFO] 已自动导入本地账号到注册表")
                # 可选：删除本地profiles目录
        return profiles
    
    def delete_profile(self, username):
        """删除登录信息"""
        # profile_path = os.path.join(self.profiles_dir, f"{username}.json")
        # if os.path.exists(profile_path):
        #     os.remove(profile_path)
        #     # 同时删除记住的账号
        #     self.remove_remembered_account(username)
        #     return True
        # return False
        # 改为只删注册表
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\PMCL\\Profiles", 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, username)
            winreg.CloseKey(key)
            self.remove_remembered_account(username)
            return True
        except Exception:
            return False
    
    def validate_token(self, profile):
        """验证令牌是否有效"""
        if profile["type"] == "offline":
            return True
            
        try:
            data = {
                "accessToken": profile["access_token"],
                "clientToken": profile["client_token"]
            }
            
            if profile["type"] == "mojang":
                response = requests.post(f"{self.auth_server}/validate", json=data)
            else:  # littleskin
                response = requests.post(f"{self.littleskin_api}/authserver/validate", json=data)
                
            return response.status_code == 204
            
        except:
            return False
    
    def refresh_token(self, profile):
        """刷新令牌"""
        if profile["type"] == "offline":
            return True, profile
            
        try:
            data = {
                "accessToken": profile["access_token"],
                "clientToken": profile["client_token"],
                "requestUser": True
            }
            
            if profile["type"] == "mojang":
                response = requests.post(f"{self.auth_server}/refresh", json=data)
            else:  # littleskin
                response = requests.post(f"{self.littleskin_api}/authserver/refresh", json=data)
                
            if response.status_code != 200:
                return False, "刷新令牌失败"
                
            auth_data = response.json()
            profile["access_token"] = auth_data["accessToken"]
            self._save_profile(profile)
            return True, profile
            
        except Exception as e:
            return False, f"刷新令牌失败：{str(e)}" 