from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel, QLineEdit, QMessageBox, QTabWidget, QFormLayout, QGroupBox, QCheckBox, QWidget)
from auth import MinecraftAuth
import winreg
import time

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

class AuthManagerUI:
    def __init__(self, auth_instance, login_label, login_button, main_window):
        self.auth = auth_instance
        self.login_label = login_label
        self.login_button = login_button
        self.main_window = main_window # 引用主窗口以便调用其方法和访问成员
        self.login_button.clicked.connect(self.show_login_dialog) # 将信号连接移动到这里

    def check_initial_login(self):
        """在启动时检查并尝试自动登录"""
        auto_login_username = self.auth.get_auto_login()
        if auto_login_username:
            remembered = self.auth.get_remembered_account(auto_login_username)
            if remembered:
                if remembered["type"] == "mojang":
                    success, result = self.auth.mojang_login(remembered["username"], remembered["password"])
                elif remembered["type"] == "offline":
                    success, result = self.auth.offline_login(remembered["username"])
                elif remembered["type"] == "littleskin":
                    success, result = self.auth.littleskin_login(remembered["username"], remembered["password"])

                if success:
                    self.main_window.current_profile = result
                    self.update_login_status()
                    print(f"[INFO] 自动登录成功: {result['name']}")
                else:
                    print(f"[WARN] 自动登录失败: {result}")
                    # 自动登录失败，清除自动登录设置
                    self.auth.set_auto_login(None)

    def show_login_dialog(self):
        dialog = LoginDialog(self.main_window)
        if dialog.exec_() == QDialog.Accepted:
            self.main_window.current_profile = dialog.current_profile
            self.update_login_status()
            self.save_login_to_registry(self.main_window.current_profile)

    def update_login_status(self):
        if self.main_window.current_profile:
            self.login_label.setText(f"已登录: {self.main_window.current_profile['name']} ({self.main_window.current_profile['type']})")
            self.login_button.setText("切换账号")
        else:
            self.login_label.setText("未登录")
            self.login_button.setText("登录/切换账号")

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