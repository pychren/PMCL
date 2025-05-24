import os
import sys
import subprocess
import shutil
# 仅在win32平台导入winreg
if sys.platform == "win32":
    import winreg

# 查找Java可执行文件的方法
def find_java_executables():
    """在系统中查找Java可执行文件路径"""
    java_installations = []
    
    if sys.platform == "win32":
        # 尝试通过注册表查找JDK
        def add_jdk_from_registry(hkey, path, view_flags):
            try:
                reg_key = winreg.OpenKey(hkey, path, 0, winreg.KEY_READ | view_flags)
                for i in range(winreg.QueryInfoKey(reg_key)[0]):
                    version = winreg.EnumKey(reg_key, i)
                    try:
                        version_key = winreg.OpenKey(reg_key, version)
                        java_home, reg_type = winreg.QueryValueEx(version_key, "JavaHome")
                        java_exec = os.path.join(java_home, "bin", "java.exe")
                        # 可以尝试从java -version获取更详细信息，但可能较慢且复杂，先用版本号
                        # name = f"Java {version} ({java_home})"
                        name = f"Java {version}"
                        java_installations.append({'name': name, 'path': java_exec})
                        winreg.CloseKey(version_key)
                    except Exception as e_version:
                        print(f"处理Java注册表版本 {version} 时发生错误: {e_version}")
                winreg.CloseKey(reg_key)
            except FileNotFoundError:
                pass # 注册表路径不存在
            except Exception as e:
                print(f"查找Java注册表时发生错误: {e}")

        add_jdk_from_registry(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\JavaSoft\\Java Development Kit", winreg.KEY_WOW64_64KEY) # 64位
        add_jdk_from_registry(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\JavaSoft\\Java Development Kit", winreg.KEY_WOW64_32KEY) # 32位

        # 查找系统PATH中的java
        java_in_path = shutil.which("java")
        if java_in_path:
            # 对于PATH中的java，可以尝试运行命令获取版本信息，或者只显示路径
            # 为了简单，先显示路径或通用名称
            path_entry_name = "Java (系统PATH)"
            # 检查是否已经通过注册表找到了这个java.exe，避免重复
            if not any(install['path'].lower() == java_in_path.lower() for install in java_installations):
                 java_installations.append({'name': path_entry_name, 'path': java_in_path})

    # 可以在这里添加查找其他操作系统下Java的逻辑
    elif sys.platform == "darwin": # macOS
         try:
             result = subprocess.run(['/usr/libexec/java_home'], capture_output=True, text=True, check=True)
             java_home = result.stdout.strip()
             java_exec = os.path.join(java_home, 'bin', 'java')
             if os.path.exists(java_exec):
                 # 在macOS上获取版本信息可能也需要运行命令，先用通用名称
                 name = f"Java (macOS java_home)"
                 java_installations.append({'name': name, 'path': java_exec})
         except (subprocess.CalledProcessError, FileNotFoundError) as e:
             print(f"在macOS上查找java_home时发生错误: {e}")

         # 也检查PATH
         java_in_path = shutil.which("java")
         if java_in_path and not any(install['path'].lower() == java_in_path.lower() for install in java_installations):
             name = "Java (系统PATH)"
             java_installations.append({'name': name, 'path': java_in_path})

    elif sys.platform.startswith("linux"): # Linux
         try:
             result = subprocess.run(['which', 'java'], capture_output=True, text=True, check=True)
             java_exec = result.stdout.strip()
             if os.path.exists(java_exec) and not any(install['path'].lower() == java_exec.lower() for install in java_installations):
                 # 在Linux上获取版本信息也可能需要运行命令，先用通用名称
                 name = "Java (系统PATH)"
                 java_installations.append({'name': name, 'path': java_exec})
         except (subprocess.CalledProcessError, FileNotFoundError) as e:
             print(f"在Linux上查找java时发生错误: {e}")

    # 过滤掉不存在的文件 (虽然查找时已过滤，再次确认)
    # unique_installations = [install for install in java_installations if os.path.exists(install['path'])]

    # 如果没有找到任何Java，添加一个提示项
    if not java_installations:
        java_installations.append({'name': "未找到Java，请检查安装或环境变量", 'path': ""})

    return java_installations 

def recursive_java_search(root_dir):
    """递归搜索指定目录查找Java可执行文件"""
    found_executables = []
    java_executable_name = "java.exe" if sys.platform == "win32" else "java"

    if not os.path.isdir(root_dir):
        print(f"错误: 目录不存在 - {root_dir}")
        return found_executables

    print(f"开始在 {root_dir} 中搜索 {java_executable_name}...")
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if java_executable_name in filenames:
            java_exec_path = os.path.join(dirpath, java_executable_name)
            # 可以尝试获取版本信息，但递归搜索中可能太慢
            name = f"{java_executable_name} ({dirpath})"
            found_executables.append({'name': name, 'path': java_exec_path})
            # 为了避免找到太多结果，可以考虑在这里添加一个break或者限制数量
            # 例如： if len(found_executables) > 100: break # 限制最多找到100个
    print(f"在 {root_dir} 中搜索完成。")
    return found_executables 