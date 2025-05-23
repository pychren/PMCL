import sys
import os
import json
import requests
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QPushButton, QComboBox, QLabel,
                           QLineEdit, QMessageBox, QFileDialog, QProgressBar,
                           QDialog, QTabWidget, QFormLayout, QGroupBox,
                           QCheckBox, QSizePolicy)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from downloader import MinecraftDownloader
from auth import MinecraftAuth
import subprocess
import winreg
import time

# 添加PMCL目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 动态获取所有Minecraft版本
def get_all_minecraft_versions():
    # 自动选择最快镜像
    from downloader import MinecraftDownloader
    # 临时用一个目录初始化downloader
    temp_downloader = MinecraftDownloader(os.getcwd())
    mirror = temp_downloader.get_fastest_mirror()
    print(f"[INFO] 选择的镜像: {mirror['name']} {mirror['manifest']}")
    try:
        resp = requests.get(mirror['manifest'], timeout=10)
        data = resp.json()
        return [v["id"] for v in data["versions"]]
    except Exception as e:
        print("获取版本列表失败：", e)
        return ["1.20.1", "1.19.4", "1.18.2", "1.17.1"]

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
        # 设置全局QSS美化
        self.setStyleSheet("""
            QWidget {
                background: #f6f8fa;
                font-family: '微软雅黑', 'Microsoft YaHei', Arial, sans-serif;
                font-size: 15px;
            }
            QGroupBox {
                border: 1.5px solid #b0b0b0;
                border-radius: 10px;
                margin-top: 15px;
                background: #fff;
                font-size: 17px;
                font-weight: bold;
                padding: 8px;
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                left: 15px;
                top: 2px;
                color: #4f8cff;
                font-size: 18px;
            }
            QLabel {
                color: #222;
                font-size: 15px;
            }
            QLineEdit, QComboBox {
                border: 1.5px solid #b0b0b0;
                border-radius: 8px;
                padding: 10px 18px;
                font-size: 15px;
                background: #fafdff;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:1 #38e6c5);
                color: #fff;
                border: none;
                border-radius: 10px;
                padding: 12px 32px;
                font-size: 16px;
                font-weight: bold;
                margin: 3px 0;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38e6c5, stop:1 #4f8cff);
                color: #fff;
            }
            QProgressBar {
                border: 1.5px solid #b0b0b0;
                border-radius: 10px;
                text-align: center;
                font-size: 15px;
                background: #e9ecef;
                height: 24px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:1 #38e6c5);
                border-radius: 10px;
            }
            QCheckBox {
                font-size: 15px;
            }
        """)
        
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
        
        # 查找或创建.minecraft目录
        self.find_or_create_minecraft_dir()
        
        # 创建界面元素
        self.create_ui()
        
        # 尝试自动登录
        self.try_auto_login()
    
    def find_or_create_minecraft_dir(self):
        """在项目主目录下查找或创建.minecraft目录"""
        project_root = os.path.abspath(os.path.dirname(__file__))
        minecraft_dir = os.path.join(project_root, '.minecraft')
        if not os.path.exists(minecraft_dir):
            try:
                os.makedirs(minecraft_dir, exist_ok=True)
                QMessageBox.information(self, "提示", f"已在 {minecraft_dir} 创建新的.minecraft目录")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法创建.minecraft目录: {str(e)}")
        self.config['game_dir'] = minecraft_dir
        self.save_config()
    
    def create_ui(self):
        # 登录信息
        login_layout = QHBoxLayout()
        self.login_label = QLabel("未登录")
        self.login_button = QPushButton("登录")
        self.login_button.clicked.connect(self.show_login_dialog)
        login_layout.addWidget(self.login_label)
        login_layout.addWidget(self.login_button)
        login_layout.addStretch()
        login_group = QGroupBox("账号管理")
        login_group.setLayout(login_layout)

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
        dir_layout.addStretch()
        dir_group = QGroupBox("游戏目录")
        dir_group.setLayout(dir_layout)

        # 版本选择
        version_layout = QHBoxLayout()
        self.version_label = QLabel("游戏版本:")
        self.version_combo = QComboBox()
        all_versions = get_all_minecraft_versions()
        self.version_combo.addItems(all_versions)
        # 显示当前镜像
        from downloader import MinecraftDownloader
        temp_downloader = MinecraftDownloader(os.getcwd())
        mirror = temp_downloader.get_fastest_mirror()
        self.mirror_label = QLabel(f"当前镜像: {mirror['name']}")
        version_layout.addWidget(self.version_label)
        version_layout.addWidget(self.version_combo)
        version_layout.addWidget(self.mirror_label)
        version_layout.addStretch()
        version_group = QGroupBox("游戏版本")
        version_group.setLayout(version_layout)

        # 内存管理
        memory_layout = QHBoxLayout()
        self.memory_label = QLabel("最大内存:")
        self.memory_combo = QComboBox()
        self.memory_combo.addItems(["2G", "4G", "8G", "16G", "自定义"])
        self.memory_combo.setCurrentIndex(0)
        self.memory_input = QLineEdit()
        self.memory_input.setPlaceholderText("如 6G 或 4096M")
        self.memory_input.setVisible(False)
        memory_layout.addWidget(self.memory_label)
        memory_layout.addWidget(self.memory_combo)
        memory_layout.addWidget(self.memory_input)
        memory_layout.addStretch()
        self.memory_combo.currentTextChanged.connect(self.on_memory_combo_changed)
        memory_group = QGroupBox("内存管理")
        memory_group.setLayout(memory_layout)

        # 下载队列管理
        queue_layout = QHBoxLayout()
        self.version_check = QPushButton("添加主程序到队列")
        self.assets_check = QPushButton("添加资源到队列")
        self.version_check.clicked.connect(lambda: self.add_to_queue('version'))
        self.assets_check.clicked.connect(lambda: self.add_to_queue('assets'))
        queue_layout.addWidget(self.version_check)
        queue_layout.addWidget(self.assets_check)
        queue_layout.addStretch()
        queue_group = QGroupBox("下载管理")
        queue_group.setLayout(queue_layout)

        # 模组管理
        mod_group = QGroupBox("模组管理")
        mod_layout = QVBoxLayout()
        self.mod_list = QComboBox()
        self.refresh_mod_list()
        self.mod_list.setMinimumWidth(220)

        # 按钮横向布局
        btn_layout = QHBoxLayout()
        self.add_mod_button = QPushButton("添加本地模组")
        self.delete_mod_button = QPushButton("删除选中模组")
        btn_layout.addWidget(self.add_mod_button)
        btn_layout.addSpacing(10)
        btn_layout.addWidget(self.delete_mod_button)

        # 搜索横向布局
        search_layout = QHBoxLayout()
        self.search_mod_input = QLineEdit()
        self.search_mod_input.setPlaceholderText("输入模组名（如 sodium）")
        self.search_mod_input.setMinimumWidth(220)
        self.search_mod_button = QPushButton("在线搜索并下载")
        search_layout.addWidget(self.search_mod_input)
        search_layout.addSpacing(10)
        search_layout.addWidget(self.search_mod_button)

        self.add_mod_button.clicked.connect(self.add_local_mod)
        self.delete_mod_button.clicked.connect(self.delete_selected_mod)
        self.search_mod_button.clicked.connect(self.download_online_mod)

        mod_layout.addWidget(self.mod_list)
        mod_layout.addLayout(btn_layout)
        mod_layout.addLayout(search_layout)
        mod_group.setLayout(mod_layout)

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

        # 主布局
        self.layout.addWidget(login_group)
        self.layout.addWidget(dir_group)
        self.layout.addWidget(version_group)
        self.layout.addWidget(memory_group)
        self.layout.addWidget(queue_group)
        self.layout.addWidget(mod_group)
        self.layout.addWidget(self.download_button)
        self.layout.addWidget(self.pause_button)
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.launch_button)
        self.layout.addStretch()
        
        # 控件宽度优化
        self.mod_list.setMinimumWidth(220)
        self.search_mod_input.setMinimumWidth(220)
        self.version_combo.setMinimumWidth(120)
        self.dir_input.setMinimumWidth(250)
        self.memory_input.setMinimumWidth(100)
        self.login_label.setMinimumWidth(120)
        # 按钮自适应扩展
        self.add_mod_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.delete_mod_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.download_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.pause_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.launch_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    
    def show_login_dialog(self):
        dialog = LoginDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.current_profile = dialog.current_profile
            self.login_label.setText(f"已登录: {self.current_profile['name']} ({self.current_profile['type']})")
            self.login_button.setText("切换账号")
            self.save_login_to_registry(self.current_profile)
    
    def add_to_queue(self, task):
        if task not in self.download_queue:
            self.download_queue.append(task)
            self.status_label.setText(f"已添加到队列: {self.download_queue}")
        else:
            self.status_label.setText(f"任务已在队列: {self.download_queue}")
    
    def select_game_dir(self):
        project_root = os.path.abspath(os.path.dirname(__file__))
        default_minecraft_dir = os.path.join(project_root, '.minecraft')
        dir_path = QFileDialog.getExistingDirectory(self, "选择Minecraft游戏目录", default_minecraft_dir)
        if dir_path:
            # 只允许选择主目录下的.minecraft
            if os.path.abspath(dir_path) != os.path.abspath(default_minecraft_dir):
                QMessageBox.warning(self, "错误", f"请选择本项目主目录下的 .minecraft 文件夹！\n当前选择: {dir_path}")
                return
            self.dir_input.setText(dir_path)
            self.config['game_dir'] = dir_path
            self.save_config()
            
    def load_config(self):
        config = {}
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
        except Exception as e:
            print("读取注册表配置失败：", e)
        return config

    def save_config(self):
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\\PMCL\\Config")
            for k, v in self.config.items():
                winreg.SetValueEx(key, k, 0, winreg.REG_SZ, str(v))
            winreg.CloseKey(key)
        except Exception as e:
            print("写入注册表配置失败：", e)
    
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
    
    def on_memory_combo_changed(self, text):
        if text == "自定义":
            self.memory_input.setVisible(True)
        else:
            self.memory_input.setVisible(False)
    
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
        
        # 获取内存参数
        memory = self.memory_combo.currentText()
        if memory == "自定义":
            memory = self.memory_input.text().strip()
            if not memory:
                QMessageBox.warning(self, "错误", "请输入自定义内存大小，如 6G 或 4096M")
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

    def try_auto_login(self):
        """尝试自动登录"""
        dialog = LoginDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.current_profile = dialog.current_profile
            self.login_label.setText(f"已登录: {self.current_profile['name']} ({self.current_profile['type']})")
            self.login_button.setText("切换账号")

    def refresh_mod_list(self):
        mods_dir = os.path.join(self.config.get('game_dir', ''), 'mods')
        if not os.path.exists(mods_dir):
            os.makedirs(mods_dir, exist_ok=True)
        self.mod_list.clear()
        for f in os.listdir(mods_dir):
            if f.endswith('.jar'):
                self.mod_list.addItem(f)

    def add_local_mod(self):
        mods_dir = os.path.join(self.config.get('game_dir', ''), 'mods')
        file_path, _ = QFileDialog.getOpenFileName(self, "选择模组文件", "", "Mod 文件 (*.jar)")
        if file_path:
            import shutil
            shutil.copy(file_path, mods_dir)
            self.refresh_mod_list()
            QMessageBox.information(self, "成功", "模组已添加！")

    def delete_selected_mod(self):
        mods_dir = os.path.join(self.config.get('game_dir', ''), 'mods')
        mod_name = self.mod_list.currentText()
        if mod_name:
            os.remove(os.path.join(mods_dir, mod_name))
            self.refresh_mod_list()
            QMessageBox.information(self, "成功", "模组已删除！")

    def download_online_mod(self):
        mod_name = self.search_mod_input.text().strip()
        if not mod_name:
            QMessageBox.warning(self, "错误", "请输入模组名！")
            return
        # 使用 Modrinth API 搜索
        url = f"https://api.modrinth.com/v2/search?query={mod_name}&facets=[[\"project_type:mod\"]]"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            if not data['hits']:
                QMessageBox.warning(self, "未找到", "未找到相关模组")
                return
            # 取第一个结果
            mod = data['hits'][0]
            project_id = mod['project_id']
            # 获取最新版本文件
            files_url = f"https://api.modrinth.com/v2/project/{project_id}/version"
            files_resp = requests.get(files_url, timeout=10)
            files = files_resp.json()
            if not files:
                QMessageBox.warning(self, "未找到", "未找到模组文件")
                return
            # 取第一个文件的第一个下载链接
            file_url = files[0]['files'][0]['url']
            mods_dir = os.path.join(self.config.get('game_dir', ''), 'mods')
            if not os.path.exists(mods_dir):
                os.makedirs(mods_dir, exist_ok=True)
            file_name = files[0]['files'][0]['filename']
            file_path = os.path.join(mods_dir, file_name)
            with requests.get(file_url, stream=True) as r:
                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            self.refresh_mod_list()
            QMessageBox.information(self, "成功", f"模组 {file_name} 已下载！")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"下载失败: {e}")

    def save_login_to_registry(self, profile):
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\\PMCL\\LastLogin")
            winreg.SetValueEx(key, "username", 0, winreg.REG_SZ, profile.get("name", ""))
            winreg.SetValueEx(key, "uuid", 0, winreg.REG_SZ, profile.get("uuid", ""))
            winreg.SetValueEx(key, "type", 0, winreg.REG_SZ, profile.get("type", ""))
            winreg.SetValueEx(key, "timestamp", 0, winreg.REG_SZ, str(int(time.time())))
            winreg.CloseKey(key)
        except Exception as e:
            print("写入注册表失败：", e)

def main():
    app = QApplication(sys.argv)
    window = PMCL()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 