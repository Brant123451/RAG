# installer/rag_installer.py
import os
import sys
import subprocess
import shutil
import ctypes
import winreg
from pathlib import Path
import time

class RAGInstaller:
    def __init__(self):
        # 初始化配置
        self.app_name = "水利设计助手"
        self.app_version = "1.0.0"
        self.default_install_dir = Path(os.getenv('ProgramFiles', 'C:\\Program Files')) / self.app_name
        self.install_dir = self.default_install_dir
        self.desktop_dir = Path(os.path.expanduser("~")) / "Desktop"
        self.start_menu_dir = Path(os.path.expanduser("~")) / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        self.conda_path = r"E:\Useless\Anaconda\Scripts\conda.bat"
        
        # 资源路径
        self.resources_dir = Path(__file__).parent / "resources"
        self.icon_path = self.resources_dir / "icon.ico"
        self.logo_path = self.resources_dir / "logo.png"
        
        # 项目根目录
        self.project_root = Path(__file__).parent.parent
        
        # 目录结构
        self.dirs = ["docs", "models", "vector_store", "data"]
        
        # 依赖列表
        self.dependencies = [
            ["torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu118"],
            ["langchain"],
            ["langchain-community"],
            ["transformers"],
            ["sentence-transformers"],
            ["faiss-cpu"],
            ["pymupdf"],
            ["python-docx"],
            ["huggingface-hub"],
            ["tqdm"],
            ["watchdog"],
            ["modelscope"],
            ["sentencepiece"],
            ["accelerate"],
            ["pywin32"],
            ["pyqt5"],
            ["langchain-huggingface"]
        ]
        
        # 安装步骤
        self.steps = [
            "检查管理员权限",
            "准备安装环境",
            "创建Python虚拟环境",
            "安装系统依赖",
            "创建应用目录结构",
            "复制应用程序文件",
            "创建启动脚本",
            "创建桌面快捷方式",
            "添加开始菜单项",
            "添加卸载程序",
            "验证安装环境",
            "安装完成"
        ]
        
        # 模型文件提醒
        self.model_reminder = """请确保模型文件已手动放置到以下目录：
  - {models_dir}/chatglm3-6b
  - {models_dir}/bge-small-zh

首次使用请将水利设计文档放入:
  - {docs_dir}"""

    # 管理员权限检查方法
    def is_admin(self):
        """检查管理员权限"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def run_as_admin(self):
        """以管理员权限重新运行"""
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit()
        except Exception as e:
            print(f"无法获取管理员权限: {e}")
            sys.exit(1)

    # 虚拟环境创建方法
    def create_virtual_environment(self, log_callback=None):
        """创建Python虚拟环境"""
        if log_callback:
            log_callback("检查Python环境...")
        
        python_cmd = "python"
        pip_cmd = "pip"
        
        # 检查conda是否可用
        if os.path.exists(self.conda_path):
            if log_callback:
                log_callback("使用Anaconda环境...")
            
            try:
                # 创建conda环境
                result = subprocess.run([self.conda_path, "create", "-n", "rag_system", "python=3.10", "-y"], 
                                      capture_output=True, text=True, check=True)
                if log_callback:
                    log_callback("Conda环境创建成功")
                
                python_cmd = f'"{self.conda_path}" activate rag_system && python'
                pip_cmd = f'"{self.conda_path}" activate rag_system && pip'
            except subprocess.CalledProcessError as e:
                if log_callback:
                    log_callback(f"Conda环境创建失败: {e.stderr}")
                raise
        else:
            if log_callback:
                log_callback("创建Python虚拟环境...")
            
            # 创建venv环境
            venv_path = self.install_dir / "venv"
            if venv_path.exists():
                shutil.rmtree(venv_path)
            
            try:
                subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
                if log_callback:
                    log_callback("虚拟环境创建成功")
            except subprocess.CalledProcessError as e:
                if log_callback:
                    log_callback(f"虚拟环境创建失败: {e}")
                raise
            
            # 激活venv环境
            python_path = venv_path / "Scripts" / "python.exe"
            pip_path = venv_path / "Scripts" / "pip.exe"
            
            # 处理路径中的空格
            python_cmd = f'"{python_path}"' if ' ' in str(python_path) else str(python_path)
            pip_cmd = f'"{pip_path}"' if ' ' in str(pip_path) else str(pip_path)
        
        if log_callback:
            log_callback("升级pip...")
        
        try:
            # 升级pip
            subprocess.run([python_cmd.replace('"', ''), "-m", "pip", "install", "--upgrade", "pip"], 
                         check=True, capture_output=True, text=True)
            if log_callback:
                log_callback("pip升级成功")
        except subprocess.CalledProcessError as e:
            if log_callback:
                log_callback(f"pip升级失败: {e.stderr}")
            raise
        
        return python_cmd, pip_cmd
    
    # 依赖安装方法
    def install_dependencies(self, pip_cmd, log_callback=None, progress_callback=None):
        """安装Python依赖 - 增加重试机制和进度反馈"""
        if log_callback:
            log_callback("开始安装系统依赖...")
        
        total_deps = len(self.dependencies)
        
        # 安装依赖
        for idx, dep in enumerate(self.dependencies):
            package_name = dep[0]
            if log_callback:
                log_callback(f"正在安装 ({idx+1}/{total_deps}): {package_name}")
            
            # 更新进度
            if progress_callback:
                progress = int((idx / total_deps) * 100)
                progress_callback(progress)
            
            # 构建完整的命令
            if os.path.exists(self.conda_path):
                cmd = [self.conda_path, "activate", "rag_system", "&&", "pip", "install"] + dep
                cmd_str = " ".join(cmd)
            else:
                pip_exe = pip_cmd.replace('"', '')
                cmd = [pip_exe, "install"] + dep
                cmd_str = " ".join([f'"{item}"' if ' ' in item else item for item in cmd])
            
            # 添加重试机制
            max_retries = 3
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    if os.path.exists(self.conda_path):
                        # 使用shell执行conda命令
                        result = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, check=True)
                    else:
                        # 直接执行pip命令
                        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    
                    if log_callback:
                        log_callback(f"✓ 安装成功: {package_name}")
                    success = True
                    
                except subprocess.CalledProcessError as e:
                    retry_count += 1
                    error_msg = f"安装 {package_name} 失败 (尝试 {retry_count}/{max_retries})"
                    if log_callback:
                        log_callback(error_msg)
                    
                    if retry_count < max_retries:
                        if log_callback:
                            log_callback(f"等待5秒后重试...")
                        time.sleep(5)
                    else:
                        raise RuntimeError(f"无法安装 {package_name}: {e.stderr}")
        
        # 完成进度
        if progress_callback:
            progress_callback(100)
        
        if log_callback:
            log_callback("所有依赖安装完成")
    
    # 目录创建方法
    def create_directories(self, log_callback=None):
        """创建必要的目录"""
        if log_callback:
            log_callback("创建应用目录结构...")
        
        for dir_name in self.dirs:
            dir_path = self.install_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            if log_callback:
                log_callback(f"创建目录: {dir_path}")
        
        return self.install_dir / "models", self.install_dir / "docs"
    
    # 复制应用程序文件
    def copy_application_files(self, log_callback=None):
        """复制应用程序文件到安装目录"""
        if log_callback:
            log_callback("复制应用程序文件...")
        
        # 源目录：项目根目录下的app目录
        app_source = self.project_root / "app"
        
        # 目标目录：安装目录下的app目录
        app_target = self.install_dir / "app"
        
        # 复制整个app目录
        shutil.copytree(app_source, app_target, dirs_exist_ok=True)
        
        if log_callback:
            log_callback(f"应用程序文件复制到: {app_target}")
        
        return app_target
    
    # 启动脚本创建
    def create_launch_script(self, log_callback=None):
        """创建启动脚本"""
        if log_callback:
            log_callback("创建启动脚本...")

        # 确保使用正确的路径分隔符
        app_main_path = self.install_dir / "app" / "main.py"

        launch_content = f"""@echo off
chcp 65001 >nul
setlocal

set "CONDA_BAT={self.conda_path}"
set "VENV_PATH=%~dp0venv"

echo 正在激活环境...
if exist "%CONDA_BAT%" (
    call "%CONDA_BAT%" activate rag_system
    echo 使用Conda环境
) else (
    if exist "%VENV_PATH%\\Scripts\\activate.bat" (
        call "%VENV_PATH%\\Scripts\\activate.bat"
        echo 使用Venv环境
    ) else (
        echo 警告：未找到虚拟环境
    )
)

echo 设置离线模式...
set TRANSFORMERS_OFFLINE=1
set HF_DATASETS_OFFLINE=1
set HF_EVALUATE_OFFLINE=1

echo 设置工作目录...
cd /d "%~dp0"

echo 正在启动水利设计助手...
python -m app.main
if %ERRORLEVEL% NEQ 0 (
    echo 程序启动失败，错误代码: %ERRORLEVEL%
)
echo 程序已退出
pause
"""
        launch_path = self.install_dir / "启动水利助手.bat"
        with open(launch_path, "w", encoding="utf-8") as f:
            f.write(launch_content)
        
        if log_callback:
            log_callback(f"启动脚本创建完成: {launch_path}")
        
        return launch_path
    
    # 快捷方式创建
    def create_shortcut(self, target, name, description, log_callback=None):
        """创建快捷方式 - 使用 PowerShell"""
        if log_callback:
            log_callback("创建快捷方式...")
        
        # 应用程序图标路径
        app_icon_path = self.install_dir / "app" / "resources" / "app_icon.ico"
        
        try:
            # 创建桌面快捷方式
            desktop_shortcut = str(self.desktop_dir / f"{name}.lnk")
            ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{desktop_shortcut}')
$Shortcut.TargetPath = '{target}'
$Shortcut.WorkingDirectory = '{self.install_dir}'
$Shortcut.Description = '{description}'
$Shortcut.IconLocation = '{app_icon_path}'
$Shortcut.Save()
'''
            result = subprocess.run(["powershell", "-Command", ps_script], 
                                  shell=True, capture_output=True, text=True, check=True)
            if log_callback:
                log_callback("桌面快捷方式创建成功")
            
            # 创建开始菜单快捷方式
            start_menu_shortcut = str(self.start_menu_dir / f"{name}.lnk")
            ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{start_menu_shortcut}')
$Shortcut.TargetPath = '{target}'
$Shortcut.WorkingDirectory = '{self.install_dir}'
$Shortcut.Description = '{description}'
$Shortcut.IconLocation = '{app_icon_path}'
$Shortcut.Save()
'''
            result = subprocess.run(["powershell", "-Command", ps_script], 
                                  shell=True, capture_output=True, text=True, check=True)
            if log_callback:
                log_callback("开始菜单快捷方式创建成功")
            
            return True
            
        except subprocess.CalledProcessError as e:
            if log_callback:
                log_callback(f"创建快捷方式失败: {e.stderr}")
            return False
        except Exception as e:
            if log_callback:
                log_callback(f"创建快捷方式失败: {str(e)}")
            return False
    
    # 卸载程序创建
    def create_uninstaller(self, log_callback=None):
        """创建卸载程序"""
        if log_callback:
            log_callback("创建卸载程序...")
        
        uninstall_bat = self.install_dir / "uninstall.bat"
        uninstall_content = f"""@echo off
chcp 65001 >nul
setlocal

echo.
echo 正在卸载 {self.app_name}...
echo.

set "INSTALL_DIR=%~dp0"

:: 删除桌面快捷方式
del "{self.desktop_dir}\\{self.app_name}.lnk" >nul 2>&1

:: 删除开始菜单项
del "{self.start_menu_dir}\\{self.app_name}.lnk" >nul 2>&1

:: 删除注册表项
reg delete "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{self.app_name}" /f >nul 2>&1

:: 等待2秒确保进程关闭
timeout /t 2 /nobreak >nul

:: 删除安装目录
rd /s /q "%INSTALL_DIR%" >nul 2>&1

echo 卸载完成!
echo.
pause
"""
        with open(uninstall_bat, "w", encoding="utf-8") as f:
            f.write(uninstall_content)
        
        # 添加注册表项以便在控制面板中显示
        try:
            key_path = f"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{self.app_name}"
            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, self.app_name)
                winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, str(uninstall_bat))
                winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(self.install_dir))
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "水利设计院")
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, self.app_version)
                # 使用应用程序图标
                app_icon_path = self.install_dir / "app" / "resources" / "app_icon.ico"
                winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(app_icon_path))
        except Exception as e:
            if log_callback:
                log_callback(f"添加注册表项失败: {e}")
        
        return uninstall_bat
    
    # 安装验证
    def verify_installation(self, log_callback=None):
        """验证安装环境"""
        if log_callback:
            log_callback("验证安装环境...")
        
        try:
            # 检查关键包是否安装
            python_cmd = "python"
            if os.path.exists(self.conda_path):
                python_cmd = f'"{self.conda_path}" activate rag_system && python'
            else:
                venv_path = self.install_dir / "venv"
                python_path = venv_path / "Scripts" / "python.exe"
                python_cmd = f'"{python_path}"' if ' ' in str(python_path) else str(python_path)
            
            # 检查 langchain-huggingface 是否安装
            check_script = "import langchain_huggingface; print('langchain-huggingface installed')"
            result = subprocess.run(
                [python_cmd, "-c", check_script],
                capture_output=True, text=True
            )
            
            if "langchain-huggingface installed" in result.stdout:
                if log_callback:
                    log_callback("验证通过: langchain-huggingface 已安装")
                return True
            else:
                error_msg = f"验证失败: langchain-huggingface 未安装\n{result.stderr}"
                if log_callback:
                    log_callback(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"验证过程中出错: {str(e)}"
            if log_callback:
                log_callback(error_msg)
            return False
    
    # 主安装方法
    def install(self, progress_callback=None, log_callback=None):
        """执行安装过程"""
        try:
            # 检查安装目录是否存在
            if self.install_dir.exists():
                # 备份旧版本
                backup_dir = self.install_dir.with_name(f"{self.app_name}_backup")
                shutil.move(self.install_dir, backup_dir)
                if log_callback:
                    log_callback(f"备份旧版本到: {backup_dir}")
            
            # 创建安装目录
            self.install_dir.mkdir(parents=True, exist_ok=True)
            if log_callback:
                log_callback(f"创建安装目录: {self.install_dir}")
            
            # 创建虚拟环境
            python_cmd, pip_cmd = self.create_virtual_environment(log_callback)
            if log_callback:
                log_callback(f"Python命令: {python_cmd}")
                log_callback(f"Pip命令: {pip_cmd}")
            
            # 安装依赖
            self.install_dependencies(pip_cmd, log_callback, progress_callback)
            
            # 创建目录结构
            models_dir, docs_dir = self.create_directories(log_callback)
            if log_callback:
                log_callback(f"创建模型目录: {models_dir}")
                log_callback(f"创建文档目录: {docs_dir}")
            
            # 复制应用程序文件
            app_dir = self.copy_application_files(log_callback)
            
            # 创建启动脚本
            launch_script = self.create_launch_script(log_callback)
            if log_callback:
                log_callback(f"创建启动脚本: {launch_script}")
            
            # 创建快捷方式
            if self.create_shortcut(launch_script, self.app_name, "水利设计院RAG助手", log_callback):
                if log_callback:
                    log_callback("创建桌面和开始菜单快捷方式")
            else:
                if log_callback:
                    log_callback("快捷方式创建失败")
            
            # 创建卸载程序
            uninstall_bat = self.create_uninstaller(log_callback)
            if log_callback:
                log_callback(f"创建卸载程序: {uninstall_bat}")
            
            # 验证安装
            if not self.verify_installation(log_callback):
                raise RuntimeError("安装验证失败，请检查日志")
            
            # 完成安装
            if log_callback:
                log_callback("安装成功完成！")
            
            return True, self.model_reminder.format(
                models_dir=models_dir,
                docs_dir=docs_dir
            )
        except Exception as e:
            if log_callback:
                log_callback(f"安装过程中出错: {str(e)}")
            return False, f"安装失败: {str(e)}"