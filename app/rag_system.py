# app/rag_system.py
import os
import sys
import shutil
import torch
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QTextEdit, QLineEdit, QFileDialog, 
                            QProgressBar, QMessageBox, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader, Docx2txtLoader
from transformers import AutoModel, AutoTokenizer, pipeline
from langchain_community.llms import HuggingFacePipeline
from pathlib import Path

# 获取应用根目录
APP_ROOT = Path(__file__).resolve().parent.parent

# 模型常量
MODEL_PATH = str(APP_ROOT / "models" / "chatglm3-6b")
EMBEDDING_PATH = str(APP_ROOT / "models" / "bge-small-zh")
DOCS_DIR = str(APP_ROOT / "docs")
VECTOR_STORE_PATH = str(APP_ROOT / "vector_store")

class ModelLoader(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(object, object)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.progress.emit(10, "初始化嵌入模型...")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # 使用本地文件
            emb = HuggingFaceEmbeddings(
                model_name=EMBEDDING_PATH,
                model_kwargs={"device": device},
                cache_folder=EMBEDDING_PATH,
                local_files_only=True
            )
            
            self.progress.emit(30, "加载ChatGLM Tokenizer...")
            tokenizer = AutoTokenizer.from_pretrained(
                MODEL_PATH, 
                trust_remote_code=True,
                local_files_only=True
            )
            
            self.progress.emit(50, "加载ChatGLM模型...")
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model = AutoModel.from_pretrained(
                MODEL_PATH,
                trust_remote_code=True,
                torch_dtype=torch.float16 if device.type == "cuda" else torch.float32,
                local_files_only=True
            ).to(device).eval()
            
            self.progress.emit(70, "创建文本生成管道...")
            pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=1024,
                temperature=0.2,
                top_p=0.8,
                do_sample=True,
                device=0 if torch.cuda.is_available() else -1,
            )
            llm = HuggingFacePipeline(pipeline=pipe)
            
            self.progress.emit(100, "模型加载完成")
            self.finished.emit(emb, llm)
            
        except Exception as e:
            import traceback
            error_msg = f"模型加载失败: {str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)

class DocumentIndexer(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, embeddings):
        super().__init__()
        self.embeddings = embeddings

    def run(self):
        try:
            self.progress.emit(10, "加载文档...")
            docs = []
            try:
                docs += DirectoryLoader(DOCS_DIR, glob="**/*.pdf", loader_cls=PyMuPDFLoader).load()
            except Exception as e:
                print(f"PDF加载错误: {e}")
            
            try:
                docs += DirectoryLoader(DOCS_DIR, glob="**/*.docx", loader_cls=Docx2txtLoader).load()
            except Exception as e:
                print(f"DOCX加载错误: {e}")
            
            if not docs:
                self.error.emit("未找到文档! 请将PDF/DOCX文件放入docs文件夹")
                return
                
            self.progress.emit(30, f"处理 {len(docs)} 个文档...")
            splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            chunks = splitter.split_documents(docs)
            
            self.progress.emit(60, "创建向量索引...")
            vs = FAISS.from_documents(chunks, self.embeddings)
            
            self.progress.emit(80, "保存索引...")
            vs.save_local(VECTOR_STORE_PATH)
            
            self.progress.emit(100, f"索引创建完成! {len(chunks)} 个文档片段")
            self.finished.emit(vs)
            
        except Exception as e:
            import traceback
            error_msg = f"文档索引创建失败: {str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)

class QueryWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, qa, question):
        super().__init__()
        self.qa = qa
        self.question = question

    def run(self):
        try:
            result = self.qa.run(self.question)
            cleaned_answer = result.replace("<|im_end|>", "").replace("<|im_start|>", "")
            self.finished.emit(cleaned_answer)
        except Exception as e:
            import traceback
            error_msg = f"查询失败: {str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)

class RAGDesktopApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("水利设计院文档智能助手")
        self.setGeometry(100, 100, 800, 600)
        
        # 设置应用图标
        icon_path = APP_ROOT / "app" / "resources" / "app_icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        self.embeddings = None
        self.llm = None
        self.vector_store = None
        self.qa = None
        
        # 验证模型路径
        self.validate_model_paths()
        
        self.init_ui()
        self.load_models()

    def validate_model_paths(self):
        """验证模型路径是否存在"""
        errors = []
        if not os.path.exists(MODEL_PATH):
            errors.append(f"模型路径不存在: {MODEL_PATH}\n请将模型文件放入此目录")
        
        if not os.path.exists(EMBEDDING_PATH):
            errors.append(f"嵌入模型路径不存在: {EMBEDDING_PATH}\n请将模型文件放入此目录")
        
        if errors:
            QMessageBox.critical(self, "模型文件缺失", "\n\n".join(errors))
            sys.exit(1)

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        title_layout = QHBoxLayout()
        title_label = QLabel("水利设计院文档智能助手")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        title_layout.addWidget(title_label)
        
        doc_group = QGroupBox("文档管理")
        doc_layout = QVBoxLayout()
        
        self.index_btn = QPushButton("构建文档索引")
        self.index_btn.clicked.connect(self.build_document_index)
        doc_layout.addWidget(self.index_btn)
        
        self.add_docs_btn = QPushButton("添加文档")
        self.add_docs_btn.clicked.connect(self.add_documents)
        doc_layout.addWidget(self.add_docs_btn)
        
        self.index_status = QLabel("索引状态: 未创建")
        doc_layout.addWidget(self.index_status)
        
        self.progress_bar = QProgressBar()
        doc_layout.addWidget(self.progress_bar)
        
        doc_group.setLayout(doc_layout)
        
        qa_group = QGroupBox("智能问答")
        qa_layout = QVBoxLayout()
        
        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("请输入您的问题...")
        qa_layout.addWidget(self.question_input)
        
        self.ask_btn = QPushButton("提问")
        self.ask_btn.setEnabled(False)
        self.ask_btn.clicked.connect(self.ask_question)
        qa_layout.addWidget(self.ask_btn)
        
        self.answer_area = QTextEdit()
        self.answer_area.setReadOnly(True)
        qa_layout.addWidget(self.answer_area)
        
        qa_group.setLayout(qa_layout)
        
        self.status_bar = QLabel("正在初始化...")
        self.status_bar.setAlignment(Qt.AlignCenter)
        self.status_bar.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        
        main_layout.addLayout(title_layout)
        main_layout.addWidget(doc_group)
        main_layout.addWidget(qa_group)
        main_layout.addWidget(self.status_bar)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def load_models(self):
        self.status_bar.setText("正在加载AI模型，请稍候...")
        self.model_loader = ModelLoader()
        self.model_loader.progress.connect(self.update_progress)
        self.model_loader.finished.connect(self.on_models_loaded)
        self.model_loader.error.connect(self.show_error)
        self.model_loader.start()

    def build_document_index(self):
        if not self.embeddings:
            self.show_error("请先等待模型加载完成")
            return
            
        self.status_bar.setText("开始构建文档索引...")
        self.indexer = DocumentIndexer(self.embeddings)
        self.indexer.progress.connect(self.update_progress)
        self.indexer.finished.connect(self.on_index_created)
        self.indexer.error.connect(self.show_error)
        self.indexer.start()

    def add_documents(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择文档", "", 
            "文档文件 (*.pdf *.docx)"
        )
        
        if files:
            for file in files:
                dest = os.path.join(DOCS_DIR, os.path.basename(file))
                shutil.copy(file, dest)
            self.show_info(f"已添加 {len(files)} 个文档到 docs 文件夹")

    def ask_question(self):
        question = self.question_input.text().strip()
        if not question:
            self.show_warning("请输入问题")
            return
            
        self.answer_area.setText("思考中...")
        self.worker = QueryWorker(self.qa, question)
        self.worker.finished.connect(self.on_answer_received)
        self.worker.error.connect(self.show_error)
        self.worker.start()

    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.status_bar.setText(message)

    def on_models_loaded(self, emb, llm):
        self.embeddings = emb
        self.llm = llm
        self.status_bar.setText("AI模型加载完成!")
        
        index_file = os.path.join(VECTOR_STORE_PATH, "index.faiss")
        if os.path.exists(index_file):
            try:
                self.vector_store = FAISS.load_local(
                    VECTOR_STORE_PATH, self.embeddings, allow_dangerous_deserialization=True
                )
                self.qa = RetrievalQA.from_chain_type(
                    llm=self.llm, retriever=self.vector_store.as_retriever()
                )
                self.ask_btn.setEnabled(True)
                self.index_status.setText("索引状态: 已加载")
                self.show_info("文档索引已加载，可以开始提问")
            except Exception as e:
                self.show_error(f"加载索引失败: {str(e)}")
        else:
            self.index_status.setText("索引状态: 未创建")

    def on_index_created(self, vs):
        self.vector_store = vs
        self.qa = RetrievalQA.from_chain_type(
            llm=self.llm, retriever=self.vector_store.as_retriever()
        )
        self.ask_btn.setEnabled(True)
        self.index_status.setText("索引状态: 已创建")
        self.show_info("文档索引创建完成，可以开始提问")

    def on_answer_received(self, answer):
        self.answer_area.setText(answer)

    def show_error(self, message):
        QMessageBox.critical(self, "错误", message)
        self.status_bar.setText(f"错误: {message}")

    def show_warning(self, message):
        QMessageBox.warning(self, "警告", message)
        self.status_bar.setText(f"警告: {message}")

    def show_info(self, message):
        QMessageBox.information(self, "信息", message)
        self.status_bar.setText(message)