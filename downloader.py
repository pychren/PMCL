import os
import json
import requests
import hashlib
import time
from urllib.parse import urljoin
from threading import Event

MIRROR_LIST = [
    {
        "name": "BMCLAPI",
        "manifest": "https://bmclapi2.bangbang93.com/mc/game/version_manifest.json",
        "base": "https://bmclapi2.bangbang93.com/"
    },
    {
        "name": "Mcbbs",
        "manifest": "https://download.mcbbs.net/mc/game/version_manifest.json",
        "base": "https://download.mcbbs.net/"
    },
    {
        "name": "Mojang",
        "manifest": "https://launchermeta.mojang.com/mc/game/version_manifest.json",
        "base": "https://launchermeta.mojang.com/"
    }
]

class MinecraftDownloader:
    def __init__(self, game_dir):
        self.game_dir = game_dir
        self.versions_dir = os.path.join(game_dir, "versions")
        self.libraries_dir = os.path.join(game_dir, "libraries")
        self.assets_dir = os.path.join(game_dir, "assets")
        self.pause_event = Event()
        self.pause_event.set()  # 默认不暂停
        self.current_mirror = self.select_fastest_mirror()
        self.version_manifest_url = self.current_mirror["manifest"]
        
        # 创建必要的目录
        for directory in [self.versions_dir, self.libraries_dir, self.assets_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def select_fastest_mirror(self):
        best = None
        best_time = float('inf')
        for mirror in MIRROR_LIST:
            try:
                start = time.time()
                resp = requests.get(mirror["manifest"], timeout=3)
                elapsed = time.time() - start
                if resp.status_code == 200 and elapsed < best_time:
                    best = mirror
                    best_time = elapsed
            except Exception as e:
                continue
        return best if best else MIRROR_LIST[0]

    def get_fastest_mirror(self):
        return self.current_mirror

    def get_version_manifest(self):
        """获取版本清单"""
        response = requests.get(self.version_manifest_url)
        return response.json()
    
    def get_version_info(self, version):
        """获取特定版本的详细信息"""
        manifest = self.get_version_manifest()
        for v in manifest["versions"]:
            if v["id"] == version:
                response = requests.get(v["url"])
                return response.json()
        return None
    
    def download_file(self, url, target_path, progress_callback=None):
        """下载文件到指定路径"""
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        start_time = time.time()
        
        with open(target_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                self.pause_event.wait()  # 检查是否需要暂停
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    if progress_callback and total_size > 0:
                        elapsed_time = time.time() - start_time
                        speed = downloaded_size / elapsed_time if elapsed_time > 0 else 0
                        progress = (downloaded_size / total_size) * 100
                        progress_callback(progress, speed, downloaded_size, total_size)
        
        return True
    
    def pause_download(self):
        """暂停下载"""
        self.pause_event.clear()
    
    def resume_download(self):
        """继续下载"""
        self.pause_event.set()
    
    def verify_file(self, file_path, expected_hash):
        """验证文件完整性"""
        if not os.path.exists(file_path):
            return False
        
        sha1 = hashlib.sha1()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha1.update(chunk)
        return sha1.hexdigest() == expected_hash
    
    def download_version(self, version, progress_callback=None):
        """下载指定版本的游戏文件"""
        version_info = self.get_version_info(version)
        if not version_info:
            raise Exception(f"找不到版本 {version} 的信息")
        
        # 下载客户端
        client_path = os.path.join(self.versions_dir, version, f"{version}.jar")
        if not os.path.exists(client_path):
            self.download_file(version_info["downloads"]["client"]["url"], client_path, progress_callback)
        
        # 下载资源文件
        assets_index = version_info["assetIndex"]
        assets_index_path = os.path.join(self.assets_dir, "indexes", f"{assets_index['id']}.json")
        if not os.path.exists(assets_index_path):
            self.download_file(assets_index["url"], assets_index_path, progress_callback)
        
        # 下载库文件
        libraries = version_info["libraries"]
        total_libraries = len(libraries)
        for i, library in enumerate(libraries):
            if "downloads" not in library:
                continue
                
            artifact = library["downloads"].get("artifact")
            if artifact:
                path = os.path.join(self.libraries_dir, artifact["path"])
                if not os.path.exists(path):
                    self.download_file(artifact["url"], path, progress_callback)
        
        return True
    
    def download_assets(self, version, progress_callback=None):
        """下载资源文件"""
        version_info = self.get_version_info(version)
        if not version_info:
            raise Exception(f"找不到版本 {version} 的信息")
        
        assets_index = version_info["assetIndex"]
        assets_index_path = os.path.join(self.assets_dir, "indexes", f"{assets_index['id']}.json")
        
        with open(assets_index_path, 'r') as f:
            assets_data = json.load(f)
        
        total_assets = len(assets_data["objects"])
        downloaded_assets = 0
        
        for asset_id, asset_info in assets_data["objects"].items():
            hash = asset_info["hash"]
            path = os.path.join(self.assets_dir, "objects", hash[:2], hash)
            
            if not os.path.exists(path):
                url = f"https://resources.download.minecraft.net/{hash[:2]}/{hash}"
                self.download_file(url, path, progress_callback)
            
            downloaded_assets += 1
            if progress_callback:
                progress = (downloaded_assets / total_assets) * 100
                progress_callback(progress, 0, downloaded_assets, total_assets)
        
        return True 