import sys
import os
from pathlib import Path

def main():
    # 获取安装目录
    install_dir = Path(__file__).parent.parent
    
    # 添加虚拟环境到PATH
    venv_path = install_dir / "venv"
    if venv_path.exists():
        scripts_path = venv_path / "Scripts"
        os.environ["PATH"] = f"{scripts_path};{os.environ['PATH']}"
    
    # 添加应用目录到sys.path
    sys.path.insert(0, str(install_dir))
    
    # 导入并运行主应用
    from app.main import main
    main()

if __name__ == "__main__":
    main()