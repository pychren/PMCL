import os
import subprocess
from PyQt5.QtWidgets import QMessageBox

class GameLauncher:
    def __init__(self):
        pass

    def launch_game(self, current_profile, game_dir, version, memory_combo, memory_input):
        if not current_profile:
            QMessageBox.warning(None, "错误", "请先登录！")
            return
            
        if not game_dir:
            QMessageBox.warning(None, "错误", "请选择游戏目录！")
            return
            
        jar_path = os.path.join(game_dir, "versions", version, f"{version}.jar")
        if not os.path.exists(jar_path):
            QMessageBox.warning(None, "错误", f"未找到 {jar_path}，请先下载！")
            return
        
        # 获取内存参数
        memory = memory_combo.currentText()
        if memory == "自定义":
            memory = memory_input.text().strip()
            if not memory:
                QMessageBox.warning(None, "错误", "请输入自定义内存大小，如 6G 或 4096M")
                return
        
        java_path = "java"  # 假设Java在系统PATH中
        game_args = [
            java_path,
            f"-Xmx{memory}",  # 最大内存
            "-XX:+UnlockExperimentalVMOptions",
            "-XX:+UseG1GC",
            "-XX:G1NewSizePercent=20",
            "-XX:G1ReservePercent=20",
            "-XX:MaxGCPauseMillis=50",
            "-XX:G1HeapRegionSize=32M",
            "-jar", jar_path,
            "--username", current_profile["name"],
            "--uuid", current_profile["uuid"],
            "--gameDir", game_dir,
            "--assetsDir", os.path.join(game_dir, "assets"),
            "--assetIndex", version
        ]
        
        # 添加认证信息
        if current_profile["type"] != "offline":
            game_args.extend([
                "--accessToken", current_profile["access_token"]
            ])
        
        print("Attempting to launch game with args:", game_args)

        try:
            subprocess.Popen(game_args)
            QMessageBox.information(None, "提示", f"已启动Minecraft {version}")
        except Exception as e:
            QMessageBox.warning(None, "错误", f"启动失败: {e}") 