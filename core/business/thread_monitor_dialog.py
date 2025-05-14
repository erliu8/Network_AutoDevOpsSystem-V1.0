#!/usr/bin/env python
# thread_monitor_dialog.py
import threading
import time
import traceback
import os
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTableWidget, QTableWidgetItem,
                            QHeaderView, QMessageBox, QTextEdit, QSplitter,
                            QTabWidget, QComboBox, QCheckBox, QGroupBox,
                            QDialog, QGridLayout, QSpinBox)
from PyQt5.QtGui import QColor, QFont, QIcon

from core.business.thread_monitor import ThreadMonitor
from core.business.thread_factory import ThreadFactory

class ThreadMonitorDialog(QDialog):
    """增强版线程监控对话框，用于监控和管理线程"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("线程监控器")
        self.setMinimumSize(800, 600)
        
        # 创建线程监控器
        self.thread_monitor = ThreadMonitor()
        self.thread_monitor.thread_status_updated.connect(self.update_thread_list)
        self.thread_monitor.thread_issue_detected.connect(self.show_thread_issue)
        
        # 获取线程工厂
        self.thread_factory = ThreadFactory.get_instance()
        
        # 当前选中的模块
        self.current_module = "all"
        
        # 初始化UI
        self.init_ui()
        
        # 默认开始监控
        self.start_monitoring()
    
    def init_ui(self):
        """初始化UI界面"""
        main_layout = QVBoxLayout(self)
        
        # 创建控制面板
        control_panel = QWidget()
        control_layout = QGridLayout(control_panel)
        
        # 监控控制
        self.monitor_btn = QPushButton("开始监控")
        self.monitor_btn.clicked.connect(self.toggle_monitoring)
        control_layout.addWidget(self.monitor_btn, 0, 0)
        
        # 刷新间隔
        interval_label = QLabel("刷新间隔:")
        control_layout.addWidget(interval_label, 0, 1)
        
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1秒", "3秒", "5秒", "10秒", "30秒", "60秒"])
        self.interval_combo.setCurrentIndex(2)  # 默认5秒
        self.interval_combo.currentIndexChanged.connect(self.change_interval)
        control_layout.addWidget(self.interval_combo, 0, 2)
        
        # 模块筛选
        module_label = QLabel("模块筛选:")
        control_layout.addWidget(module_label, 0, 3)
        
        self.module_combo = QComboBox()
        self.module_combo.addItem("所有模块", "all")
        for module, name in self.thread_monitor.module_name_mapping.items():
            self.module_combo.addItem(name, module)
        self.module_combo.currentIndexChanged.connect(self.filter_threads)
        control_layout.addWidget(self.module_combo, 0, 4)
        
        # 刷新按钮
        refresh_btn = QPushButton("强制刷新")
        refresh_btn.clicked.connect(self.refresh_threads)
        control_layout.addWidget(refresh_btn, 0, 5)
        
        # 第二行控制按钮
        # 创建测试线程按钮
        create_test_btn = QPushButton("创建测试线程")
        create_test_btn.clicked.connect(self.create_test_threads)
        control_layout.addWidget(create_test_btn, 1, 0)
        
        # 测试线程数量
        test_count_label = QLabel("测试线程数:")
        control_layout.addWidget(test_count_label, 1, 1)
        
        self.test_count_spin = QSpinBox()
        self.test_count_spin.setRange(1, 10)
        self.test_count_spin.setValue(5)
        control_layout.addWidget(self.test_count_spin, 1, 2)
        
        # 模块扫描按钮
        scan_modules_btn = QPushButton("扫描所有模块")
        scan_modules_btn.clicked.connect(self.scan_modules)
        control_layout.addWidget(scan_modules_btn, 1, 3)
        
        # 注册系统线程按钮
        register_system_btn = QPushButton("注册系统线程")
        register_system_btn.clicked.connect(self.register_system_threads)
        control_layout.addWidget(register_system_btn, 1, 4)
        
        # 帮助按钮
        help_btn = QPushButton("帮助")
        help_btn.clicked.connect(self.show_help)
        control_layout.addWidget(help_btn, 1, 5)
        
        main_layout.addWidget(control_panel)
        
        # 创建线程列表
        self.thread_table = QTableWidget()
        self.thread_table.setColumnCount(6)
        self.thread_table.setHorizontalHeaderLabels(["线程ID", "线程名称", "状态", "模块", "启动时间", "来源"])
        self.thread_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.thread_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.thread_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.thread_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.thread_table.clicked.connect(self.show_thread_details)
        
        # 创建底部面板
        bottom_splitter = QSplitter(Qt.Horizontal)
        
        # 线程详情面板
        detail_panel = QWidget()
        detail_layout = QVBoxLayout(detail_panel)
        
        detail_label = QLabel("线程详情:")
        detail_layout.addWidget(detail_label)
        
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        detail_layout.addWidget(self.detail_text)
        
        # 系统信息面板
        system_panel = QWidget()
        system_layout = QVBoxLayout(system_panel)
        
        system_label = QLabel("系统信息:")
        system_layout.addWidget(system_label)
        
        self.system_text = QTextEdit()
        self.system_text.setReadOnly(True)
        system_layout.addWidget(self.system_text)
        
        # 添加到拆分器
        bottom_splitter.addWidget(detail_panel)
        bottom_splitter.addWidget(system_panel)
        bottom_splitter.setSizes([400, 400])
        
        # 创建主拆分器
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(self.thread_table)
        main_splitter.addWidget(bottom_splitter)
        main_splitter.setSizes([400, 200])
        
        main_layout.addWidget(main_splitter)
        
        # 更新系统信息
        self.update_system_info()
    
    def toggle_monitoring(self):
        """切换监控状态"""
        if self.thread_monitor.monitoring:
            self.thread_monitor.stop_monitoring()
            self.monitor_btn.setText("开始监控")
        else:
            interval = self.get_current_interval()
            self.thread_monitor.start_monitoring(interval)
            self.monitor_btn.setText("停止监控")
    
    def start_monitoring(self):
        """开始监控"""
        interval = self.get_current_interval()
        self.thread_monitor.start_monitoring(interval)
        self.monitor_btn.setText("停止监控")
    
    def get_current_interval(self):
        """获取当前选择的刷新间隔（秒）"""
        text = self.interval_combo.currentText()
        return int(text.split("秒")[0])
    
    def change_interval(self, index):
        """更改刷新间隔"""
        if self.thread_monitor.monitoring:
            interval = self.get_current_interval()
            self.thread_monitor.stop_monitoring()
            self.thread_monitor.start_monitoring(interval)
    
    def update_thread_list(self, threads):
        """更新线程列表"""
        self.filter_threads(threads=threads)
    
    def filter_threads(self, index=None, threads=None):
        """按模块筛选线程"""
        if index is not None:
            self.current_module = self.module_combo.itemData(index)
        
        if threads is None:
            threads = [t.to_dict() for t in self.thread_monitor.get_all_threads()]
        
        print(f"过滤前的线程总数: {len(threads)}")
        for t in threads:
            print(f"- 线程: {t['name']} (ID: {t['thread_id']}, 模块: {t['module']})")
            
        # 筛选线程
        if self.current_module != "all":
            filtered_threads = [t for t in threads if t["module"] == self.current_module]
        else:
            filtered_threads = threads
        
        # 更新表格
        self.thread_table.setRowCount(len(filtered_threads))
        
        for row, thread in enumerate(filtered_threads):
            # 线程ID
            thread_id_item = QTableWidgetItem(str(thread["thread_id"]))
            self.thread_table.setItem(row, 0, thread_id_item)
            
            # 线程名称
            name_item = QTableWidgetItem(thread["name"])
            self.thread_table.setItem(row, 1, name_item)
            
            # 状态
            status_item = QTableWidgetItem(thread["status"])
            # 根据状态设置颜色
            if thread["status"] == "正常":
                status_item.setForeground(QColor(0, 128, 0))  # 绿色
            elif thread["status"] == "卡住":
                status_item.setForeground(QColor(255, 165, 0))  # 橙色
            elif thread["status"] == "错误":
                status_item.setForeground(QColor(255, 0, 0))  # 红色
            self.thread_table.setItem(row, 2, status_item)
            
            # 模块
            module_name = thread["module"]
            if module_name in self.thread_monitor.module_name_mapping:
                module_name = self.thread_monitor.module_name_mapping[module_name]
            module_item = QTableWidgetItem(module_name)
            self.thread_table.setItem(row, 3, module_item)
            
            # 启动时间
            start_time_item = QTableWidgetItem(thread["start_time"])
            self.thread_table.setItem(row, 4, start_time_item)
            
            # 来源
            source = "工厂" if thread.get("factory_created", True) else "系统"
            source_item = QTableWidgetItem(source)
            self.thread_table.setItem(row, 5, source_item)
        
        print(f"实际显示的线程数: {len(filtered_threads)}")
        
        # 更新系统信息
        self.update_system_info()
    
    def refresh_threads(self):
        """刷新线程列表"""
        print("开始刷新线程列表...")
        # 强制先标记现有线程为已结束
        import threading
        current_thread_idents = [t.ident for t in threading.enumerate() if t.ident is not None]
        
        # 执行完整的线程检查
        print("执行强制完整线程检查...")
        self.thread_monitor.check_threads()
        
        # 打印当前线程信息
        all_threads = self.thread_monitor.get_all_threads()
        print(f"线程监控器中的线程数: {len(all_threads)}")
        for thread in all_threads:
            print(f"监控的线程: {thread.name} (ID: {thread.thread_id}, 模块: {thread.module})")

        # 获取线程工厂注册的线程
        if hasattr(self.thread_monitor, 'thread_factory') and self.thread_monitor.thread_factory:
            thread_factory = self.thread_monitor.thread_factory
            factory_threads = thread_factory.threads
            active_threads = thread_factory.get_active_threads()
            
            print(f"线程工厂中注册的线程数: {len(factory_threads)}")
            for thread_id, info in factory_threads.items():
                thread_obj = active_threads.get(thread_id)
                sys_id = thread_obj.ident if thread_obj else "未启动"
                print(f"- 工厂线程: {info['name']} (ID: {thread_id}, 系统ID: {sys_id}, 模块: {info['module']})")
        
        # 系统当前线程信息
        import threading
        sys_threads = threading.enumerate()
        print(f"系统当前线程数: {len(sys_threads)}")
        for t in sys_threads:
            print(f"- 系统线程: {t.name} (ID: {t.ident})")

        # 最后更新UI显示
        self.filter_threads()
    
    def show_thread_details(self, index):
        """显示线程详情"""
        row = index.row()
        thread_id_item = self.thread_table.item(row, 0)
        if not thread_id_item:
            return
            
        thread_id = int(thread_id_item.text())
        thread_info = self.thread_monitor.get_thread_info(thread_id)
        
        if not thread_info:
            self.detail_text.setText("无法获取线程信息")
            return
            
        thread_dict = thread_info.to_dict()
        
        details = f"线程ID: {thread_dict['thread_id']}\n"
        details += f"线程名称: {thread_dict['name']}\n"
        details += f"状态: {thread_dict['status']}\n"
        details += f"守护线程: {'是' if thread_dict['daemon'] else '否'}\n"
        details += f"模块: {thread_dict['module']}\n"
        
        # 转换模块名为可读名称
        if thread_dict['module'] in self.thread_monitor.module_name_mapping:
            module_readable = self.thread_monitor.module_name_mapping[thread_dict['module']]
            details += f"模块名称: {module_readable}\n"
            
        details += f"启动时间: {thread_dict['start_time']}\n"
        details += f"最后活动: {thread_dict['last_active']}\n"
        
        if thread_dict['stack_trace']:
            details += f"\n堆栈跟踪:\n{thread_dict['stack_trace']}"
        
        self.detail_text.setText(details)
    
    def show_thread_issue(self, issue_type, details):
        """显示线程问题"""
        print(f"线程问题: {issue_type} - {details}")
        # 添加到系统信息面板
        current_text = self.system_text.toPlainText()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        issue_text = f"[{timestamp}] {issue_type}: {details}\n"
        self.system_text.setText(issue_text + current_text)
    
    def create_test_threads(self):
        """创建测试线程"""
        count = self.test_count_spin.value()
        QMessageBox.information(self, "创建测试线程", f"正在创建 {count} 个测试线程...")
        
        # 使用线程工厂创建测试线程
        thread_ids = self.thread_factory.create_test_threads(count)
        
        QMessageBox.information(self, "测试线程创建完成", f"已创建 {len(thread_ids)} 个测试线程")
        
        # 立即刷新线程列表
        self.refresh_threads()
    
    def scan_modules(self):
        """扫描所有模块，检测线程创建情况"""
        QMessageBox.information(self, "模块扫描", "正在扫描所有模块，查找潜在的线程...")
        
        # 执行扫描
        try:
            # 获取模块目录
            modules_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "modules")
            if os.path.exists(modules_path):
                modules = [d for d in os.listdir(modules_path) if os.path.isdir(os.path.join(modules_path, d))]
                
                # 更新系统信息面板
                current_text = self.system_text.toPlainText()
                module_text = f"发现 {len(modules)} 个模块:\n"
                for mod in modules:
                    module_text += f"- {mod}\n"
                
                self.system_text.setText(module_text + "\n" + current_text)
                
                QMessageBox.information(self, "模块扫描完成", f"发现 {len(modules)} 个模块")
            else:
                QMessageBox.warning(self, "模块扫描失败", f"未找到模块目录: {modules_path}")
        except Exception as e:
            QMessageBox.critical(self, "模块扫描错误", f"扫描模块时出错: {str(e)}")
    
    def register_system_threads(self):
        """注册所有系统线程到线程工厂"""
        QMessageBox.information(self, "注册系统线程", "正在注册系统中的所有线程...")
        
        # 获取系统所有线程
        sys_threads = threading.enumerate()
        registered_count = 0
        
        # 遍历并注册
        for t in sys_threads:
            if t.ident is not None:
                # 检查是否已经注册
                if self.thread_factory.get_system_thread_by_id(t.ident) is None:
                    # 猜测模块
                    module = self.thread_monitor._guess_module_from_thread_name(t.name)
                    # 注册线程
                    if self.thread_factory.register_external_thread(t, module):
                        registered_count += 1
        
        # 立即刷新线程列表
        self.refresh_threads()
        
        QMessageBox.information(self, "注册完成", f"已注册 {registered_count} 个系统线程")
    
    def update_system_info(self):
        """更新系统信息面板"""
        # 获取系统信息
        import platform
        import psutil
        
        try:
            # 获取CPU、内存信息
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            # 获取当前进程信息
            process = psutil.Process()
            process_cpu = process.cpu_percent()
            process_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # 系统信息文本
            system_info = "系统信息:\n"
            system_info += f"系统: {platform.system()} {platform.version()}\n"
            system_info += f"Python: {platform.python_version()}\n"
            system_info += f"CPU使用率: {cpu_percent}%\n"
            system_info += f"内存使用率: {memory.percent}%\n"
            system_info += f"当前进程CPU使用率: {process_cpu}%\n"
            system_info += f"当前进程内存使用: {process_memory:.2f} MB\n\n"
            
            # 线程统计信息
            thread_info = "线程统计:\n"
            thread_info += f"系统线程总数: {len(threading.enumerate())}\n"
            thread_info += f"监控器线程数: {len(self.thread_monitor.get_all_threads())}\n"
            thread_info += f"线程工厂线程数: {len(self.thread_factory.threads)}\n"
            
            # 各模块线程数
            module_threads = {}
            for thread in self.thread_monitor.get_all_threads():
                if thread.module not in module_threads:
                    module_threads[thread.module] = 0
                module_threads[thread.module] += 1
            
            thread_info += "\n模块线程分布:\n"
            for module, count in module_threads.items():
                thread_info += f"- {module}: {count}个线程\n"
            
            # 更新文本
            current_text = self.system_text.toPlainText()
            # 如果当前文本中有"线程问题"，保留这部分
            issue_text = ""
            for line in current_text.split("\n"):
                if "线程问题" in line or "线程卡住" in line or "线程错误" in line:
                    issue_text += line + "\n"
            
            # 组合新文本
            if issue_text:
                self.system_text.setText(system_info + thread_info + "\n问题日志:\n" + issue_text)
            else:
                self.system_text.setText(system_info + thread_info)
        except Exception as e:
            self.system_text.setText(f"获取系统信息时出错: {str(e)}")
    
    def show_help(self):
        """显示帮助信息"""
        help_text = (
            "线程监控器使用说明:\n\n"
            "1. 开始/停止监控: 控制线程监控器的启停\n"
            "2. 刷新间隔: 设置线程状态检查的频率\n"
            "3. 模块筛选: 按模块筛选要显示的线程\n"
            "4. 强制刷新: 手动触发线程检查\n"
            "5. 创建测试线程: 创建指定数量的测试线程\n"
            "6. 扫描所有模块: 检测所有模块中的线程创建情况\n"
            "7. 注册系统线程: 将当前所有系统线程注册到线程工厂\n\n"
            "表格中包含所有线程的基本信息，点击线程行可在下方查看详细信息。"
        )
        QMessageBox.information(self, "帮助", help_text)
    
    def closeEvent(self, event):
        """关闭窗口时停止监控"""
        self.thread_monitor.stop_monitoring()
        event.accept()

# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = ThreadMonitorDialog()
    window.show()
    sys.exit(app.exec_()) 