# thread_factory.py
import threading
import time
import uuid
import inspect
import sys
import os
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

class ThreadFactory(QObject):
    """
    线程工厂类，负责创建和管理线程
    使用单例模式确保全局唯一实例
    """
    # 定义信号
    thread_created = pyqtSignal(str, str, str)  # 线程ID, 线程名称, 模块名称
    thread_started = pyqtSignal(str)  # 线程ID
    thread_finished = pyqtSignal(str)  # 线程ID
    thread_error = pyqtSignal(str, str)  # 线程ID, 错误信息
    thread_registered = pyqtSignal(str, str, str)  # 线程ID, 线程名称, 模块名称
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """获取线程工厂单例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = ThreadFactory()
        return cls._instance
    
    def __init__(self):
        super().__init__()
        self.threads = {}  # 存储线程信息 {thread_id: thread_info}
        self.active_threads = {}  # 存储活动线程 {thread_id: thread}
        self.system_thread_map = {}  # 系统线程ID到自定义ID的映射 {sys_thread_id: thread_id}
        self._thread_lock = threading.Lock()  # 线程字典的锁
        self.module_patterns = self._initialize_module_patterns()
        
        # 初始化扫描计时器
        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self.scan_for_threads)
        
        # 自动开始扫描
        self.start_scanning()
    
    def _initialize_module_patterns(self):
        """初始化模块名称匹配模式"""
        return {
            "dhcp_configuration": ["dhcp", "DHCP"],
            "vpn_deploy": ["vpn", "VPN"],
            "route_configuration": ["route", "路由"],
            "Batch_configuration_of_addresses": ["batch", "batchconfig", "批量配置"],
            "network_monitor": ["monitor", "监控"],
            "Query_device_information": ["query", "查询"],
            "acl_nat_spanning_tree_configuration": ["acl", "nat", "spanning", "生成树"],
            "internet_traffic_monitor": ["traffic", "流量"],
            "Integral_Network_Arrangement": ["network", "拓扑", "编排"],
            "core.business.monitor_service": ["monitor", "监控"],
            "core.business.query_service": ["query", "查询"],
            "core.business.thread_monitor": ["thread", "线程"],
            "core.business.thread_factory": ["factory", "工厂"],
            "core.login_window": ["login", "登录"],
            "core.main_window": ["main", "主窗口"],
            "core.module_loader": ["module", "模块"]
        }
    
    def start_thread(self, target, args=(), kwargs=None, name=None, daemon=True, module="未知"):
        """
        创建并启动线程
        
        参数:
            target: 线程目标函数
            args: 位置参数
            kwargs: 关键字参数
            name: 线程名称
            daemon: 是否为守护线程
            module: 所属模块名称
            
        返回:
            thread_id: 线程ID
        """
        if kwargs is None:
            kwargs = {}
            
        # 生成唯一线程ID
        thread_id = str(uuid.uuid4())
        
        # 生成线程名称
        if name is None:
            # 使用调用者的模块名作为线程名称前缀
            caller_frame = inspect.currentframe().f_back
            if caller_frame:
                caller_module = inspect.getmodule(caller_frame)
                if caller_module:
                    module_name = caller_module.__name__.split('.')[-1]
                    name = f"{module_name}-Thread-{thread_id[:8]}"
                else:
                    name = f"Thread-{thread_id[:8]}"
            else:
                name = f"Thread-{thread_id[:8]}"
            
            # 如果未指定模块，尝试从调用栈推断
            if module == "未知":
                module = self._guess_module_from_call_stack()
        
        # 包装目标函数，添加异常处理和完成通知
        def thread_wrapper():
            try:
                # 获取真实线程ID并添加映射
                real_thread_id = threading.current_thread().ident
                with self._thread_lock:
                    self.system_thread_map[real_thread_id] = thread_id
                
                # 记录线程开始
                print(f"[DEBUG-THREAD] 线程 {name} (ID: {thread_id}) 开始执行，时间: {datetime.now().strftime('%H:%M:%S')}")
                self.thread_started.emit(thread_id)
                
                # 执行目标函数
                print(f"[DEBUG-THREAD] 线程 {name} 调用目标函数")
                result = target(*args, **kwargs)
                
                print(f"[DEBUG-THREAD] 线程 {name} 目标函数执行完成，返回: {result}")
                return result
            except Exception as e:
                # 发送错误信号
                print(f"[DEBUG-THREAD] 线程 {name} 执行出错: {str(e)}")
                self.thread_error.emit(thread_id, str(e))
                import traceback
                print(f"线程 {name} 执行出错: {str(e)}")
                print(traceback.format_exc())
            finally:
                # 记录线程完成
                print(f"[DEBUG-THREAD] 线程 {name} (ID: {thread_id}) 执行结束，正在清理，时间: {datetime.now().strftime('%H:%M:%S')}")
                self.thread_finished.emit(thread_id)
                # 从活动线程中移除
                with self._thread_lock:
                    if thread_id in self.active_threads:
                        del self.active_threads[thread_id]
                        print(f"[DEBUG-THREAD] 线程 {name} 已从活动线程中移除")
                    # 从系统线程映射中移除
                    real_thread_id = threading.current_thread().ident
                    if real_thread_id in self.system_thread_map:
                        del self.system_thread_map[real_thread_id]
                        print(f"[DEBUG-THREAD] 线程 {name} 系统ID映射已清理")
        
        # 创建线程
        thread = threading.Thread(target=thread_wrapper, name=name, daemon=daemon)
        
        # 存储线程信息
        thread_info = {
            "id": thread_id,
            "name": name,
            "module": module,
            "created_at": datetime.now(),
            "status": "created"
        }
        
        with self._thread_lock:
            self.threads[thread_id] = thread_info
            self.active_threads[thread_id] = thread
        
        # 发送线程创建信号
        self.thread_created.emit(thread_id, name, module)
        
        # 启动线程
        thread.start()
        
        return thread_id
    
    def start_scanning(self, interval=10):
        """开始定期扫描线程"""
        self.scan_timer.start(interval * 1000)  # 转换为毫秒
    
    def stop_scanning(self):
        """停止定期扫描线程"""
        self.scan_timer.stop()
    
    def scan_for_threads(self):
        """扫描已存在的线程并注册到工厂"""
        # 先获取所有当前线程
        current_threads = threading.enumerate()
        
        print(f"正在扫描线程，当前系统中有 {len(current_threads)} 个线程")
        
        # 跳过已注册的线程
        registered_sys_ids = list(self.system_thread_map.keys())
        
        # 查找未注册的线程
        for thread in current_threads:
            # 跳过没有线程ID的线程（未启动的线程）
            if thread.ident is None:
                continue
                
            # 如果这个线程已经注册，跳过
            if thread.ident in registered_sys_ids:
                continue
                
            # 判断线程类型
            if thread.name == "MainThread":
                # 主线程单独处理
                self.register_main_thread(thread)
            elif any(qt_term in thread.name for qt_term in ["PyQt", "Qt", "Dummy"]):
                # PyQt相关线程
                self.register_qt_thread(thread)
            else:
                # 其他线程
                module = self._guess_module_from_thread_name(thread.name)
                self.register_external_thread(thread, module)
        
        # 输出当前注册的线程信息
        print(f"线程工厂中注册的线程数: {len(self.threads)}")
        for thread_id, info in self.threads.items():
            thread_obj = self.active_threads.get(thread_id)
            sys_id = thread_obj.ident if thread_obj else "未知"
            print(f"- 工厂线程: {info['name']} (ID: {thread_id}, 系统ID: {sys_id}, 模块: {info['module']})")
        
        # 检查不再存在的线程
        current_sys_thread_ids = [t.ident for t in current_threads if t.ident is not None]
        for sys_thread_id, thread_id in list(self.system_thread_map.items()):
            if sys_thread_id not in current_sys_thread_ids:
                # 线程已经结束，标记为完成
                if thread_id in self.threads:
                    print(f"线程 {self.threads[thread_id]['name']} (ID: {thread_id}) 已结束，清理记录")
                    # 发送线程完成信号
                    self.thread_finished.emit(thread_id)
                    # 从活动线程中移除
                    with self._thread_lock:
                        if thread_id in self.active_threads:
                            del self.active_threads[thread_id]
                        if sys_thread_id in self.system_thread_map:
                            del self.system_thread_map[sys_thread_id]
    
    def register_main_thread(self, thread):
        """注册主线程"""
        self.register_external_thread(thread, "core.main_window")
    
    def register_qt_thread(self, thread):
        """注册Qt线程"""
        self.register_external_thread(thread, "qt_gui")
    
    def register_external_thread(self, thread, module=None):
        """
        注册外部创建的线程到工厂
        
        参数:
            thread: 线程对象
            module: 模块名称，如果不提供则尝试推断
        """
        if thread.ident is None:
            print(f"尝试注册未启动的线程 {thread.name}，跳过")
            return False
            
        # 如果这个线程已经注册过，直接返回
        with self._thread_lock:
            if thread.ident in self.system_thread_map:
                thread_id = self.system_thread_map[thread.ident]
                print(f"线程 {thread.name} (ID: {thread.ident}) 已注册，ID: {thread_id}")
                return True
        
        # 如果没有提供模块名，尝试推断
        if not module:
            module = self._guess_module_from_thread_name(thread.name)
            print(f"为线程 {thread.name} 推断的模块: {module}")
        
        # 生成唯一线程ID
        thread_id = str(uuid.uuid4())
        
        # 存储线程信息
        thread_info = {
            "id": thread_id,
            "name": thread.name,
            "module": module,
            "created_at": datetime.now(),
            "status": "active",  # 直接标记为活动
            "external": True  # 标记为外部线程
        }
        
        # 添加到线程管理器
        with self._thread_lock:
            self.threads[thread_id] = thread_info
            self.active_threads[thread_id] = thread
            self.system_thread_map[thread.ident] = thread_id
        
        print(f"成功注册外部线程: {thread.name} (系统ID: {thread.ident}, 工厂ID: {thread_id}, 模块: {module})")
        
        # 发送线程注册信号
        self.thread_registered.emit(thread_id, thread.name, module)
        
        return True
    
    def _guess_module_from_call_stack(self):
        """从调用栈推断所属模块"""
        try:
            # 获取调用栈
            stack = inspect.stack()
            
            # 查找非工厂类的调用者
            for frame_info in stack[2:]:  # 跳过自身和直接调用者
                module = inspect.getmodule(frame_info.frame)
                if module:
                    module_name = module.__name__
                    
                    # 跳过标准库
                    if module_name.startswith(('threading', 'PyQt5', '__main__')):
                        continue
                        
                    # 查找匹配的模块
                    for mod_key, patterns in self.module_patterns.items():
                        for part in module_name.split('.'):
                            if any(pattern.lower() in part.lower() for pattern in patterns):
                                return mod_key
                                
                    # 如果找不到精确匹配，返回模块名
                    return module_name
                    
            # 默认返回未知
            return "未知"
        except Exception:
            return "未知"
    
    def _guess_module_from_thread_name(self, thread_name):
        """从线程名称推断所属模块"""
        # 特殊线程名处理
        if thread_name == "MainThread":
            return "core.main_window"
        elif thread_name.startswith("Dummy-"):
            return "dummy"
            
        # 根据模块模式匹配
        for mod_key, patterns in self.module_patterns.items():
            if any(pattern.lower() in thread_name.lower() for pattern in patterns):
                return mod_key
                
        # Qt相关线程
        if "Qt" in thread_name or "PyQt" in thread_name:
            return "qt_gui"
        # 线程池相关线程
        elif "ThreadPool" in thread_name:
            return "core.business.thread_factory"
        # 无法推断
        else:
            return "未知"
    
    def get_thread_info(self, thread_id):
        """获取线程信息"""
        with self._thread_lock:
            return self.threads.get(thread_id)
    
    def get_active_threads(self):
        """获取所有活动线程"""
        with self._thread_lock:
            return self.active_threads.copy()
    
    def get_thread_count(self):
        """获取活动线程数量"""
        with self._thread_lock:
            return len(self.active_threads)
    
    def get_threads_by_module(self, module):
        """获取指定模块的所有线程"""
        with self._thread_lock:
            return {tid: info for tid, info in self.threads.items() 
                    if info["module"] == module and tid in self.active_threads}
    
    def stop_all_threads(self):
        """停止所有线程（注意：这只是标记，无法强制停止Python线程）"""
        with self._thread_lock:
            for thread_id, thread in list(self.active_threads.items()):
                if thread_id in self.threads:
                    self.threads[thread_id]["status"] = "stopping"
            
            # 等待所有非守护线程完成
            for thread in list(self.active_threads.values()):
                if not thread.daemon:
                    thread.join(timeout=0.1)
    
    def get_system_thread_by_id(self, sys_thread_id):
        """通过系统线程ID获取工厂线程ID"""
        with self._thread_lock:
            return self.system_thread_map.get(sys_thread_id)
    
    def create_test_threads(self, count=5):
        """创建测试线程"""
        print(f"创建 {count} 个测试线程")
        thread_ids = []
        
        test_modules = [
            "dhcp_configuration", 
            "vpn_deploy", 
            "route_configuration",
            "Batch_configuration_of_addresses", 
            "network_monitor"
        ]
        
        for i in range(count):
            module = test_modules[i % len(test_modules)]
            name = f"{module.capitalize()}_TestThread_{i+1}"
            
            # 创建测试线程
            thread_id = self.start_thread(
                target=self._test_thread_function,
                args=(name, i+1),
                name=name,
                daemon=True,
                module=module
            )
            
            thread_ids.append(thread_id)
            print(f"已创建测试线程: {name}, ID: {thread_id}")
            
        return thread_ids
    
    def _test_thread_function(self, name, sleep_time):
        """测试线程函数"""
        print(f"测试线程 {name} 启动，休眠时间: {sleep_time}秒")
        real_thread_id = threading.current_thread().ident
        print(f"线程 {name} 的系统ID: {real_thread_id}")
        
        # 模拟线程工作
        for i in range(30):
            print(f"线程 {name} 正在工作: {i+1}/30")
            time.sleep(sleep_time)
        print(f"测试线程 {name} 完成工作")