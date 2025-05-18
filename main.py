import sys
import os
import json
import requests
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QPushButton, QComboBox, QLabel,
                           QLineEdit, QMessageBox, QFileDialog, QProgressBar,
                           QDialog, QTabWidget, QFormLayout, QGroupBox,
                           QCheckBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from downloader import MinecraftDownloader
from auth import MinecraftAuth
import subprocess

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("登录")
        self.setMinimumWidth(400)
        self.auth = MinecraftAuth()
        self.current_profile = None
        self.create_ui()
        
    def create_ui(self):
        layout = QVBoxLayout(self)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 正版登录
        mojang_tab = QWidget()
        mojang_layout = QFormLayout()
        self.mojang_email = QLineEdit()
        self.mojang_password = QLineEdit()
        self.mojang_password.setEchoMode(QLineEdit.Password)
        self.mojang_remember = QCheckBox("记住密码")
        mojang_layout.addRow("邮箱:", self.mojang_email)
        mojang_layout.addRow("密码:", self.mojang_password)
        mojang_layout.addRow("", self.mojang_remember)
        mojang_tab.setLayout(mojang_layout)
        
        # 离线登录
        offline_tab = QWidget()
        offline_layout = QFormLayout()
        self.offline_username = QLineEdit()
        self.offline_remember = QCheckBox("记住账号")
        offline_layout.addRow("用户名:", self.offline_username)
        offline_layout.addRow("", self.offline_remember)
        offline_tab.setLayout(offline_layout)
        
        # LittleSkin登录
        littleskin_tab = QWidget()
        littleskin_layout = QFormLayout()
        self.littleskin_email = QLineEdit()
        self.littleskin_password = QLineEdit()
        self.littleskin_password.setEchoMode(QLineEdit.Password)
        self.littleskin_remember = QCheckBox("记住密码")
        littleskin_layout.addRow("邮箱:", self.littleskin_email)
        littleskin_layout.addRow("密码:", self.littleskin_password)
        littleskin_layout.addRow("", self.littleskin_remember)
        littleskin_tab.setLayout(littleskin_layout)
        
        # 添加标签页
        tab_widget.addTab(mojang_tab, "正版登录")
        tab_widget.addTab(offline_tab, "离线登录")
        tab_widget.addTab(littleskin_tab, "LittleSkin")
        
        # 已保存的账号
        saved_group = QGroupBox("已保存的账号")
        saved_layout = QVBoxLayout()
        self.saved_profiles = QComboBox()
        self.load_saved_profiles()
        self.auto_login_check = QCheckBox("自动登录")
        saved_layout.addWidget(self.saved_profiles)
        saved_layout.addWidget(self.auto_login_check)
        saved_group.setLayout(saved_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.login_button = QPushButton("登录")
        self.delete_button = QPushButton("删除账号")
        self.login_button.clicked.connect(self.login)
        self.delete_button.clicked.connect(self.delete_profile)
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.delete_button)
        
        # 添加所有组件
        layout.addWidget(tab_widget)
        layout.addWidget(saved_group)
        layout.addLayout(button_layout)
        
        # 尝试自动登录
        self.try_auto_login()
        
    def try_auto_login(self):
        """尝试自动登录"""
        auto_login_username = self.auth.get_auto_login()
        if auto_login_username:
            remembered = self.auth.get_remembered_account(auto_login_username)
            if remembered:
                if remembered["type"] == "mojang":
                    self.mojang_email.setText(remembered["username"])
                    self.mojang_password.setText(remembered["password"])
                    self.mojang_remember.setChecked(True)
                    self.login()
                elif remembered["type"] == "offline":
                    self.offline_username.setText(remembered["username"])
                    self.offline_remember.setChecked(True)
                    self.login()
                elif remembered["type"] == "littleskin":
                    self.littleskin_email.setText(remembered["username"])
                    self.littleskin_password.setText(remembered["password"])
                    self.littleskin_remember.setChecked(True)
                    self.login()
    
    def load_saved_profiles(self):
        self.saved_profiles.clear()
        profiles = self.auth.get_saved_profiles()
        for profile in profiles:
            self.saved_profiles.addItem(f"{profile['name']} ({profile['type']})", profile)
    
    def login(self):
        current_tab = self.parent().findChild(QTabWidget).currentIndex()
        
        if current_tab == 0:  # 正版登录
            email = self.mojang_email.text()
            password = self.mojang_password.text()
            if not email or not password:
                QMessageBox.warning(self, "错误", "请输入邮箱和密码！")
                return
            success, result = self.auth.mojang_login(email, password, self.mojang_remember.isChecked())
            
        elif current_tab == 1:  # 离线登录
            username = self.offline_username.text()
            if not username:
                QMessageBox.warning(self, "错误", "请输入用户名！")
                return
            success, result = self.auth.offline_login(username, self.offline_remember.isChecked())
            
        else:  # LittleSkin登录
            email = self.littleskin_email.text()
            password = self.littleskin_password.text()
            if not email or not password:
                QMessageBox.warning(self, "错误", "请输入邮箱和密码！")
                return
            success, result = self.auth.littleskin_login(email, password, self.littleskin_remember.isChecked())
        
        if success:
            self.current_profile = result
            # 设置自动登录
            if self.auto_login_check.isChecked():
                self.auth.set_auto_login(result["name"])
            self.accept()
        else:
            QMessageBox.warning(self, "错误", result)
    
    def delete_profile(self):
        current_text = self.saved_profiles.currentText()
        if not current_text:
            return
            
        username = current_text.split(" (")[0]
        if self.auth.delete_profile(username):
            self.load_saved_profiles()
            QMessageBox.information(self, "成功", "账号已删除！")
        else:
            QMessageBox.warning(self, "错误", "删除账号失败！")

class DownloadThread(QThread):
    progress = pyqtSignal(str, float, float)  # 状态文本, 百分比, 速度
    finished = pyqtSignal(bool, str)
    
    def __init__(self, downloader, version, queue):
        super().__init__()
        self.downloader = downloader
        self.version = version
        self.queue = queue
        self._running = True
    
    def run(self):
        try:
            for task in self.queue:
                if task == 'version':
                    self.progress.emit("正在下载游戏主程序...", 0, 0)
                    self.downloader.download_version(self.version, self.progress_callback)
                elif task == 'assets':
                    self.progress.emit("正在下载资源文件...", 0, 0)
                    self.downloader.download_assets(self.version, self.progress_callback)
            self.finished.emit(True, "下载完成！")
        except Exception as e:
            self.finished.emit(False, f"下载失败：{str(e)}")
    
    def progress_callback(self, percent, speed, current, total):
        text = f"进度: {percent:.2f}%  速度: {speed/1024:.2f} KB/s ({current}/{total}字节)"
        self.progress.emit(text, percent, speed)

class PMCL(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PMCL - Python Minecraft Launcher")
        self.setMinimumSize(800, 600)
        
        # 初始化配置
        self.config = self.load_config()
        
        # 下载队列
        self.download_queue = []
        
        # 当前登录信息
        self.current_profile = None
        
        # 创建主窗口部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # 创建界面元素
        self.create_ui()
        
        # 尝试自动登录
        self.try_auto_login()
    
    def try_auto_login(self):
        """尝试自动登录"""
        dialog = LoginDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.current_profile = dialog.current_profile
            self.login_label.setText(f"已登录: {self.current_profile['name']} ({self.current_profile['type']})")
            self.login_button.setText("切换账号")
    
    def create_ui(self):
        # 登录信息
        login_layout = QHBoxLayout()
        self.login_label = QLabel("未登录")
        self.login_button = QPushButton("登录")
        self.login_button.clicked.connect(self.show_login_dialog)
        login_layout.addWidget(self.login_label)
        login_layout.addWidget(self.login_button)
        
        # 游戏目录选择
        dir_layout = QHBoxLayout()
        self.dir_label = QLabel("游戏目录:")
        self.dir_input = QLineEdit()
        self.dir_input.setText(self.config.get('game_dir', ''))
        self.dir_button = QPushButton("浏览")
        self.dir_button.clicked.connect(self.select_game_dir)
        
        dir_layout.addWidget(self.dir_label)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.dir_button)
        
        # 版本选择
        version_layout = QHBoxLayout()
        self.version_label = QLabel("游戏版本:")
        self.version_combo = QComboBox()
        self.version_combo.addItems(["1.20.1", "1.19.4", "1.18.2", "1.17.1"])
        
        version_layout.addWidget(self.version_label)
        version_layout.addWidget(self.version_combo)
        
        # 下载队列管理
        queue_layout = QHBoxLayout()
        self.version_check = QPushButton("添加主程序到队列")
        self.assets_check = QPushButton("添加资源到队列")
        self.version_check.clicked.connect(lambda: self.add_to_queue('version'))
        self.assets_check.clicked.connect(lambda: self.add_to_queue('assets'))
        queue_layout.addWidget(self.version_check)
        queue_layout.addWidget(self.assets_check)
        
        # 下载按钮
        self.download_button = QPushButton("开始下载队列")
        self.download_button.clicked.connect(self.download_game)
        
        # 暂停/继续按钮
        self.pause_button = QPushButton("暂停下载")
        self.pause_button.clicked.connect(self.pause_or_resume)
        self.is_paused = False
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(True)
        
        # 状态标签
        self.status_label = QLabel("")
        
        # 启动按钮
        self.launch_button = QPushButton("启动游戏")
        self.launch_button.clicked.connect(self.launch_game)
        
        # 添加所有布局
        self.layout.addLayout(login_layout)
        self.layout.addLayout(dir_layout)
        self.layout.addLayout(version_layout)
        self.layout.addLayout(queue_layout)
        self.layout.addWidget(self.download_button)
        self.layout.addWidget(self.pause_button)
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.launch_button)
        self.layout.addStretch()
    
    def show_login_dialog(self):
        dialog = LoginDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.current_profile = dialog.current_profile
            self.login_label.setText(f"已登录: {self.current_profile['name']} ({self.current_profile['type']})")
            self.login_button.setText("切换账号")
    
    def add_to_queue(self, task):
        if task not in self.download_queue:
            self.download_queue.append(task)
            self.status_label.setText(f"已添加到队列: {self.download_queue}")
        else:
            self.status_label.setText(f"任务已在队列: {self.download_queue}")
    
    def select_game_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择Minecraft游戏目录")
        if dir_path:
            self.dir_input.setText(dir_path)
            self.config['game_dir'] = dir_path
            self.save_config()
            
    def load_config(self):
        config_path = os.path.join('PMCL', 'config', 'launcher_config.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_config(self):
        config_path = os.path.join('PMCL', 'config', 'launcher_config.json')
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)
    
    def download_game(self):
        game_dir = self.dir_input.text()
        version = self.version_combo.currentText()
        
        if not game_dir:
            QMessageBox.warning(self, "错误", "请选择游戏目录！")
            return
        if not self.download_queue:
            QMessageBox.warning(self, "错误", "请先添加下载任务到队列！")
            return
        
        self.download_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.status_label.setText("准备下载...")
        self.progress_bar.setValue(0)
        
        self.downloader = MinecraftDownloader(game_dir)
        self.download_thread = DownloadThread(self.downloader, version, self.download_queue)
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.start()
    
    def update_progress(self, message, percent, speed):
        self.status_label.setText(message)
        self.progress_bar.setValue(int(percent))
    
    def download_finished(self, success, message):
        self.download_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.status_label.setText(message)
        self.download_queue.clear()
        
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.warning(self, "错误", message)
    
    def pause_or_resume(self):
        if not hasattr(self, 'downloader'):
            return
        if self.is_paused:
            self.downloader.resume_download()
            self.pause_button.setText("暂停下载")
            self.is_paused = False
        else:
            self.downloader.pause_download()
            self.pause_button.setText("继续下载")
            self.is_paused = True
    
    def launch_game(self):
        if not self.current_profile:
            QMessageBox.warning(self, "错误", "请先登录！")
            return
            
        game_dir = self.dir_input.text()
        version = self.version_combo.currentText()
        
        if not game_dir:
            QMessageBox.warning(self, "错误", "请选择游戏目录！")
            return
            
        jar_path = os.path.join(game_dir, "versions", version, f"{version}.jar")
        if not os.path.exists(jar_path):
            QMessageBox.warning(self, "错误", f"未找到 {jar_path}，请先下载！")
            return
            
        # 构建启动命令
        java_path = "java"  # 假设Java在系统PATH中
        game_args = [
            java_path,
            "-Xmx2G",  # 最大内存
            "-XX:+UnlockExperimentalVMOptions",
            "-XX:+UseG1GC",
            "-XX:G1NewSizePercent=20",
            "-XX:G1ReservePercent=20",
            "-XX:MaxGCPauseMillis=50",
            "-XX:G1HeapRegionSize=32M",
            "-jar", jar_path,
            "--username", self.current_profile["name"],
            "--uuid", self.current_profile["uuid"],
            "--gameDir", game_dir,
            "--assetsDir", os.path.join(game_dir, "assets"),
            "--assetIndex", version
        ]
        
        # 添加认证信息
        if self.current_profile["type"] != "offline":
            game_args.extend([
                "--accessToken", self.current_profile["access_token"]
            ])
        
        try:
            subprocess.Popen(game_args)
            QMessageBox.information(self, "提示", f"已启动Minecraft {version}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"启动失败: {e}")

def main():
    app = QApplication(sys.argv)
    window = PMCL()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 