# 在文件开头添加路径配置
import sys
import os
import traceback
import time  # 添加时间模块
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

# 添加虚拟环境路径
venv_path = Path(__file__).parent / "venv" / "Lib" / "site-packages"
if venv_path.exists():
    sys.path.append(str(venv_path))

# main.py
from PyQt5.QtWidgets import (QMainWindow, QAction, QMenu, QToolBar, QTabWidget, 
                            QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                            QStackedWidget, QScrollArea, QFrame, QSizePolicy, QSplitter,
                            QApplication, QMessageBox)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer
from core.module_loader import ModuleLoader
from core.main_window import MainWindow  # 导入正确的窗口类
from core.business.websocket_service import WebSocketService

# 导入线程工厂
from core.business.thread_factory import ThreadFactory

class MainApp(MainWindow):  # 继承包含菜单栏的MainWindow
    modules_loaded = pyqtSignal()  # 在类作用域内定义信号
    
    # 修改 MainApp 类中的相关方法
    
    def __init__(self):
        import threading
        print(f"主窗口线程ID: {threading.current_thread().ident}")
        print(f"主窗口线程名称: {threading.current_thread().name}")
        #主窗口线程ID: 4088
        #主窗口线程名称: MainThread
        try:
            super().__init__()  # 调用父类初始化
            self.setWindowTitle("自动运维平台")
            self.setGeometry(100, 100, 1200, 800)
            
            # 获取线程工厂实例
            self.thread_factory = ThreadFactory.get_instance()
            
            # 初始化模块系统
            print("正在初始化模块系统...")
            self.module_loader = ModuleLoader()
            self.modules_loaded.connect(self._update_modules)
            
            # 延迟加载模块，确保窗口完全初始化后再加载
            QTimer.singleShot(500, self.init_modules)
            
            # 将WebSocket服务初始化移到模块加载完成后
            self.websocket_service = None
            
            # 初始时隐藏主窗口，等待登录成功后显示
            self.hide()
            print("主窗口初始化完成")
            
            # 设置任务队列
            try:
                # 尝试使用基于数据库的任务队列
                from core.business.db_task_queue import get_db_task_queue
                
                # 创建任务队列实例
                self.task_queue = get_db_task_queue()
                
                # 连接任务通知信号
                self.task_queue.task_added.connect(self.on_task_added)
                self.task_queue.task_status_changed.connect(self.on_task_status_changed)
                
                # 启动任务处理和轮询
                self.task_queue.start_processing()
                
                # 注册任务处理程序
                self.register_task_handlers()
                
                print("任务队列已初始化 - 使用数据库模式")
                
                # 立即进行一次轮询，获取最新任务
                self.task_queue.poll_task_status_changes()
                
                # 延迟几秒后检查待处理任务
                QTimer.singleShot(3000, self.check_for_pending_tasks)
            except Exception as e:
                print(f"初始化任务队列失败: {str(e)}")
                import traceback
                traceback.print_exc()
        except Exception as e:
            print(f"主窗口初始化失败: {str(e)}")
            traceback.print_exc()
    
    # 替换原来的 _update_tabs 方法
    def _update_modules(self):
        try:
            self.load_modules()  # 在主线程执行UI更新
            print("模块更新完成")
            
            # 在模块加载完成后初始化WebSocket服务
            self.init_websocket_service()
        except Exception as e:
            print(f"模块更新失败: {str(e)}")
            traceback.print_exc()
    
    # 添加WebSocket服务初始化方法
    def init_websocket_service(self):
        """在模块加载完成后初始化WebSocket服务"""
        try:
            if self.websocket_service is None:
                print("初始化WebSocket服务...")
                self.websocket_service = WebSocketService()
                print("WebSocket服务初始化完成")
        except Exception as e:
            print(f"WebSocket服务初始化失败: {str(e)}")
            traceback.print_exc()
    
    # 替换原来的 load_module_tabs 方法
    def load_modules(self):
        """加载所有模块到左侧导航面板"""
        try:
            # 清空现有导航项
            for i in range(self.nav_layout.count()-1, -1, -1):
                item = self.nav_layout.itemAt(i)
                if item and item.widget():
                    item.widget().deleteLater()
            
            print("开始加载模块...")
            # 只添加通用模块
            self.add_module("通用", self.create_welcome_widget())
            print("已添加通用模块")
            
            # 加载动态模块
            metadata = self.module_loader.get_module_metadata()
            print(f"找到的模块元数据: {metadata}")
            
            # 如果没有找到模块，手动添加已知模块
            if not metadata:
                print("未找到模块元数据，手动添加已知模块")
                self.add_known_modules()
                return
                
            for module_id, meta in metadata.items():
                # 排除已经添加的模块
                if meta.get("name") in {"通用"}:
                    continue
                    
                # PyQt5模块直接加载
                try:
                    print(f"尝试加载模块: {meta['name']}")
                    widget = self.module_loader.get_module_widgets().get(meta["name"])
                    if widget:
                        print(f"添加模块到导航面板: {meta['name']}")
                        self.add_module(meta["name"], widget)
                    else:
                        print(f"模块 {meta['name']} 没有可用的小部件，尝试手动创建")
                        # 尝试手动创建模块小部件
                        self.create_module_widget(meta["name"], module_id)
                except Exception as e:
                    print(f"添加模块 {meta['name']} 失败: {str(e)}")
                    traceback.print_exc()
            
            print(f"成功加载了所有模块")
            
        except Exception as e:
            print(f"加载模块失败: {str(e)}")
            traceback.print_exc()
            # 出错时尝试手动添加已知模块
            self.add_known_modules()
    
    def add_known_modules(self):
        """手动添加已知的模块"""
        print("手动添加已知模块")
        
        # 批量配置地址模块需要特殊处理，因为它需要初始化控制器
        try:
            print("尝试添加批量配置地址模块...")
            from modules.Batch_configuration_of_addresses.Batch_configuration_of_addresses import BatchConfigController
            controller = BatchConfigController()
            
            try:
                from modules.Batch_configuration_of_addresses.gui import BatchConfigWindow
                self.add_module("批量配置地址", BatchConfigWindow(controller))
                print("成功添加批量配置地址模块")
            except Exception as e:
                print(f"添加批量配置地址模块失败 (GUI加载错误): {str(e)}")
                traceback.print_exc()
                # 尝试动态重载模块
                try:
                    import importlib
                    import modules.Batch_configuration_of_addresses.gui as gui_module
                    importlib.reload(gui_module)
                    self.add_module("批量配置地址", gui_module.BatchConfigWindow(controller))
                    print("成功通过重载方式添加批量配置地址模块")
                except Exception as inner_e:
                    print(f"重载模块失败: {str(inner_e)}")
                    traceback.print_exc()
                
        except Exception as e:
            print(f"添加批量配置地址模块失败 (控制器加载错误): {str(e)}")
            traceback.print_exc()
        
        # 加载其他模块
        modules_to_add = [
            ("DHCP配置", "modules.dhcp_configuration.gui", "DHCPConfigWindow"), 
            ("VPN配置", "modules.vpn_deploy.gui", "VPNConfigApp"),
            ("路由配置", "modules.route_configuration.gui", "RouteConfigWindow"),
            ("网络监控", "modules.network_monitor.gui", "AutoMaintainGUI"),
            ("设备信息查询", "modules.Query_device_information.gui", "DeviceInfoQueryWindow"),
            ("ACL/NAT/生成树配置", "modules.acl_nat_spanning_tree_configuration.gui", "ConfigurationWindow"),
            ("流量监控", "modules.internet_traffic_monitor.gui", "TrafficMonitorApp")
        ]
        
        # 加载其他模块
        for module_name, module_path, class_name in modules_to_add:
            try:
                print(f"尝试添加{module_name}模块...")
                # 动态导入模块
                module = __import__(module_path, fromlist=[class_name])
                # 获取类
                widget_class = getattr(module, class_name)
                # 实例化添加
                self.add_module(module_name, widget_class())
                print(f"成功添加{module_name}模块")
            except Exception as e:
                print(f"添加{module_name}模块失败: {str(e)}")
                traceback.print_exc()

    def create_module_widget(self, module_name, module_id):
        """尝试为模块创建小部件"""
        try:
            # 根据模块名称尝试导入对应的GUI类
            if "DHCP" in module_name:
                from modules.dhcp_configuration.gui import DHCPConfigWindow
                self.add_module(module_name, DHCPConfigWindow())
            elif "VPN" in module_name:
                from modules.vpn_deploy.gui import VPNConfigApp
                self.add_module(module_name, VPNConfigApp())
            elif "路由" in module_name:
                from modules.route_configuration.gui import RouteConfigWindow
                self.add_module(module_name, RouteConfigWindow())
            elif "批量配置" in module_name:
                from modules.Batch_configuration_of_addresses.gui import BatchConfigWindow
                from modules.Batch_configuration_of_addresses.Batch_configuration_of_addresses import BatchConfigController
                controller = BatchConfigController()
                self.add_module(module_name, BatchConfigWindow(controller))
            elif "网络监控" in module_name:
                from modules.network_monitor.gui import AutoMaintainGUI
                self.add_module(module_name, AutoMaintainGUI())
            elif "设备信息" in module_name:
                from modules.Query_device_information.gui import DeviceInfoQueryWindow
                self.add_module(module_name, DeviceInfoQueryWindow())
            elif "ACL" in module_name or "NAT" in module_name:
                from modules.acl_nat_spanning_tree_configuration.gui import ConfigurationWindow
                self.add_module(module_name, ConfigurationWindow())
            elif "流量" in module_name:
                from modules.internet_traffic_monitor.gui import TrafficMonitorApp
                self.add_module(module_name, TrafficMonitorApp())
            else:
                # 如果无法确定模块类型，创建一个空白页面
                self.add_module(module_name, self.create_empty_widget(module_name))
        except Exception as e:
            print(f"为模块 {module_name} 创建小部件失败: {str(e)}")
            traceback.print_exc()
            # 创建一个空白页面作为后备
            self.add_module(module_name, self.create_empty_widget(module_name))

    def create_welcome_widget(self):
        """创建欢迎页面"""
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        welcome_label = QLabel("欢迎使用自动运维平台")
        welcome_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(welcome_label)
        return welcome_widget
    
    def create_empty_widget(self, title):
        """创建空白页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(f"{title} - 功能开发中...")
        label.setStyleSheet("font-size: 18px; color: #666;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        return widget
    
    def add_menu_action(self, menu, text, slot=None, shortcut=None, icon=None):
        """添加菜单项"""
        action = QAction(text, self)
        if icon:
            action.setIcon(QIcon(icon))
        if shortcut:
            action.setShortcut(shortcut)
        if slot:
            action.triggered.connect(slot)
        menu.addAction(action)
        return action
    
    def add_modules_to_tools_menu(self):
        """添加模块到工具菜单"""
        try:
            # 确保创建了工具菜单
            tools_menu = self.menuBar().findChild(QMenu, "toolsMenu")
            if not tools_menu:
                tools_menu = self.menuBar().addMenu("工具")
                tools_menu.setObjectName("toolsMenu")
            
            # 添加网络设备监控
            self.add_menu_action(tools_menu, "网络设备监控", self.show_device_status)
            
            # 添加批量配置地址
            self.add_menu_action(tools_menu, "批量配置地址", self.show_batch_config)
            
            # 添加流量监控
            self.add_menu_action(tools_menu, "流量监控", self.open_traffic_monitor)
            
            # 添加VPN配置
            self.add_menu_action(tools_menu, "VPN配置", self.open_vpn_config)
            
            # 添加任务审批窗口
            self.add_menu_action(tools_menu, "任务审批管理", self.open_approval_window)
            
            # 添加线程监控
            self.add_menu_action(tools_menu, "线程监控", self.open_thread_monitor)
        except Exception as e:
            print(f"添加工具菜单失败: {str(e)}")
            traceback.print_exc()
    
    def open_network_arrangement(self):
        """打开网络部署工具"""
        try:
            # 先检查模块是否已加载
            for i in range(self.nav_layout.count()):
                button = self.nav_layout.itemAt(i).widget()
                if button and button.text() == "网络部署":
                    button.click()
                    return
                    
            # 如果没有找到，尝试加载模块
            from modules.network_arrangement.gui import NetworkArrangementApp
            self.add_module("网络部署", NetworkArrangementApp())
        except Exception as e:
            QMessageBox.warning(self, "警告", f"无法加载网络部署模块: {str(e)}")
    
    def show_device_query(self):
        """打开设备信息查询工具"""
        try:
            # 先检查模块是否已加载
            for i in range(self.nav_layout.count()):
                button = self.nav_layout.itemAt(i).widget()
                if button and button.text() == "设备信息查询":
                    button.click()
                    return
                    
            # 如果没有找到，尝试加载模块
            from modules.Query_device_information.gui import DeviceInfoQueryWindow
            self.add_module("设备信息查询", DeviceInfoQueryWindow())
        except Exception as e:
            QMessageBox.warning(self, "警告", f"无法加载设备信息查询模块: {str(e)}")
    
    def open_traffic_monitor(self):
        """打开流量监控工具"""
        try:
            # 先检查模块是否已加载
            for i in range(self.nav_layout.count()):
                button = self.nav_layout.itemAt(i).widget()
                if button and button.text() == "流量监控":
                    button.click()
                    return
                    
            # 如果没有找到，尝试加载模块
            from modules.internet_traffic_monitor.gui import TrafficMonitorApp
            self.add_module("流量监控", TrafficMonitorApp())
        except Exception as e:
            QMessageBox.warning(self, "警告", f"无法加载流量监控模块: {str(e)}")
    
    def open_vpn_config(self):
        """打开VPN配置工具"""
        try:
            # 先检查模块是否已加载
            for i in range(self.nav_layout.count()):
                button = self.nav_layout.itemAt(i).widget()
                if button and button.text() == "VPN配置":
                    button.click()
                    return
                    
            # 如果没有找到，尝试加载模块
            from modules.vpn_deploy.gui import VPNConfigApp
            self.add_module("VPN配置", VPNConfigApp())
        except Exception as e:
            QMessageBox.warning(self, "警告", f"无法加载VPN配置模块: {str(e)}")
    
    def open_thread_monitor(self):
        """打开线程监控工具"""
        try:
            print(f"打开线程监控对话框")
            print(f"当前线程工厂ID: {id(self.thread_factory)}")
            print(f"当前线程工厂中的线程数: {self.thread_factory.get_thread_count()}")
            
            # 打开线程监控对话框
            from core.thread_monitor import ThreadMonitorDialog
            monitor = ThreadMonitorDialog(self.thread_factory, self)
            monitor.exec_()
        except Exception as e:
            QMessageBox.warning(self, "警告", f"无法打开线程监控: {str(e)}")
            traceback.print_exc()
            
    def create_test_threads(self):
        """创建测试线程用于测试线程监控功能"""
        try:
            # 创建不同类型的测试线程
            modules = [
                "dhcp_configuration", 
                "vpn_deploy", 
                "route_configuration",
                "Batch_configuration_of_addresses", 
                "network_monitor"
            ]
            
            print("正在创建测试线程...")
            
            # 创建测试线程
            for i, module in enumerate(modules):
                thread_name = f"{module.capitalize()}_TestThread_{i+1}"
                thread_id = self.thread_factory.start_thread(
                    target=self._test_thread_function,
                    args=(thread_name, i+1),
                    name=thread_name,
                    daemon=True,
                    module=module
                )
                print(f"启动测试线程: {thread_name}, ID: {thread_id}, 线程工厂: {id(self.thread_factory)}")
            
            print("测试线程创建完成")
            
            # 打印当前所有线程
            import threading
            threads = threading.enumerate()
            print(f"\n当前Python线程数: {len(threads)}")
            for t in threads:
                print(f"- {t.name} (ID: {t.ident})")
            
            # 打印线程工厂中的线程
            print("\n线程工厂注册的线程:")
            for thread_id, info in self.thread_factory.threads.items():
                print(f"- {info['name']} (ID: {thread_id}, 模块: {info['module']})")
                
        except Exception as e:
            print(f"创建测试线程失败: {str(e)}")
            traceback.print_exc()
            
    def _test_thread_function(self, name, sleep_time):
        """测试线程函数"""
        try:
            import threading
            print(f"测试线程 {name} 启动, 休眠时间: {sleep_time}秒")
            thread_id = threading.current_thread().ident
            print(f"线程 {name} 的系统ID: {thread_id}")
            
            # 模拟线程工作
            for i in range(20):
                print(f"线程 {name} 正在工作: {i+1}/20")
                time.sleep(sleep_time)
            print(f"测试线程 {name} 完成工作")
        except Exception as e:
            print(f"测试线程 {name} 发生错误: {str(e)}")
            traceback.print_exc()
    
    def init_modules(self):
        """初始化模块"""
        try:
            # 在主线程加载模块
            print("开始加载模块...")
            self.module_loader.load_all_modules()
            print("模块加载完成")
            
            # 尝试添加工具菜单
            print("正在添加工具菜单...")
            self.add_modules_to_tools_menu()
            print("工具菜单添加完成")
                
            # 发送模块加载完成信号
            self.modules_loaded.emit()
        except Exception as e:
            print(f"初始化模块失败: {str(e)}")
            traceback.print_exc()
            # 出错时依然触发信号，让UI更新进行手动加载
            self.modules_loaded.emit()
    
    def _load_modules(self):
        """在线程中加载模块"""
        try:
            self.module_loader.load_all_modules()
            return True
        except Exception as e:
            print(f"加载模块失败: {str(e)}")
            traceback.print_exc()
            return False
    
    def show_device_status(self):
        """打开设备状态监控工具"""
        try:
            # 先检查模块是否已加载
            for i in range(self.nav_layout.count()):
                button = self.nav_layout.itemAt(i).widget()
                if button and button.text() == "网络监控":
                    button.click()
                    return
                    
            # 如果没有找到，尝试加载模块
            from modules.network_monitor.gui import AutoMaintainGUI
            self.add_module("网络监控", AutoMaintainGUI())
        except Exception as e:
            QMessageBox.warning(self, "警告", f"无法加载网络监控模块: {str(e)}")
    
    def show_batch_config(self):
        """打开批量配置地址工具"""
        try:
            # 先检查模块是否已加载
            for i in range(self.nav_layout.count()):
                button = self.nav_layout.itemAt(i).widget()
                if button and button.text() == "批量配置地址":
                    button.click()
                    return
                    
            # 如果没有找到，尝试加载模块
            from modules.Batch_configuration_of_addresses.gui import BatchConfigWindow
            from modules.Batch_configuration_of_addresses.Batch_configuration_of_addresses import BatchConfigController
            controller = BatchConfigController()
            self.add_module("批量配置地址", BatchConfigWindow(controller))
        except Exception as e:
            QMessageBox.warning(self, "警告", f"无法加载批量配置地址模块: {str(e)}")
    
    def show(self):
        """显示主窗口"""
        super().show()
        
        # 设置更频繁的任务检查计时器
        self.task_check_timer = QTimer(self)
        self.task_check_timer.timeout.connect(self.check_for_pending_tasks)
        self.task_check_timer.start(10000)  # 每10秒检查一次任务
        print("已启动任务检查计时器，每10秒检查一次")
        
        # 立即进行一次任务检查
        QTimer.singleShot(2000, self.check_for_pending_tasks)
        
        # 检查WebSocket服务是否已初始化
        if hasattr(self, 'websocket_service') and self.websocket_service is not None:
            try:
                self.websocket_service.start()
                print("WebSocket服务已启动")
            except Exception as e:
                print(f"启动WebSocket服务失败: {str(e)}")
                traceback.print_exc()
        else:
            print("WebSocket服务未初始化，跳过启动")
        
        # 启动设备监控
        from core.business.monitor_service import MonitorService
        self.monitor_service = MonitorService()
        self.monitor_service.start_device_monitoring(interval=60)  # 每60秒检查一次设备状态
        print("设备监控服务已启动")
    
    def closeEvent(self, event):
        """应用程序关闭事件处理"""
        try:
            # 关闭WebSocket服务
            if hasattr(self, 'websocket_service') and self.websocket_service is not None:
                print("正在关闭WebSocket服务...")
                self.websocket_service.stop()
                
            # 调用父类的closeEvent
            super().closeEvent(event)
        except Exception as e:
            print(f"关闭应用程序时出错: {str(e)}")
            traceback.print_exc()

    def on_task_added(self, task):
        """任务添加通知回调
        
        Args:
            task: 任务对象
        """
        print(f"[INFO] 收到新任务通知: {task.task_id} (类型: {task.task_type}, 状态: {task.status})")
        # 不再自动打开审批窗口，由用户手动点击菜单打开
                
    def on_task_status_changed(self, task, old_status, new_status):
        """任务状态变化通知回调
        
        Args:
            task: 任务对象
            old_status: 旧状态
            new_status: 新状态
        """
        print(f"[INFO] 任务状态变化: {task.task_id} 从 {old_status} 变为 {new_status}")
        
        # 不再自动打开审批窗口，由用户手动点击菜单打开
        
        # 如果任务完成或失败，添加日志但不显示弹窗
        if new_status in ["completed", "failed"]:
            status_text = "完成" if new_status == "completed" else "失败"
            error_msg = f"\n错误: {task.error}" if task.error else ""
            print(f"[INFO] 任务 {task.task_id} 已{status_text}: 类型={task.task_type}{error_msg}")

    def open_approval_window(self):
        """打开任务审批窗口"""
        try:
            # 尝试导入任务审批窗口
            from modules.final_approval.gui import ApprovalWindow
            
            # 创建审批窗口
            approval_window = ApprovalWindow()
            
            # 显示窗口
            approval_window.show()
            
            # 保存窗口引用，防止垃圾回收
            if not hasattr(self, '_approval_windows'):
                self._approval_windows = []
            self._approval_windows.append(approval_window)
            
            print("已打开任务审批窗口")
            
        except Exception as e:
            print(f"打开任务审批窗口失败: {str(e)}")
            import traceback
            traceback.print_exc()
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "错误",
                f"打开任务审批窗口失败: {str(e)}"
            )

    def register_task_handlers(self):
        """注册任务处理程序"""
        try:
            # 注册DHCP配置任务处理程序
            if hasattr(self.task_queue, 'register_handler'):
                # 创建处理函数适配器
                def handle_dhcp_config_task(params):
                    """处理DHCP配置任务
                    
                    Args:
                        params: 任务参数
                        
                    Returns:
                        dict: 处理结果
                    """
                    print(f"[INFO] MainApp处理DHCP配置任务: {params}")
                    
                    try:
                        # 这里需要执行实际的DHCP配置命令
                        print(f"[DEBUG] 开始在设备上执行DHCP配置命令")
                        
                        # 获取设备ID列表
                        device_ids = params.get('device_ids', [])
                        if not device_ids:
                            return {
                                "status": "error",
                                "message": "未指定设备ID"
                            }
                            
                        # 从数据库获取设备信息
                        from core.repositories.device_repository import DeviceRepository
                        device_repo = DeviceRepository()
                        
                        device_results = []
                        for device_id in device_ids:
                            try:
                                device = device_repo.get_device_by_id(device_id)
                                if not device:
                                    device_results.append({
                                        "device_id": device_id,
                                        "status": "error",
                                        "message": f"未找到设备 ID: {device_id}"
                                    })
                                    continue
                                    
                                # 构建并执行DHCP配置命令
                                device_ip = device.get('ip')
                                print(f"[INFO] 在设备 {device_ip} 上配置DHCP...")
                                
                                # 构建DHCP配置命令
                                pool_name = params.get('pool_name')
                                network = params.get('network')
                                mask = params.get('mask')
                                
                                # 执行配置命令
                                from core.device_ops.config import ConfigManager
                                config_mgr = ConfigManager()
                                
                                # 这里传入实际的设备命令
                                commands = [
                                    f"dhcp enable",
                                    f"ip dhcp pool {pool_name}",
                                    f"network {network} {mask}",
                                ]
                                
                                if params.get('gateway'):
                                    commands.append(f"gateway-list {params.get('gateway')}")
                                if params.get('dns'):
                                    commands.append(f"dns-list {params.get('dns')}")
                                if params.get('domain'):
                                    commands.append(f"domain-name {params.get('domain')}")
                                if params.get('lease_days'):
                                    commands.append(f"lease day {params.get('lease_days')}")
                                
                                # 执行命令并获取结果
                                result = config_mgr.execute_config(device, commands)
                                
                                device_results.append({
                                    "device_id": device_id,
                                    "status": "success" if result.get("success") else "error",
                                    "message": result.get("output", ""),
                                    "error": result.get("error")
                                })
                                
                                print(f"[INFO] 设备 {device_ip} DHCP配置完成")
                                
                            except Exception as device_err:
                                print(f"[ERROR] 设备 {device_id} 配置失败: {str(device_err)}")
                                device_results.append({
                                    "device_id": device_id,
                                    "status": "error",
                                    "message": f"配置出错: {str(device_err)}"
                                })
                        
                        return {
                            "status": "success",
                            "message": "DHCP配置任务已处理",
                            "device_results": device_results
                        }
                    except Exception as e:
                        print(f"[ERROR] 处理DHCP配置任务失败: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        return {
                            "status": "error",
                            "error": str(e)
                        }
                
                # 注册处理函数
                self.task_queue.register_handler("dhcp_config", handle_dhcp_config_task)
                print("[INFO] 已注册DHCP配置任务处理程序")
                
        except Exception as e:
            print(f"[ERROR] 注册任务处理程序失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def check_for_pending_tasks(self):
        """检查是否有待处理的任务"""
        # 如果未初始化任务队列，则不检查
        if not hasattr(self, 'task_queue'):
            print("[WARNING] 任务队列未初始化，无法检查待处理任务")
            return
        
        try:
            print("\n[DEBUG] 开始检查待处理任务...")
            
            # 强制主动轮询，获取最新任务
            if hasattr(self.task_queue, 'poll_task_status_changes'):
                print("[DEBUG] 主动调用轮询获取最新任务状态...")
                # 调用轮询任务状态变化方法
                self.task_queue.poll_task_status_changes()
            else:
                print("[WARNING] 任务队列没有poll_task_status_changes方法")
                return
            
            # 获取所有任务
            tasks = self.task_queue.get_all_tasks()
            
            if not tasks:
                print("[DEBUG] 没有找到任何任务")
                return
                
            print(f"[DEBUG] 获取到 {len(tasks)} 个任务")
            
            # 统计任务状态
            status_counts = {}
            for task in tasks:
                status = task.status
                if status not in status_counts:
                    status_counts[status] = 0
                status_counts[status] += 1
                
            # 打印统计信息
            print("[DEBUG] 任务状态统计:")
            for status, count in status_counts.items():
                print(f"  [DEBUG] - {status}: {count} 个任务")
            
            # 检查是否有待审核的任务
            pending_approval_tasks = [task for task in tasks if task.status == "pending_approval"]
            approved_tasks = [task for task in tasks if task.status == "approved"]
            new_tasks = [task for task in tasks if task.status == "pending"]
            
            # 输出任务分类信息
            if pending_approval_tasks:
                print(f"[INFO] 发现 {len(pending_approval_tasks)} 个待审核任务:")
                for task in pending_approval_tasks:
                    print(f"  [INFO] - 任务ID: {task.task_id}, 类型: {task.task_type}")
            
            if approved_tasks:
                print(f"[INFO] 发现 {len(approved_tasks)} 个已批准任务:")
                for task in approved_tasks:
                    print(f"  [INFO] - 任务ID: {task.task_id}, 类型: {task.task_type}")
            
            if new_tasks:
                print(f"[INFO] 发现 {len(new_tasks)} 个新添加任务:")
                for task in new_tasks:
                    print(f"  [INFO] - 任务ID: {task.task_id}, 类型: {task.task_type}")
            
            # 不再自动打开审批窗口，由用户手动打开
            print("[DEBUG] 检查待处理任务完成\n")
                
        except Exception as e:
            print(f"[ERROR] 检查待处理任务时出错: {str(e)}")
            import traceback
            traceback.print_exc()

# 添加全局异常处理
def exception_hook(exctype, value, traceback_obj):
    """全局异常处理器"""
    import traceback
    traceback_str = ''.join(traceback.format_exception(exctype, value, traceback_obj))
    print(f"未捕获的异常: {traceback_str}")
    # 可以在这里添加日志记录或其他处理
    sys.__excepthook__(exctype, value, traceback_obj)

def main():
    """主函数"""
    # 设置全局异常处理
    sys.excepthook = exception_hook
    
    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("自动运维平台")
    app.setStyle("Fusion")  # 使用Fusion风格
    
    # 创建并显示主窗口
    main_app = MainApp()
    main_app.show()
    
    # 启动应用
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
