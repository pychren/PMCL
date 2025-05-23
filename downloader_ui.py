from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox # 需要QMessageBox来显示下载完成/失败消息
from downloader import MinecraftDownloader # 需要MinecraftDownloader类

class DownloadThread(QThread):
    progress = pyqtSignal(str, float, float)  # 状态文本, 百分比, 速度
    finished = pyqtSignal(bool, str)
    
    def __init__(self, downloader, version, queue):
        super().__init__()
        self.downloader = downloader
        self.version = version
        self.queue = queue
        self._running = True # 这个变量在原代码中没有被使用，先保留
    
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

class DownloadManagerUI:
    def __init__(self, status_label, progress_bar, download_button, pause_button, dir_input, version_combo, download_queue, main_window):
        self.status_label = status_label
        self.progress_bar = progress_bar
        self.download_button = download_button
        self.pause_button = pause_button
        self.dir_input = dir_input
        self.version_combo = version_combo
        self.download_queue = download_queue
        self.main_window = main_window # 引用主窗口以便调用其方法和访问成员
        self.is_paused = False # 添加is_paused属性

        # 连接信号
        self.download_button.clicked.connect(self.download_game)
        self.pause_button.clicked.connect(self.pause_or_resume)

    def add_to_queue(self, task):
        if task not in self.download_queue:
            self.download_queue.append(task)
            self.status_label.setText(f"已添加到队列: {self.download_queue}")
        else:
            self.status_label.setText(f"任务已在队列: {self.download_queue}")

    def download_game(self):
        game_dir = self.dir_input.text()
        version = self.version_combo.currentText()

        if not game_dir:
            QMessageBox.warning(self.main_window, "错误", "请选择游戏目录！")
            return
        if not self.download_queue:
            QMessageBox.warning(self.main_window, "错误", "请先添加下载任务到队列！")
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
            QMessageBox.information(self.main_window, "成功", message)
        else:
            QMessageBox.warning(self.main_window, "错误", message)

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