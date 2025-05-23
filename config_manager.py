import os
import json
import winreg

class ConfigManager:
    def __init__(self):
        pass

    def load_config(self):
        config = {}
        # 1. 先尝试从注册表读取
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\PMCL\\Config")
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    config[name] = value
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except Exception:
            pass
        # 2. 如果注册表没有内容，尝试读取本地文件并导入
        if not config:
            config_path = os.path.join('PMCL', 'config', 'launcher_config.json')
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    # 写入注册表
                    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\\PMCL\\Config")
                    for k, v in config.items():
                        winreg.SetValueEx(key, k, 0, winreg.REG_SZ, str(v))
                    winreg.CloseKey(key)
                    print("[INFO] 已自动导入本地配置到注册表")
                    # 可选：os.remove(config_path)
                except Exception as e:
                    print("导入本地配置失败：", e)
        return config

    def save_config(self, config):
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\\PMCL\\Config")
            for k, v in config.items():
                winreg.SetValueEx(key, k, 0, winreg.REG_SZ, str(v))
            winreg.CloseKey(key)
        except Exception as e:
            print("写入注册表配置失败：", e) 