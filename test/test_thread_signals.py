#!/usr/bin/env python3
# test_thread_signals.py - 测试PyQt线程信号问题
import sys
import time
import threading
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QLabel, QWidget

class WorkerSignals(QObject):
    """Worker线程的信号定义"""
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)

class Worker:
    """模拟批量配置模块中的工作线程"""
    def __init__(self):
        self.signals = WorkerSignals()
        
    def do_work(self):
        """模拟配置过程"""
        try:
            print(f"[Worker] 工作线程开始，时间: {time.strftime('%H:%M:%S')}")
            self.signals.progress.emit("开始工作，步骤1")
            
            # 模拟延时操作
            time.sleep(1)
            self.signals.progress.emit("步骤1完成")
            
            # 模拟步骤2
            time.sleep(2)
            self.signals.progress.emit("步骤2完成")
            
            # 模拟步骤3
            time.sleep(1)
            self.signals.progress.emit("全部完成")
            
            # 发送完成信号
            print(f"[Worker] 准备发送完成信号，时间: {time.strftime('%H:%M:%S')}")
            self.signals.finished.emit(True, "操作成功完成")
            print(f"[Worker] 完成信号已发送，时间: {time.strftime('%H:%M:%S')}")
            
            return "Success"
        except Exception as e:
            print(f"[Worker] 发生错误: {str(e)}")
            self.signals.finished.emit(False, f"操作失败: {str(e)}")
            return None
        finally:
            print(f"[Worker] 工作线程结束，时间: {time.strftime('%H:%M:%S')}")

class MainWindow(QMainWindow):
    """测试主窗口"""
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("PyQt线程信号测试")
        self.setGeometry(100, 100, 400, 300)
        
        # 创建UI
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        layout = QVBoxLayout()
        self.central_widget.setLayout(layout)
        
        # 显示消息的标签
        self.status_label = QLabel("状态: 准备就绪")
        layout.addWidget(self.status_label)
        
        # 开始按钮
        self.start_button = QPushButton("开始操作")
        self.start_button.clicked.connect(self.start_operation)
        layout.addWidget(self.start_button)
        
        # 用于显示进度的标签
        self.progress_label = QLabel("进度: 未开始")
        layout.addWidget(self.progress_label)
        
        # 创建Worker实例
        self.worker = Worker()
        self.worker.signals.finished.connect(self.on_finished)
        self.worker.signals.progress.connect(self.on_progress)
        
        # 超时计时器
        self.timeout_timer = QTimer()
        self.timeout_timer.timeout.connect(self.check_timeout)
        
    def start_operation(self):
        """开始模拟操作"""
        self.start_button.setEnabled(False)
        self.status_label.setText("状态: 处理中...")
        self.progress_label.setText("进度: 已开始")
        
        # 记录开始时间
        self.start_time = time.time()
        
        # 启动超时计时器
        self.timeout_timer.start(1000)
        
        # 在线程中启动工作
        print(f"[Main] 启动工作线程，时间: {time.strftime('%H:%M:%S')}")
        self.work_thread = threading.Thread(target=self.worker.do_work)
        self.work_thread.daemon = True
        self.work_thread.start()
        
        print(f"[Main] 工作线程已启动，ID: {self.work_thread.ident}")
        
    def on_progress(self, message):
        """处理进度更新"""
        print(f"[Main] 收到进度消息: {message}, 时间: {time.strftime('%H:%M:%S')}")
        self.progress_label.setText(f"进度: {message}")
        
    def on_finished(self, success, message):
        """处理完成信号"""
        print(f"[Main] 收到完成信号: 成功={success}, 消息={message}, 时间: {time.strftime('%H:%M:%S')}")
        
        # 停止超时计时器
        self.timeout_timer.stop()
        
        # 重新启用按钮
        self.start_button.setEnabled(True)
        
        # 计算耗时
        elapsed = time.time() - self.start_time
        
        if success:
            self.status_label.setText(f"状态: 成功完成，耗时: {elapsed:.2f}秒")
        else:
            self.status_label.setText(f"状态: 操作失败，耗时: {elapsed:.2f}秒")
            
    def check_timeout(self):
        """检查是否超时"""
        elapsed = time.time() - self.start_time
        
        # 更新状态
        self.status_label.setText(f"状态: 处理中... ({int(elapsed)}秒)")
        
        # 检查线程状态
        if hasattr(self, 'work_thread'):
            print(f"[Main] 检查线程状态: {'运行中' if self.work_thread.is_alive() else '已结束'}, 时间: {time.strftime('%H:%M:%S')}")
            
        # 超过10秒视为超时
        if elapsed > 10:
            print(f"[Main] 操作超时，强制结束")
            self.timeout_timer.stop()
            if hasattr(self, 'work_thread') and self.work_thread.is_alive():
                print(f"[Main] 工作线程仍在运行，但UI未收到结果信号")
                self.on_finished(False, "操作超时")
            else:
                print(f"[Main] 工作线程已结束，但UI未收到结果信号")
                self.on_finished(False, "操作异常结束")
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    main_window = MainWindow()
    main_window.show()
    
    sys.exit(app.exec_()) 