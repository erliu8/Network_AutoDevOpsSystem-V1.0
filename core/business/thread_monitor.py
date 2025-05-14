# thread_monitor.py
import sys
import threading
import time
import traceback
import os
import inspect
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread, Qt
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTableWidget, QTableWidgetItem,
                            QHeaderView, QMessageBox, QTextEdit, QSplitter,
                            QTabWidget, QComboBox, QCheckBox, QGroupBox)
from PyQt5.QtGui import QColor, QFont

# 导入线程工厂
from core.business.thread_factory import ThreadFactory

# 全局标志，防止递归
_thread_monitor_active = False

class ThreadInfo:
    """线程信息类，存储线程的详细信息"""
    def __init__(self, thread_id, name, alive, daemon, module=None):
        self.thread_id = thread_id
        self.name = name
        self.alive = alive
        self.daemon = daemon
        self.module = module or "未知"
        self.start_time = datetime.now()
        self.last_active = datetime.now()
        self.status = "正常"
        self.stack_trace = ""
    
    def update_activity(self):
        """更新线程活动时间"""
        self.last_active = datetime.now()
    
    def is_stuck(self, timeout_seconds=60):
        """检查线程是否卡住"""
        if not self.alive:
            return False
        
        time_diff = (datetime.now() - self.last_active).total_seconds()
        return time_diff > timeout_seconds
    
    def to_dict(self):
        """将线程信息转换为字典"""
        return {
            "thread_id": self.thread_id,
            "name": self.name,
            "alive": self.alive,
            "daemon": self.daemon,
            "module": self.module,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_active": self.last_active.strftime("%Y-%m-%d %H:%M:%S"),
            "status": self.status,
            "stack_trace": self.stack_trace
        }

class ThreadMonitor(QObject):
    """线程监控类，负责监控系统中的所有线程"""
    
    # 定义信号
    thread_status_updated = pyqtSignal(list)  # 线程状态更新信号
    thread_issue_detected = pyqtSignal(str, str)  # 线程问题检测信号：问题类型, 详细信息
    
    def __init__(self):
        super().__init__()
        self.threads = {}  # 存储线程信息 {thread_id: ThreadInfo}
        self.module_thread_map = {}  # 模块与线程的映射 {module_name: [thread_id, ...]}
        self.monitoring = False
        self.check_interval = 5  # 默认检查间隔（秒）
        self.stuck_threshold = 60  # 默认卡住阈值（秒）
        
        # 初始化定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_threads)
        
        # 初始化模块映射
        self.init_module_mapping()
        
        # 获取线程工厂实例并连接信号
        self.thread_factory = ThreadFactory.get_instance()
        self.thread_factory.thread_created.connect(self.on_thread_created)
        self.thread_factory.thread_started.connect(self.on_thread_started)
        self.thread_factory.thread_finished.connect(self.on_thread_finished)
        self.thread_factory.thread_error.connect(self.on_thread_error)
        
        # 记录监控器自己的线程ID，避免在监控时自递归
        self.monitor_thread_id = threading.current_thread().ident
        print(f"线程监控器的线程ID: {self.monitor_thread_id}")
    
    def init_module_mapping(self):
        """初始化模块名称映射"""
        self.module_name_mapping = {
            "dhcp_configuration": "DHCP配置模块",
            "vpn_deploy": "VPN配置模块",
            "route_configuration": "路由配置模块",
            "Batch_configuration_of_addresses": "批量配置地址模块",
            "network_monitor": "网络监控模块",
            "Query_device_information": "设备信息查询模块",
            "acl_nat_spanning_tree_configuration": "ACL/NAT/生成树配置模块",
            "internet_traffic_monitor": "流量监控模块",
            "Integral_Network_Arrangement": "整体网络编排模块",
            "core.business.monitor_service": "监控服务",
            "core.business.query_service": "查询服务",
            "core.business.thread_monitor": "线程监控服务",
            "core.business.thread_factory": "线程工厂",
            "core.login_window": "登录窗口",
            "core.main_window": "主窗口",
            "core.module_loader": "模块加载器"
        }
    
    def on_thread_created(self, thread_id, name, module):
        """处理线程创建事件"""
        print(f"线程创建: {name} (ID: {thread_id}) - 模块: {module}")
        # 添加到监控列表
        thread_info = ThreadInfo(thread_id, name, True, True, module)
        self.threads[thread_id] = thread_info
        
        # 更新模块线程映射
        if module not in self.module_thread_map:
            self.module_thread_map[module] = []
        self.module_thread_map[module].append(thread_id)
    
    def on_thread_started(self, thread_id):
        """处理线程启动事件"""
        if thread_id in self.threads:
            self.threads[thread_id].update_activity()
            self.threads[thread_id].status = "正常"
    
    def on_thread_finished(self, thread_id):
        """处理线程完成事件"""
        if thread_id in self.threads:
            self.threads[thread_id].alive = False
            self.threads[thread_id].status = "已结束"
    
    def on_thread_error(self, thread_id, error):
        """处理线程错误事件"""
        if thread_id in self.threads:
            self.threads[thread_id].status = "错误"
            self.thread_issue_detected.emit("线程错误", f"线程 {self.threads[thread_id].name} 发生错误: {error}")
    
    def start_monitoring(self, interval=5):
        """
        开始监控线程
        
        参数:
            interval (int): 监控间隔，单位秒
        """
        if self.monitoring:
            return
        
        self.check_interval = interval
        self.monitoring = True
        self.timer.start(interval * 1000)  # 转换为毫秒
        
        # 立即执行一次检查
        self.check_threads()
        
        return True
    
    def stop_monitoring(self):
        """停止监控线程"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        self.timer.stop()
        return True
    
    def set_stuck_threshold(self, seconds):
        """设置线程卡住阈值"""
        self.stuck_threshold = seconds
    
    def check_threads(self):
        """检查所有线程的状态"""
        global _thread_monitor_active
        if _thread_monitor_active:
            print("线程监控器已经在运行中，避免递归")
            return
            
        _thread_monitor_active = True
        try:
            # 获取当前所有线程
            current_threads = threading.enumerate()
            current_thread_ids = {t.ident for t in current_threads if t.ident is not None}
            
            # 打印调试信息
            print(f"当前检测到 {len(current_threads)} 个线程")
            
            # 调试: 查看模块上下文中的所有线程
            self._scan_for_all_modules_threads()
            
            # 输出线程名称，辅助调试
            for t in current_threads:
                print(f"线程名称: {t.name}, ID: {t.ident}, 活动状态: {t.is_alive()}")
                
                # 推导线程所属模块
                module = self._guess_module_from_thread_name(t.name)
                
                # 尝试从堆栈推导模块（如果名称推导不出）
                if not module or module == "未知线程":
                    stack_module = self._guess_module_from_thread_stack(t)
                    if stack_module:
                        module = stack_module
                        
                if module:
                    print(f"  - 推导的模块: {module}")
            
            # 先尝试从线程工厂获取线程
            self._update_from_thread_factory()
            
            # 检查所有Python线程
            self._update_from_python_threads(current_threads)
            
            # 检查是否有线程已经终止，标记为非活动
            thread_ids = list(self.threads.keys())
            for thread_id in thread_ids:
                if thread_id not in current_thread_ids and thread_id != self.monitor_thread_id:
                    if thread_id in self.threads:
                        self.threads[thread_id].alive = False
                        print(f"标记线程为非活动: {self.threads[thread_id].name} (ID: {thread_id})")
            
            # 打印最终结果
            print(f"线程检查完成，监控器中现有 {len(self.threads)} 个线程:")
            for thread_id, thread_info in self.threads.items():
                print(f"- {thread_info.name} (ID: {thread_id}, 模块: {thread_info.module}, 活动: {thread_info.alive})")
            
            # 发送线程状态更新信号
            thread_info_list = [thread.to_dict() for thread in self.threads.values()]
            self.thread_status_updated.emit(thread_info_list)
            
        except Exception as e:
            print(f"检查线程状态时出错: {str(e)}")
            traceback.print_exc()
        finally:
            _thread_monitor_active = False
    
    def _update_from_thread_factory(self):
        """从线程工厂更新线程信息"""
        if not hasattr(self, 'thread_factory') or not self.thread_factory:
            print("线程工厂不可用")
            return
            
        factory_threads = self.thread_factory.threads
        active_factory_threads = self.thread_factory.get_active_threads()
        
        print(f"线程工厂中注册的线程数: {len(factory_threads)}")
        
        # 从线程工厂中获取已注册的线程信息
        for thread_id, thread_info in factory_threads.items():
            thread_obj = active_factory_threads.get(thread_id)
            if thread_obj and thread_obj.ident:
                real_thread_id = thread_obj.ident
                
                # 如果系统线程ID尚未在监控列表中，添加它
                if real_thread_id not in self.threads:
                    module = thread_info.get('module', '未知')
                    
                    # 创建线程信息对象
                    thread_info_obj = ThreadInfo(
                        thread_id=real_thread_id,
                        name=thread_info.get('name', '未命名'),
                        alive=True,
                        daemon=True if thread_obj.daemon else False,
                        module=module
                    )
                    
                    # 添加到监控列表
                    self.threads[real_thread_id] = thread_info_obj
                    print(f"从线程工厂添加线程: {thread_info_obj.name}, ID: {real_thread_id}, 模块: {module}")
                    
                    # 更新模块线程映射
                    if module not in self.module_thread_map:
                        self.module_thread_map[module] = []
                    self.module_thread_map[module].append(real_thread_id)
    
    def _update_from_python_threads(self, current_threads):
        """从Python的threading模块更新线程信息"""
        # 更新线程列表（处理其他未通过线程工厂创建的线程）
        for thread in current_threads:
            thread_id = thread.ident
            if thread_id is None:
                # 为未启动的线程分配一个临时ID
                thread_id = id(thread)
                print(f"为线程 {thread.name} 分配临时ID: {thread_id}")
            
            # 忽略监控器自己的线程，避免递归
            if thread_id == self.monitor_thread_id:
                continue
                
            if thread_id not in self.threads:
                # 如果是新线程，添加到监控列表
                module = self._guess_module_from_thread_name(thread.name)
                
                # 尝试从堆栈推导模块
                stack_module = self._guess_module_from_thread_stack(thread)
                if stack_module:
                    module = stack_module
                
                self.threads[thread_id] = ThreadInfo(
                    thread_id=thread_id,
                    name=thread.name,
                    alive=thread.is_alive(),
                    daemon=thread.daemon,
                    module=module
                )
                
                print(f"添加新线程到监控: {thread.name}, ID: {thread_id}, 模块: {module}")
                
                # 更新模块线程映射
                if module not in self.module_thread_map:
                    self.module_thread_map[module] = []
                self.module_thread_map[module].append(thread_id)
            else:
                # 更新现有线程的状态
                self.threads[thread_id].alive = thread.is_alive()
                self.threads[thread_id].update_activity()
    
    def _scan_for_all_modules_threads(self):
        """扫描所有模块目录，查找可能的线程创建"""
        try:
            # 检查各模块的线程创建情况
            modules_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "modules")
            if os.path.exists(modules_path):
                modules = [d for d in os.listdir(modules_path) if os.path.isdir(os.path.join(modules_path, d))]
                print(f"找到 {len(modules)} 个模块目录: {modules}")
            else:
                print(f"未找到模块目录: {modules_path}")
        except Exception as e:
            print(f"扫描模块目录时出错: {str(e)}")
    
    def _guess_module_from_thread_stack(self, thread):
        """通过检查线程的调用栈推导模块名称"""
        try:
            # 尝试获取线程的堆栈 - 安全方式，避免递归
            thread_id = thread.ident
            if not thread_id:
                return None
                
            # 检查线程帧对象，确定是哪个模块创建的线程
            for module_prefix in self.module_name_mapping.keys():
                # 检查线程名称中是否包含模块名称关键字
                if module_prefix in thread.name:
                    return module_prefix
            
            # 如果是PyQt线程，则归类为GUI
            if "Qt" in thread.name:
                return "qt_gui"
                
            return None
        except Exception:
            # 如果获取堆栈出错，返回None
            return None
    
    def _guess_module_from_thread_name(self, thread_name):
        """根据线程名称猜测所属模块"""
        # 特殊线程名处理
        if thread_name == "MainThread":
            return "core.main_window"
        elif thread_name.startswith("Dummy-"):
            return "dummy"
        elif "Thread-" in thread_name:
            # 通用线程可能来自任何模块，尝试进一步分析
            if "DHCP" in thread_name:
                return "dhcp_configuration"
            elif "VPN" in thread_name:
                return "vpn_deploy"
            elif "Route" in thread_name or "路由" in thread_name:
                return "route_configuration"
            elif "BatchConfig" in thread_name or "批量配置" in thread_name:
                return "Batch_configuration_of_addresses"
            elif "Monitor" in thread_name or "监控" in thread_name:
                return "network_monitor"
            elif "Query" in thread_name or "查询" in thread_name:
                return "Query_device_information"
            elif "ACL" in thread_name or "NAT" in thread_name or "生成树" in thread_name:
                return "acl_nat_spanning_tree_configuration"
            elif "Traffic" in thread_name or "流量" in thread_name:
                return "internet_traffic_monitor"
            elif "Network" in thread_name or "拓扑" in thread_name or "编排" in thread_name:
                return "Integral_Network_Arrangement"
            else:
                return "未知线程"
        # Qt相关线程
        elif "Qt" in thread_name:
            return "qt_gui"
        # 线程池相关线程
        elif "ThreadPool" in thread_name:
            return "core.business.thread_factory"
        # 其他情况，用关键词匹配
        elif "DHCP" in thread_name:
            return "dhcp_configuration"
        elif "VPN" in thread_name:
            return "vpn_deploy"
        elif "Route" in thread_name:
            return "route_configuration"
        elif "BatchConfig" in thread_name:
            return "Batch_configuration_of_addresses"
        elif "Monitor" in thread_name:
            return "network_monitor"
        elif "Query" in thread_name:
            return "Query_device_information"
        elif "ACL" in thread_name or "NAT" in thread_name:
            return "acl_nat_spanning_tree_configuration"
        elif "Traffic" in thread_name:
            return "internet_traffic_monitor"
        elif "Network" in thread_name:
            return "Integral_Network_Arrangement"
        else:
            return "未知"
    
    def _update_stack_traces(self):
        """更新线程的堆栈信息 - 安全版本"""
        try:
            # 一次性获取所有线程的帧
            frames = sys._current_frames()
            
            for thread_id, thread_info in self.threads.items():
                # 跳过已结束的线程
                if not thread_info.alive:
                    continue
                
                # 跳过监控器自己的线程
                if thread_id == self.monitor_thread_id:
                    thread_info.stack_trace = "监控线程 - 不收集堆栈以避免递归"
                    continue
                    
                # 安全获取堆栈
                if thread_id in frames:
                    try:
                        frame = frames[thread_id]
                        # 限制堆栈深度，避免过长的堆栈
                        stack = traceback.format_stack(frame, limit=20)
                        thread_info.stack_trace = ''.join(stack)
                    except Exception as stack_error:
                        print(f"格式化线程 {thread_id} 堆栈时出错: {str(stack_error)}")
                        thread_info.stack_trace = f"获取堆栈时出错: {str(stack_error)}"
                else:
                    thread_info.stack_trace = "此线程无法获取堆栈跟踪（可能已结束或未完全启动）"
        except Exception as e:
            print(f"更新线程堆栈信息时出错: {str(e)}")
            traceback.print_exc()
    
    def _check_thread_issues(self):
        """检查线程问题 - 安全版本"""
        try:
            for thread_id, thread_info in self.threads.items():
                # 检查线程是否卡住
                if thread_info.is_stuck(self.stuck_threshold):
                    thread_info.status = "卡住"
                    self.thread_issue_detected.emit(
                        "线程卡住",
                        f"线程 {thread_info.name} (ID: {thread_id}) 可能已卡住，"
                        f"最后活动时间: {thread_info.last_active.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
        except Exception as e:
            print(f"检查线程问题时出错: {str(e)}")
            traceback.print_exc()

    def get_thread_info(self, thread_id):
        """获取指定线程的信息"""
        return self.threads.get(thread_id)
    
    def get_all_threads(self):
        """获取所有线程的信息"""
        return list(self.threads.values())
    
    def get_module_threads(self, module_name):
        """获取指定模块的所有线程"""
        thread_ids = self.module_thread_map.get(module_name, [])
        return [self.threads.get(tid) for tid in thread_ids if tid in self.threads]
    
    def get_thread_stack_trace(self, thread_id):
        """获取指定线程的堆栈跟踪信息"""
        thread_info = self.threads.get(thread_id)
        if thread_info:
            return thread_info.stack_trace
        return "线程不存在或已终止"

class ThreadMonitorWindow(QWidget):
    """线程监控窗口，用于展示线程监控信息"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("线程监控")
        
        # 创建线程监控器
        self.thread_monitor = ThreadMonitor()
        self.thread_monitor.thread_status_updated.connect(self.update_thread_list)
        self.thread_monitor.thread_issue_detected.connect(self.show_thread_issue)
        
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
        control_layout = QHBoxLayout(control_panel)
        
        # 监控控制
        self.monitor_btn = QPushButton("开始监控")
        self.monitor_btn.clicked.connect(self.toggle_monitoring)
        control_layout.addWidget(self.monitor_btn)
        
        # 刷新间隔
        interval_label = QLabel("刷新间隔:")
        control_layout.addWidget(interval_label)
        
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1秒", "3秒", "5秒", "10秒", "30秒", "60秒"])
        self.interval_combo.setCurrentIndex(2)  # 默认5秒
        self.interval_combo.currentIndexChanged.connect(self.change_interval)
        control_layout.addWidget(self.interval_combo)
        
        # 模块筛选
        module_label = QLabel("模块筛选:")
        control_layout.addWidget(module_label)
        
        self.module_combo = QComboBox()
        self.module_combo.addItem("所有模块", "all")
        for module, name in self.thread_monitor.module_name_mapping.items():
            self.module_combo.addItem(name, module)
        self.module_combo.currentIndexChanged.connect(self.filter_threads)
        control_layout.addWidget(self.module_combo)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_threads)
        control_layout.addWidget(refresh_btn)
        
        control_layout.addStretch()
        
        main_layout.addWidget(control_panel)
        
        # 创建线程列表
        self.thread_table = QTableWidget()
        self.thread_table.setColumnCount(5)
        self.thread_table.setHorizontalHeaderLabels(["线程ID", "线程名称", "状态", "模块", "启动时间"])
        self.thread_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.thread_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.thread_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.thread_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.thread_table.clicked.connect(self.show_thread_details)
        
        main_layout.addWidget(self.thread_table)
        
        # 创建详情面板
        detail_panel = QWidget()
        detail_layout = QVBoxLayout(detail_panel)
        
        detail_label = QLabel("线程详情:")
        detail_layout.addWidget(detail_label)
        
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        detail_layout.addWidget(self.detail_text)
        
        main_layout.addWidget(detail_panel)
        
        # 设置内容比例
        main_layout.setStretch(1, 3)  # 表格占比更大
        main_layout.setStretch(2, 1)  # 详情占比较小
    
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
        
        # 强制再次检查线程状态（增加这一行）
        self.thread_monitor.check_threads()
        threads = [t.to_dict() for t in self.thread_monitor.get_all_threads()]
        
        print(f"过滤前的线程总数: {len(threads)}")
        for t in threads:
            print(f"- 线程: {t['name']} (ID: {t['thread_id']}, 模块: {t['module']})")
            
        # 在筛选前始终显示所有线程（临时调试用，去掉筛选）
        filtered_threads = threads
        
        # 筛选线程
        #if self.current_module != "all":
        #    filtered_threads = [t for t in threads if t["module"] == self.current_module]
        #else:
        #    filtered_threads = threads
        
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
            
        print(f"实际显示的线程数: {len(filtered_threads)}")
    
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
        # 可以在这里添加更多的问题处理逻辑，如弹出警告等
    
    def closeEvent(self, event):
        """关闭窗口时停止监控"""
        self.thread_monitor.stop_monitoring()
        event.accept()