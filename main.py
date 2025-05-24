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
from jdk_find import find_java_executables, recursive_java_search

# 仅在win32平台导入winreg
if sys.platform == "win32":
    import winreg

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
        
        # 创建界面元素 (先创建UI元素)
        self.create_ui()
        
        # 管理器初始化和信号连接将在 create_ui 方法中完成
        # # 初始化认证和登录UI管理器
        # self.auth_instance = MinecraftAuth()
        # self.auth_manager = AuthManagerUI(self.auth_instance, self.login_label, self.login_button, self)
        
        # # 初始化下载UI管理器
        # self.download_manager = DownloadManagerUI(self.status_label, self.progress_bar, self.download_button, self.pause_button, self.dir_input, self.download_version_combo, self.download_queue, self, self.download_mirror_label)
        
        # # 初始化模组管理UI管理器
        # self.mod_manager = ModManagerUI(self.mod_list, self.search_mod_input, self.add_mod_button, self.delete_mod_button, self.search_mod_button, self)
        
        # # 尝试自动登录（通过 AuthManagerUI 处理）
        # self.auth_manager.check_initial_login() # 自动登录也移到 create_ui 中，在管理器初始化后调用
        
        # 刷新本地已下载版本列表
        # self.refresh_local_versions() # 刷新本地版本列表也移到 create_ui 中，在管理器初始化后调用
    
    def get_version_game_dir(self, version):
        """根据版本和配置获取版本隔离的游戏目录，并确保目录存在"""
        versions_base_dir = self.config.get('versions_base_dir')
        if not versions_base_dir:
            # Fallback to default if not set in config (should not happen with default config)
            project_root = os.path.abspath(os.path.dirname(__file__))
            versions_base_dir = os.path.join(os.path.dirname(project_root), 'versions_isolated')

        version_game_dir = os.path.join(versions_base_dir, version)
        os.makedirs(version_game_dir, exist_ok=True)
        return version_game_dir

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
        # 填充本地已下载版本列表将在 create_ui 末尾完成
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

        # Mirror source selection
        mirror_layout = QHBoxLayout()
        self.mirror_label = QLabel("选择镜像源:")
        self.mirror_combo = QComboBox()
        self.mirror_combo.addItems([
            'https://bmclapi2.bangbang93.com/',
            'https://download.mcbbs.net/',
            '自定义'
        ])
        self.mirror_input = QLineEdit()
        self.mirror_input.setPlaceholderText("输入自定义镜像源 URL")
        self.mirror_input.setVisible(False) # Initially hidden

        mirror_layout.addWidget(self.mirror_label)
        mirror_layout.addWidget(self.mirror_combo)
        mirror_layout.addWidget(self.mirror_input)
        mirror_layout.addStretch()

        # Connect signal for mirror combo
        self.mirror_combo.currentTextChanged.connect(self.on_mirror_combo_changed)

        # Download buttons
        add_version_button = QPushButton("添加版本下载")
        add_assets_button = QPushButton("添加资源下载")

        # Add download/pause buttons and progress bar back
        self.download_button = QPushButton("开始下载队列")
        self.download_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.pause_button = QPushButton("暂停下载")
        self.pause_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(True)

        # Download queue
        self.status_label = QLabel("等待任务...")
        download_layout.addLayout(download_version_layout)
        download_layout.addLayout(mirror_layout) # Add mirror selection layout
        download_layout.addWidget(add_version_button)
        download_layout.addWidget(add_assets_button)
        download_layout.addWidget(self.status_label)
        # Add download/pause buttons and progress bar to the layout
        download_layout.addWidget(self.download_button)
        download_layout.addWidget(self.pause_button)
        download_layout.addWidget(self.progress_bar)

        # Add mod management UI elements before initializing ModManagerUI
        mod_group = QGroupBox("模组管理")
        mod_layout = QVBoxLayout()
        self.mod_list = QComboBox()
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
        self.search_mod_input.setPlaceholderText("输入模组名（如 sodium")
        self.search_mod_input.setMinimumWidth(220)
        self.search_mod_button = QPushButton("在线搜索并下载")
        search_layout.addWidget(self.search_mod_input)
        search_layout.addSpacing(10)
        search_layout.addWidget(self.search_mod_button)
        mod_layout.addWidget(self.mod_list)
        mod_layout.addLayout(btn_layout)
        mod_layout.addLayout(search_layout)
        mod_group.setLayout(mod_layout)

        # Add mod group to download tab layout
        download_layout.addWidget(mod_group)

        # Set the layout for the download tab
        self.tab_download.setLayout(download_layout)

        # 设置Tab
        settings_layout = QVBoxLayout()
        dir_layout = QHBoxLayout()
        self.dir_label = QLabel("版本隔离基础目录:")
        self.dir_input = QLineEdit()
        self.dir_input.setText(self.config.get('versions_base_dir', ''))
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

        # Java 设置
        java_layout = QHBoxLayout()
        self.java_label = QLabel("Java 可执行文件:")
        self.java_combo = QComboBox()
        self.java_combo.setMinimumWidth(300)
        java_layout.addWidget(self.java_label)
        java_layout.addWidget(self.java_combo)
        java_layout.addStretch()
        java_group = QGroupBox("Java 设置")
        java_group.setLayout(java_layout)
        settings_layout.addWidget(java_group)

        # 添加搜索Java目录按钮
        search_java_dir_layout = QHBoxLayout()
        self.search_java_dir_button = QPushButton("浏览并搜索Java目录")
        search_java_dir_layout.addWidget(self.search_java_dir_button)
        search_java_dir_layout.addStretch()
        settings_layout.addLayout(search_java_dir_layout)

        settings_layout.addStretch()
        self.tab_settings.setLayout(settings_layout)

        # 连接搜索Java目录按钮信号
        self.search_java_dir_button.clicked.connect(self.browse_and_search_java)

        # 连接Java下拉框信号，保存选定的路径到注册表
        self.java_combo.currentIndexChanged.connect(self.save_selected_java_path)

        # 初始化管理器
        self.auth_instance = MinecraftAuth()
        self.auth_manager = AuthManagerUI(self.auth_instance, self.login_label, self.login_button, self)
        self.download_manager = DownloadManagerUI(self.status_label, self.progress_bar, self.download_button, self.pause_button, self.dir_input, self.download_version_combo, self.download_queue, self, self.download_mirror_label, self.config_manager)
        self.mod_manager = ModManagerUI(self.mod_list, self.search_mod_input, self.add_mod_button, self.delete_mod_button, self.search_mod_button, self)

        # 连接信号
        self.launch_button.clicked.connect(self.launch_game)
        # download_button 和 pause_button 的信号连接已移至 DownloadManagerUI 的 __init__ 方法
        # 模组按钮的信号连接已移至 ModManagerUI 的 __init__ 方法
        # login_button 的信号连接已移至 AuthManagerUI 的 __init__ 方法

        # 尝试自动登录（通过 AuthManagerUI 处理）
        self.auth_manager.check_initial_login()

        # 刷新本地已下载版本列表
        self.refresh_local_versions()

        # 查找Java可执行文件并填充到下拉框
        self.populate_java_combo()

        # Load mirror source from config and set the combo box
        initial_config = self.config_manager.load_config()
        saved_mirror = initial_config.get('mirror_source', 'https://bmclapi2.bangbang93.com/')
        index = self.mirror_combo.findText(saved_mirror)
        if index != -1:
            self.mirror_combo.setCurrentIndex(index)
        else:
            self.mirror_combo.setCurrentText('自定义')
            self.mirror_input.setText(saved_mirror)
            self.mirror_input.setVisible(True)
    
    def refresh_local_versions(self):
        """刷新本地已下载的游戏版本列表"""
        # Get the versions base directory from config
        versions_base_dir = self.config.get('versions_base_dir')
        if not versions_base_dir:
             # Fallback to default if not set in config
             project_root = os.path.abspath(os.path.dirname(__file__))
             versions_base_dir = os.path.join(os.path.dirname(project_root), 'versions_isolated')

        local_versions = []
        if os.path.exists(versions_base_dir):
            for item in os.listdir(versions_base_dir):
                # Check if the item is a directory and contains a versions folder
                version_specific_dir = os.path.join(versions_base_dir, item)
                versions_dir = os.path.join(version_specific_dir, 'versions')
                if os.path.isdir(version_specific_dir) and os.path.exists(versions_dir):
                    # Check if there's a version jar file inside the version-specific versions directory
                    version_jar_path = os.path.join(versions_dir, item, f'{item}.jar')
                    if os.path.exists(version_jar_path):
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
        """选择版本隔离的基础目录"""
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.DirectoryOnly)
        if dialog.exec_():
            selected_dir = dialog.selectedFiles()[0]
            self.dir_input.setText(selected_dir)
            # Save selected directory to config
            config = self.config_manager.load_config() # Get current config
            config['versions_base_dir'] = selected_dir # Save the base directory
            self.config_manager.save_config(config)
            # Refresh the local versions list after changing the base directory
            self.refresh_local_versions()

    def on_memory_combo_changed(self, text):
        if text == "自定义":
            self.memory_input.setVisible(True)
        else:
            self.memory_input.setVisible(False)
    
    def populate_java_combo(self):
        """查找Java可执行文件并填充到下拉框"""
        java_installations = find_java_executables() # 调用导入的函数
        self.java_paths_map = {} # 存储名称和路径的映射
        print("Populating Java combo box...")
        print(f"Found Java installations: {java_installations}")

        # 断开信号，避免在填充时触发save_selected_java_path
        if self.java_combo.signalsBlocked():
            was_blocked = True
        else:
            self.java_combo.blockSignals(True)
            was_blocked = False

        try:
            if java_installations:
                for install in java_installations:
                    self.java_combo.addItem(install['name'])
                    self.java_paths_map[install['name']] = install['path']
                print(f"Populated java_paths_map: {self.java_paths_map}")
            else:
                self.java_combo.addItem("未找到Java，请检查安装或环境变量")
                self.java_paths_map["未找到Java，请检查安装或环境变量"] = ""
                print("No Java installations found.")
                # 可能需要禁用启动按钮或显示警告

            # 加载并选择之前保存的Java路径
            print("Attempting to load saved Java path...")
            self.load_saved_java_path()
            print("Finished loading saved Java path.")
        finally:
            # 重新连接信号
            if not was_blocked:
                self.java_combo.blockSignals(False)

    def save_selected_java_path(self):
        """将当前选定的Java路径保存到配置"""
        selected_name = self.java_combo.currentText()
        # Get the actual path from the map
        selected_path = self.java_paths_map.get(selected_name, "")
        # Save selected Java path to config
        config = self.config_manager.load_config()
        config['java_path'] = selected_path
        self.config_manager.save_config(config)

    def load_saved_java_path(self):
        """从配置加载保存的Java路径并选择"""
        # Load saved Java path from config
        config = self.config_manager.load_config()
        saved_java_path = config.get('java_path')
        if saved_java_path:
            # Find the index of the saved path in the java_paths_map values
            saved_index = -1
            for i in range(self.java_combo.count()):
                item_text = self.java_combo.itemText(i)
                item_path = self.java_paths_map.get(item_text)
                if item_path and os.path.normpath(item_path).lower() == os.path.normpath(saved_java_path).lower():
                    saved_index = i
                    break

            if saved_index != -1:
                self.java_combo.setCurrentIndex(saved_index)
            elif os.path.exists(saved_java_path): # If the saved path exists but wasn't in the initial list, add it
                 item_name = f"Saved: {saved_java_path}"
                 if item_name not in self.java_paths_map:
                      self.java_combo.addItem(item_name)
                      self.java_paths_map[item_name] = saved_java_path
                      index = self.java_combo.findText(item_name)
                      if index != -1:
                           self.java_combo.setCurrentIndex(index)
        # Load saved memory setting from config
        saved_memory = config.get('max_memory')
        if saved_memory:
            index = self.memory_combo.findText(saved_memory)
            if index != -1:
                self.memory_combo.setCurrentIndex(index)
                if saved_memory == '自定义':
                    custom_memory = config.get('custom_memory', '')
                    self.memory_input.setText(custom_memory)
                    self.memory_input.setVisible(True)
            elif saved_memory:
                 # Handle case where saved_memory is a custom value not in the combo
                 self.memory_combo.setCurrentText('自定义')
                 self.memory_input.setText(saved_memory)
                 self.memory_input.setVisible(True)

    def launch_game(self):
        # 启动游戏逻辑将委托给GameLauncher
        selected_version = self.launch_version_combo.currentText()
        # Get the version-specific game directory
        game_dir = self.get_version_game_dir(selected_version)
        java_path = self.java_combo.currentText()
        # Get memory setting
        memory_setting = self.memory_combo.currentText()
        if memory_setting == '自定义':
            max_memory = self.memory_input.text()
        else:
            max_memory = memory_setting

        if not selected_version:
            QMessageBox.warning(self, "错误", "未选择有效的游戏版本！")
            return
        if java_path == "未找到Java，请检查安装或环境变量":
            QMessageBox.warning(self, "错误", "未选择有效的Java可执行文件！")
            return

        # Before launching, save the selected Java path and memory to config
        self.save_selected_java_path() # Use existing method to save java path
        # Save memory setting to config
        config = self.config_manager.load_config()
        config['max_memory'] = memory_setting
        if memory_setting == '自定义':
            config['custom_memory'] = max_memory # Save custom value if applicable
        else:
            if 'custom_memory' in config:
                del config['custom_memory'] # Remove custom value if not using custom
        self.config_manager.save_config(config)

        # Now, launch the game using GameLauncher
        self.game_launcher = GameLauncher(game_dir)
        self.game_launcher.launch_game(selected_version, java_path, self.current_profile, max_memory) # Pass max_memory

    def browse_and_search_java(self):
        """让用户选择目录并递归搜索Java可执行文件"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择搜索Java的目录")
        if dir_path:
            found_installations = recursive_java_search(dir_path)
            if found_installations:
                current_items = [self.java_combo.itemText(i) for i in range(self.java_combo.count())]
                for install in found_installations:
                    if install['name'] not in current_items and install['path'] not in self.java_paths_map.values():
                        self.java_combo.addItem(install['name'])
                        self.java_paths_map[install['name']] = install['path']
                QMessageBox.information(self, "搜索完成", f"在 {dir_path} 中找到 {len(found_installations)} 个Java可执行文件。")
            else:
                QMessageBox.information(self, "搜索完成", f"在 {dir_path} 中未找到Java可执行文件。")

    def on_mirror_combo_changed(self, text):
        if text == '自定义':
            self.mirror_input.setVisible(True)
            # Load custom mirror from config if exists
            config = self.config_manager.load_config()
            saved_mirror = config.get('mirror_source', '')
            if saved_mirror and saved_mirror not in ['https://bmclapi2.bangbang93.com/', 'https://download.mcbbs.net/']:
                self.mirror_input.setText(saved_mirror)
            else:
                self.mirror_input.clear()
        else:
            self.mirror_input.setVisible(False)
            # Save selected mirror to config
            config = self.config_manager.load_config()
            config['mirror_source'] = text
            self.config_manager.save_config(config)
            # Update the displayed current mirror label
            self.download_mirror_label.setText(f"当前镜像: {text}")

def main():
    app = QApplication(sys.argv)
    window = PMCL()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 