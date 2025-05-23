import os
import shutil
import requests
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QComboBox

class ModManagerUI:
    def __init__(self, mod_list, search_mod_input, add_mod_button, delete_mod_button, search_mod_button, main_window):
        self.mod_list = mod_list
        self.search_mod_input = search_mod_input
        self.add_mod_button = add_mod_button
        self.delete_mod_button = delete_mod_button
        self.search_mod_button = search_mod_button
        self.main_window = main_window # 引用主窗口以便调用其方法和访问成员，以及访问config

        # 连接信号
        self.add_mod_button.clicked.connect(self.add_local_mod)
        self.delete_mod_button.clicked.connect(self.delete_selected_mod)
        self.search_mod_button.clicked.connect(self.download_online_mod)

    def refresh_mod_list(self):
        mods_dir = os.path.join(self.main_window.config.get('game_dir', ''), 'mods')
        if not os.path.exists(mods_dir):
            os.makedirs(mods_dir, exist_ok=True)
        self.mod_list.clear()
        for f in os.listdir(mods_dir):
            if f.endswith('.jar'):
                self.mod_list.addItem(f)

    def add_local_mod(self):
        mods_dir = os.path.join(self.main_window.config.get('game_dir', ''), 'mods')
        file_path, _ = QFileDialog.getOpenFileName(self.main_window, "选择模组文件", "", "Mod 文件 (*.jar)")
        if file_path:
            shutil.copy(file_path, mods_dir)
            self.refresh_mod_list()
            QMessageBox.information(self.main_window, "成功", "模组已添加！")

    def delete_selected_mod(self):
        mods_dir = os.path.join(self.main_window.config.get('game_dir', ''), 'mods')
        mod_name = self.mod_list.currentText()
        if mod_name:
            os.remove(os.path.join(mods_dir, mod_name))
            self.refresh_mod_list()
            QMessageBox.information(self.main_window, "成功", "模组已删除！")

    def download_online_mod(self):
        mod_name = self.search_mod_input.text().strip()
        if not mod_name:
            QMessageBox.warning(self.main_window, "错误", "请输入模组名！")
            return
        # 使用 Modrinth API 搜索
        url = f"https://api.modrinth.com/v2/search?query={mod_name}&facets=[[\"project_type:mod\"]]"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            if not data['hits']:
                QMessageBox.warning(self.main_window, "未找到", "未找到相关模组")
                return
            # 取第一个结果
            mod = data['hits'][0]
            project_id = mod['project_id']
            # 获取最新版本文件
            files_url = f"https://api.modrinth.com/v2/project/{project_id}/version"
            files_resp = requests.get(files_url, timeout=10)
            files = files_resp.json()
            if not files:
                QMessageBox.warning(self.main_window, "未找到", "未找到模组文件")
                return
            # 取第一个文件的第一个下载链接
            file_url = files[0]['files'][0]['url']
            mods_dir = os.path.join(self.main_window.config.get('game_dir', ''), 'mods')
            if not os.path.exists(mods_dir):
                os.makedirs(mods_dir, exist_ok=True)
            file_name = files[0]['files'][0]['filename']
            file_path = os.path.join(mods_dir, file_name)
            with requests.get(file_url, stream=True) as r:
                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            self.refresh_mod_list()
            QMessageBox.information(self.main_window, "成功", f"模组 {file_name} 已下载！")
        except Exception as e:
            QMessageBox.warning(self.main_window, "错误", f"下载失败: {e}") 