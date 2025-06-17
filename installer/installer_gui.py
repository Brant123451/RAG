import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from pathlib import Path
from .rag_installer import RAGInstaller

class InstallerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("水利设计院RAG系统安装程序")
        self.root.geometry("700x500")
        self.root.resizable(False, False)
        
        # 创建安装器实例
        self.installer = RAGInstaller()
        
        # 设置图标
        try:
            self.root.iconbitmap(str(self.installer.icon_path))
        except:
            pass
        
        # 创建UI元素
        self.create_widgets()
        
        self.installation_thread = None
        self.current_step = 0
        self.total_steps = len(self.installer.steps)
    
    def create_widgets(self):
        """创建UI组件"""
        # 标题栏
        self.header_frame = tk.Frame(self.root, bg="white", height=80)
        self.header_frame.pack(fill=tk.X, side=tk.TOP)
        
        # 添加logo
        try:
            self.logo_img = tk.PhotoImage(file=str(self.installer.logo_path))
            self.logo_img = self.logo_img.subsample(4, 4)  # 缩小图像
        except:
            self.logo_img = None
        
        if self.logo_img:
            self.logo_label = tk.Label(self.header_frame, image=self.logo_img, bg="white")
            self.logo_label.pack(side=tk.LEFT, padx=10)
        
        # 标题
        title_frame = tk.Frame(self.header_frame, bg="white")
        title_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        self.title_label = tk.Label(title_frame, text="水利设计院RAG系统", 
                                  font=("Microsoft YaHei", 16, "bold"), bg="white")
        self.title_label.pack(anchor=tk.W)
        
        self.subtitle_label = tk.Label(title_frame, text="智能文档助手安装程序", 
                                     font=("Microsoft YaHei", 12), bg="white")
        self.subtitle_label.pack(anchor=tk.W)
        
        # 安装目录选择
        dir_frame = tk.LabelFrame(self.root, text="安装设置", padx=10, pady=10)
        dir_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(dir_frame, text="安装目录:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.dir_var = tk.StringVar(value=str(self.installer.default_install_dir))
        dir_entry = tk.Entry(dir_frame, textvariable=self.dir_var, width=50)
        dir_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        browse_button = tk.Button(dir_frame, text="浏览...", command=self.browse_directory, width=10)
        browse_button.grid(row=0, column=2, padx=5, pady=5)
        
        dir_frame.columnconfigure(1, weight=1)
        
        # 安装按钮区域
        install_button_frame = tk.Frame(self.root)
        install_button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # 安装按钮
        self.install_button = tk.Button(install_button_frame, text="开始安装", command=self.start_installation,
                                      width=20, height=2, font=("Microsoft YaHei", 12, "bold"),
                                      bg="#4CAF50", fg="white", relief=tk.RAISED)
        self.install_button.pack(pady=10)
        
        # 进度条
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(fill=tk.X, padx=20, pady=(5, 0))
        
        self.progress_label = tk.Label(progress_frame, text="准备安装...", font=("Microsoft YaHei", 9))
        self.progress_label.pack(anchor=tk.W)
        
        self.progress = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=660, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)
        
        # 日志区域
        log_frame = tk.LabelFrame(self.root, text="安装日志", padx=10, pady=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.log_text = tk.Text(log_frame, height=8, state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # 按钮区域
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        self.cancel_button = tk.Button(button_frame, text="退出", command=self.root.destroy,
                                     width=10, font=("Microsoft YaHei", 9))
        self.cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        status_label = tk.Label(self.root, textvariable=self.status_var, font=("Microsoft YaHei", 9), fg="blue")
        status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(0, 5))
        
        # 设置窗口居中
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'+{x}+{y}')
    
    def browse_directory(self):
        """浏览安装目录"""
        directory = filedialog.askdirectory(initialdir=self.installer.default_install_dir.parent)
        if directory:
            self.dir_var.set(directory)
            self.installer.install_dir = Path(directory)
    
    def log_message(self, message):
        """记录日志消息"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.status_var.set(message)
        self.root.update()
    
    def update_progress(self, step):
        """更新进度条"""
        progress_value = (step / self.total_steps) * 100
        self.progress['value'] = progress_value
        self.progress_label.config(text=f"步骤 {step}/{self.total_steps}: {self.installer.steps[step-1]}")
        self.root.update()
    
    def start_installation(self):
        """开始安装过程"""
        if not self.installer.is_admin():
            self.log_message("需要管理员权限，正在请求...")
            self.installer.run_as_admin()
            return
        
        self.install_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED)
        
        # 设置安装目录
        self.installer.install_dir = Path(self.dir_var.get())
        
        # 在后台线程中运行安装
        self.installation_thread = threading.Thread(target=self.run_installation)
        self.installation_thread.daemon = True
        self.installation_thread.start()
    
    def run_installation(self):
        """执行安装过程"""
        try:
            self.current_step = 0
            
            # 步骤1: 检查管理员权限
            self.current_step += 1
            self.update_progress(self.current_step)
            self.log_message(f"[步骤 {self.current_step}/{self.total_steps}] {self.installer.steps[self.current_step-1]}")
            if not self.installer.is_admin():
                self.log_message("错误：需要管理员权限")
                return
            
            # 步骤2: 准备安装环境
            self.current_step += 1
            self.update_progress(self.current_step)
            self.log_message(f"[步骤 {self.current_step}/{self.total_steps}] {self.installer.steps[self.current_step-1]}")
            # 创建安装目录
            self.installer.install_dir.mkdir(parents=True, exist_ok=True)
            self.log_message(f"安装目录: {self.installer.install_dir}")
            
            # 步骤3: 创建Python虚拟环境
            self.current_step += 1
            self.update_progress(self.current_step)
            self.log_message(f"[步骤 {self.current_step}/{self.total_steps}] {self.installer.steps[self.current_step-1]}")
            python_cmd, pip_cmd = self.installer.create_virtual_environment(
                lambda msg: self.log_message(msg))
            self.log_message(f"Python命令: {python_cmd}")
            self.log_message(f"Pip命令: {pip_cmd}")
            
            # 步骤4: 安装系统依赖
            self.current_step += 1
            self.update_progress(self.current_step)
            self.log_message(f"[步骤 {self.current_step}/{self.total_steps}] {self.installer.steps[self.current_step-1]}")
            self.log_message(f"开始安装 {len(self.installer.dependencies)} 个依赖包...")
            self.installer.install_dependencies(pip_cmd, 
                                              lambda msg: self.log_message(msg), 
                                              lambda progress: self.progress.config(value=progress))
            
            # 步骤5: 创建应用目录结构
            self.current_step += 1
            self.update_progress(self.current_step)
            self.log_message(f"[步骤 {self.current_step}/{self.total_steps}] {self.installer.steps[self.current_step-1]}")
            models_dir, docs_dir = self.installer.create_directories(lambda msg: self.log_message(msg))
            self.log_message(f"模型目录: {models_dir}")
            self.log_message(f"文档目录: {docs_dir}")
            
            # 步骤6: 复制应用程序文件
            self.current_step += 1
            self.update_progress(self.current_step)
            self.log_message(f"[步骤 {self.current_step}/{self.total_steps}] {self.installer.steps[self.current_step-1]}")
            app_dir = self.installer.copy_application_files(lambda msg: self.log_message(msg))
            
            # 步骤7: 创建启动脚本
            self.current_step += 1
            self.update_progress(self.current_step)
            self.log_message(f"[步骤 {self.current_step}/{self.total_steps}] {self.installer.steps[self.current_step-1]}")
            launch_script = self.installer.create_launch_script(lambda msg: self.log_message(msg))
            self.log_message(f"启动脚本: {launch_script}")
            
            # 步骤8: 创建桌面快捷方式
            self.current_step += 1
            self.update_progress(self.current_step)
            self.log_message(f"[步骤 {self.current_step}/{self.total_steps}] {self.installer.steps[self.current_step-1]}")
            if self.installer.create_shortcut(launch_script, self.installer.app_name, "水利设计院RAG助手", lambda msg: self.log_message(msg)):
                self.log_message("桌面快捷方式创建成功")
            else:
                self.log_message("警告：快捷方式创建失败")
            
            # 步骤9: 添加开始菜单项
            self.current_step += 1
            self.update_progress(self.current_step)
            self.log_message(f"[步骤 {self.current_step}/{self.total_steps}] {self.installer.steps[self.current_step-1]}")
            # 已在桌面快捷方式中处理
            self.log_message("开始菜单项已添加")
            
            # 步骤10: 添加卸载程序
            self.current_step += 1
            self.update_progress(self.current_step)
            self.log_message(f"[步骤 {self.current_step}/{self.total_steps}] {self.installer.steps[self.current_step-1]}")
            uninstall_bat = self.installer.create_uninstaller(lambda msg: self.log_message(msg))
            self.log_message(f"卸载程序: {uninstall_bat}")
            
            # 步骤11: 验证安装环境
            self.current_step += 1
            self.update_progress(self.current_step)
            self.log_message(f"[步骤 {self.current_step}/{self.total_steps}] {self.installer.steps[self.current_step-1]}")
            if not self.installer.verify_installation(lambda msg: self.log_message(msg)):
                raise RuntimeError("安装验证失败")
            
            # 步骤12: 安装完成
            self.current_step += 1
            self.update_progress(self.current_step)
            self.log_message(f"[步骤 {self.current_step}/{self.total_steps}] {self.installer.steps[self.current_step-1]}")
            self.log_message("安装成功完成！")
            
            reminder = self.installer.model_reminder.format(
                models_dir=models_dir,
                docs_dir=docs_dir
            )
            messagebox.showinfo("安装完成", f"安装成功！\n\n{reminder}")
            
            self.install_button.config(state=tk.NORMAL)
            self.cancel_button.config(text="关闭", command=self.root.destroy, state=tk.NORMAL)
        except Exception as e:
            self.log_message(f"安装过程中出错: {str(e)}")
            messagebox.showerror("安装错误", f"安装过程中发生错误:\n{str(e)}")
            self.install_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.NORMAL)
    
    def run(self):
        """运行应用程序"""
        self.root.mainloop()