import sys
import os
import requests
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QPushButton, QComboBox, QLabel,
                           QLineEdit, QMessageBox, QFileDialog, QProgressBar,
                           QDialog, QTabWidget, QFormLayout, QGroupBox,
                           QCheckBox, QSizePolicy)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from auth import MinecraftAuth
import subprocess
from game_launcher import GameLauncher
from auth_ui import LoginDialog, AuthManagerUI
from downloader_ui import DownloadManagerUI
from mod_manager_ui import ModManagerUI
from config_manager import ConfigManager

# 添加PMCL目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 动态获取所有Minecraft版本
def get_all_minecraft_versions():
    # 自动选择最快镜像
    from downloader import MinecraftDownloader
    # 获取 .minecraft 路径
    project_root = os.path.abspath(os.path.dirname(__file__))
    minecraft_dir = os.path.join(project_root, '.minecraft')
    temp_downloader = MinecraftDownloader(minecraft_dir)
    mirror = temp_downloader.get_fastest_mirror()
    print(f"[INFO] 选择的镜像: {mirror['name']} {mirror['manifest']}")
    try:
        resp = requests.get(mirror['manifest'], timeout=10)
        data = resp.json()
        return [v["id"] for v in data["versions"]]
    except Exception as e:
        print("获取版本列表失败：", e)
        return ["1.20.1", "1.19.4", "1.18.2", "1.17.1"]

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
        
        # 初始化配置 (通过 ConfigManager 处理)
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        
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
        
        # 创建界面元素 (先创建UI元素，再初始化管理器，并将UI元素传递给管理器)
        self.create_ui()
        
        # 初始化认证和登录UI管理器
        self.auth_instance = MinecraftAuth()
        self.auth_manager = AuthManagerUI(self.auth_instance, self.login_label, self.login_button, self)
        
        # 初始化下载UI管理器
        self.download_manager = DownloadManagerUI(self.status_label, self.progress_bar, self.download_button, self.pause_button, self.dir_input, self.download_version_combo, self.download_queue, self, self.download_mirror_label)
        
        # 初始化模组管理UI管理器
        # 将此初始化移到 create_ui 之后，因为它需要访问 create_ui 中创建的 UI 元素
        # self.mod_manager = ModManagerUI(self.mod_list, self.search_mod_input, self.add_mod_button, self.delete_mod_button, self.search_mod_button, self)
        
        # 尝试自动登录（通过 AuthManagerUI 处理）
        self.auth_manager.check_initial_login()
    
    def find_or_create_minecraft_dir(self):
        """只查找或创建.minecraft目录，不再创建PMCL文件夹"""
        project_root = os.path.abspath(os.path.dirname(__file__))
        minecraft_dir = os.path.join(project_root, '.minecraft')
        if not os.path.exists(minecraft_dir):
            try:
                os.makedirs(minecraft_dir, exist_ok=True)
                QMessageBox.information(self, "提示", f"已在 {minecraft_dir} 创建新的.minecraft目录")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法创建.minecraft目录: {str(e)}")
        self.config['game_dir'] = minecraft_dir
        self.config_manager.save_config(self.config)
    
    def create_ui(self):
        # 主Tab控件
        self.tabs = QTabWidget()
        self.tab_launch = QWidget()
        self.tab_login = QWidget()
        self.tab_download = QWidget()
        self.tab_settings = QWidget()
        self.tabs.addTab(self.tab_launch, "启动")
        self.tabs.addTab(self.tab_login, "登录")
        self.tabs.addTab(self.tab_download, "下载")
        self.tabs.addTab(self.tab_settings, "设置")
        self.layout.addWidget(self.tabs)

        # 启动Tab
        launch_layout = QVBoxLayout()
        # 本地游戏版本选择
        launch_version_layout = QHBoxLayout()
        self.launch_version_label = QLabel("已下载版本:")
        self.launch_version_combo = QComboBox()
        # 填充本地已下载版本列表将在 PMCL.__init__ 中完成
        launch_version_layout.addWidget(self.launch_version_label)
        launch_version_layout.addWidget(self.launch_version_combo)
        launch_version_layout.addStretch()
        launch_version_group = QGroupBox("选择版本 (本地)")
        launch_version_group.setLayout(launch_version_layout)

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
        # 启动按钮
        self.launch_button = QPushButton("启动游戏")
        # 启动按钮的信号连接将在 __init__ 中使用 self.launch_version_combo
        self.launch_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        launch_layout.addWidget(launch_version_group)
        launch_layout.addWidget(memory_group)
        launch_layout.addWidget(self.launch_button)
        launch_layout.addStretch()
        self.tab_launch.setLayout(launch_layout)

        # 登录Tab
        login_layout = QVBoxLayout()
        login_hlayout = QHBoxLayout()
        self.login_label = QLabel("未登录")
        self.login_button = QPushButton("登录/切换账号")
        # login_button 的信号连接已移至 AuthManagerUI 的 __init__ 方法
        self.login_label.setMinimumWidth(120)
        login_hlayout.addWidget(self.login_label)
        login_hlayout.addWidget(self.login_button)
        login_hlayout.addStretch()
        login_group = QGroupBox("账号管理")
        login_group.setLayout(login_hlayout)
        login_layout.addWidget(login_group)
        login_layout.addStretch()
        self.tab_login.setLayout(login_layout)

        # 下载Tab
        download_layout = QVBoxLayout()
        # 在线游戏版本选择
        download_version_layout = QHBoxLayout()
        self.download_version_label = QLabel("在线版本:")
        self.download_version_combo = QComboBox()
        all_versions = get_all_minecraft_versions()
        self.download_version_combo.addItems(all_versions)
        # 显示当前镜像
        from downloader import MinecraftDownloader
        project_root = os.path.abspath(os.path.dirname(__file__))
        minecraft_dir = os.path.join(project_root, '.minecraft')
        temp_downloader = MinecraftDownloader(minecraft_dir)
        mirror = temp_downloader.get_fastest_mirror()
        self.download_mirror_label = QLabel(f"当前镜像: {mirror['name']}")
        download_version_layout.addWidget(self.download_version_label)
        download_version_layout.addWidget(self.download_version_combo)
        download_version_layout.addWidget(self.download_mirror_label)
        download_version_layout.addStretch()
        download_version_group = QGroupBox("选择版本 (在线)")
        download_version_group.setLayout(download_version_layout)

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

        # 下载按钮
        self.download_button = QPushButton("开始下载队列")
        # download_button 的信号连接已移至 DownloadManagerUI 的 __init__ 方法
        self.download_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        # 暂停/继续按钮
        self.pause_button = QPushButton("暂停下载")
        # pause_button 的信号连接已移至 DownloadManagerUI 的 __init__ 方法
        self.pause_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(True)
        # 状态标签
        self.status_label = QLabel("")
        # 模组管理
        mod_group = QGroupBox("模组管理")
        mod_layout = QVBoxLayout()
        self.mod_list = QComboBox()
        self.mod_list.setMinimumWidth(220)
        # 按钮横向布局
        btn_layout = QHBoxLayout()
        self.add_mod_button = QPushButton("添加本地模组")
        self.delete_mod_button = QPushButton("删除选中模组")
        # 模组按钮的信号连接已移至 ModManagerUI 的 __init__ 方法
        btn_layout.addWidget(self.add_mod_button)
        btn_layout.addSpacing(10)
        btn_layout.addWidget(self.delete_mod_button)
        # 搜索横向布局
        search_layout = QHBoxLayout()
        self.search_mod_input = QLineEdit()
        self.search_mod_input.setPlaceholderText("输入模组名（如 sodium）")
        self.search_mod_input.setMinimumWidth(220)
        self.search_mod_button = QPushButton("在线搜索并下载")
        # 模组搜索按钮的信号连接已移至 ModManagerUI 的 __init__ 方法
        search_layout.addWidget(self.search_mod_input)
        search_layout.addSpacing(10)
        search_layout.addWidget(self.search_mod_button)
        mod_layout.addWidget(self.mod_list)
        mod_layout.addLayout(btn_layout)
        mod_layout.addLayout(search_layout)
        mod_group.setLayout(mod_layout)

        download_layout.addWidget(download_version_group)
        download_layout.addWidget(queue_group)
        download_layout.addWidget(self.download_button)
        download_layout.addWidget(self.pause_button)
        download_layout.addWidget(self.progress_bar)
        download_layout.addWidget(self.status_label)
        download_layout.addWidget(mod_group)
        download_layout.addStretch()
        self.tab_download.setLayout(download_layout)

        # 设置Tab
        settings_layout = QVBoxLayout()
        dir_layout = QHBoxLayout()
        self.dir_label = QLabel("游戏目录:")
        self.dir_input = QLineEdit()
        self.dir_input.setText(self.config.get('game_dir', ''))
        self.dir_button = QPushButton("浏览")
        self.dir_button.clicked.connect(self.select_game_dir)
        self.dir_input.setMinimumWidth(250)
        dir_layout.addWidget(self.dir_label)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.dir_button)
        dir_layout.addStretch()
        dir_group = QGroupBox("游戏目录")
        dir_group.setLayout(dir_layout)
        settings_layout.addWidget(dir_group)
        settings_layout.addStretch()
        self.tab_settings.setLayout(settings_layout)

        # 初始化管理器
        self.auth_instance = MinecraftAuth()
        self.auth_manager = AuthManagerUI(self.auth_instance, self.login_label, self.login_button, self)
        self.download_manager = DownloadManagerUI(self.status_label, self.progress_bar, self.download_button, self.pause_button, self.dir_input, self.download_version_combo, self.download_queue, self, self.download_mirror_label)
        self.mod_manager = ModManagerUI(self.mod_list, self.search_mod_input, self.add_mod_button, self.delete_mod_button, self.search_mod_button, self)

        # 尝试自动登录（通过 AuthManagerUI 处理）
        self.auth_manager.check_initial_login()

        # 刷新本地已下载版本列表
        self.refresh_local_versions()
    
    def refresh_local_versions(self):
        """刷新本地已下载的游戏版本列表"""
        versions_dir = os.path.join(self.config.get('game_dir', ''), 'versions')
        local_versions = []
        if os.path.exists(versions_dir):
            for item in os.listdir(versions_dir):
                version_path = os.path.join(versions_dir, item)
                # 检查是否是版本目录且包含同名jar文件
                if os.path.isdir(version_path) and os.path.exists(os.path.join(version_path, f'{item}.jar')):
                    local_versions.append(item)
        self.launch_version_combo.clear()
        if local_versions:
            self.launch_version_combo.addItems(local_versions)
        else:
            self.launch_version_combo.addItem("未找到本地版本")
            self.launch_button.setEnabled(False) # 如果没有本地版本，禁用启动按钮

    def add_to_queue(self, task):
        # 将任务添加到下载队列的操作委托给DownloadManagerUI
        self.download_manager.add_to_queue(task)
    
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
            self.config_manager.save_config(self.config)
            # 更新本地版本列表
            self.refresh_local_versions()
            
    def on_memory_combo_changed(self, text):
        if text == "自定义":
            self.memory_input.setVisible(True)
        else:
            self.memory_input.setVisible(False)
    
    def launch_game(self):
        launcher = GameLauncher()
        # 使用 self.launch_version_combo 获取本地版本
        version = self.launch_version_combo.currentText()
        if version == "未找到本地版本":
            QMessageBox.warning(self, "错误", "未找到本地版本，无法启动游戏！")
            return
        launcher.launch_game(self.current_profile, self.dir_input.text(), version, self.memory_combo, self.memory_input)

def main():
    app = QApplication(sys.argv)
    window = PMCL()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 