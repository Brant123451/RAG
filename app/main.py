# app/main.py
import sys
import os
from pathlib import Path  # 添加这行导入
from PyQt5.QtWidgets import QApplication
from .rag_system import RAGDesktopApp

def main():
    # 设置环境变量
    sys.path.append(str(Path(__file__).parent))
    
    # 设置当前工作目录为应用目录
    os.chdir(Path(__file__).parent)
    
    app = QApplication(sys.argv)
    window = RAGDesktopApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()