import sys
from pathlib import Path

# 将项目根目录添加到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from installer.installer_gui import InstallerGUI

if __name__ == "__main__":
    # 检查管理员权限
    from installer.rag_installer import RAGInstaller
    installer = RAGInstaller()
    if not installer.is_admin():
        print("请求管理员权限...")
        installer.run_as_admin()
        sys.exit()
    
    gui = InstallerGUI()
    gui.run()