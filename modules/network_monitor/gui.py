import sys
import time
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QListWidget, QPushButton, QLabel, QProgressBar, QMessageBox,
                             QListWidgetItem, QDialog, QFrame, QGroupBox, QFormLayout, QSpinBox,
                             QCheckBox, QSplitter)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon, QColor, QPixmap

# 导入核心监控服务
from core.business.monitor_service import MonitorService
from core.services.device_service import DeviceService
# 在文件顶部导入部分添加
from core.business.thread_factory import ThreadFactory

# 接口状态详情对话框
class InterfaceStatusDialog(QDialog):
    def __init__(self, interfaces, parent=None):
        super().__init__(parent)
        self.setWindowTitle('接口状态详情')
        self.setFixedSize(500, 500)
        
        self.status_colors = {
            'up': QColor(0, 200, 0),
            'adm_down': QColor(255, 0, 0),
            'down': QColor(0, 0, 0)
        }
        
        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        # 统计面板
        self.stats_label = QLabel()
        stats_layout = QHBoxLayout()
        stats_layout.addWidget(self.stats_label)
        layout.addLayout(stats_layout)
        
        self.setLayout(layout)
        self.update_interface_list(interfaces)

    def update_interface_list(self, interfaces):
        self.list_widget.clear()
        stats = {'up': 0, 'adm_down': 0, 'down': 0}
        
        for intf in interfaces:
            status = intf.get('status', 'down')
            # 确定状态类型和颜色
            if status == 'up':
                color = self.status_colors['up']
                status_type = 'up'
            elif status == 'adm_down':
                color = self.status_colors['adm_down']
                status_type = 'adm_down'
            else:
                color = self.status_colors['down']
                status_type = 'down'
            
            # 创建列表项
            item_text = f"{intf['name']}\n状态：{status.upper()}"
            if intf['errors'] > 0:
                item_text += f"\n错误数：{intf['errors']}"
            
            item = QListWidgetItem(item_text)
            pixmap = QPixmap(16, 16)
            pixmap.fill(color)
            item.setIcon(QIcon(pixmap))
            
            stats[status_type] += 1
            self.list_widget.addItem(item)
        
        # 更新统计信息
        stats_text = (
            f"<span style='color: {self.status_colors['up'].name()};'>●</span> 正常UP: {stats['up']}\n"
            f"<span style='color: {self.status_colors['adm_down'].name()};'>●</span> 异常关闭: {stats['adm_down']}\n"
            f"<span style='color: {self.status_colors['down'].name()};'>●</span> 物理DOWN: {stats['down']}"
        )
        self.stats_label.setText(stats_text)
        self.stats_label.setTextFormat(Qt.RichText)  # 启用富文本格式

# 可视化主界面
class AutoMaintainGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.refresh_interval = 300  # 将类变量改为实例变量
        
        # 从数据库获取设备列表
        self.devices = DeviceService.get_all_devices()
        
        # 如果数据库中没有设备，使用默认设备列表
        if not self.devices:
            self.devices = [
                {"ip": "10.1.0.3", "username": "1", "name": "LSW1", "password": "1", "type": "地域1核心交换机"},
                {"ip": "10.1.200.1", "username": "1", "name": "AR5", "password": "1", "type": "地域1出口路由器"},
                {"ip": "10.1.18.1", "username": "1", "name": "AR1", "password": "1", "type": "地域2出口路由器"},
                {"ip": "22.22.22.22", "username": "1", "name": "LSW2", "password": "1", "type": "地域1汇聚交换机(企业A)"},
                {"ip": "10.1.18.8", "username": "1", "name": "LSW8", "password": "1", "type": "地域2核心交换机(企业A)"},
            ]
            print("未从数据库获取到设备列表，使用默认设备列表")
        else:
            print(f"从数据库获取到 {len(self.devices)} 个设备")
        
        for device in self.devices:
            if "地域1核心交换机" in device.get("type", "") or \
            "地域1出口路由器" in device.get("type", "") or \
            "地域2出口路由器" in device.get("type", ""):
                # 为特殊设备设置默认企业为企业A
                device["enterprise"] = "企业A"
        
        # 状态颜色映射
        self.status_colors = {
            "normal": QColor(0, 200, 0),
            "warning": QColor(255, 165, 0),
            "error": QColor(255, 0, 0),
            "disconnected": QColor(100, 100, 100),
            "unknown": QColor(200, 200, 200)
        }
        
        # 初始化监控服务
        self.monitor_service = MonitorService()
        self.monitor_service.device_status_updated.connect(self.update_device_status)
        self.monitor_service.device_repair_result.connect(self.handle_repair_result)
        
        self.init_ui()
        self.init_auto_refresh()
    
    def get_device_status(self, device_name):
        return next((d for d in self.devices if d["name"] == device_name), None)
    
    def update_topology_view(self, topology_view):
        # 将监控数据同步到拓扑视图
        for device in self.devices:
            node = topology_view.node_items.get(device["name"])
            if node:
                color = self.status_colors.get(device.get("status", "unknown"))
                node["node"].setBrush(color)

    def init_ui(self):
        """初始化UI界面"""
        self.setWindowTitle("网络设备状态监控")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(600)

        # 设置中央部件
        central = QWidget()
        main_layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        # 创建主内容区域
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        main_layout.addWidget(content_widget)

        # 左侧面板 - 设备列表
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 添加设备列表标题
        title_label = QLabel("设备列表")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        left_layout.addWidget(title_label)
        
        # 添加设备列表
        self.device_list = QListWidget()
        self.device_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.device_list.setStyleSheet("QListWidget::item { padding: 6px; }")
        self.device_list.setFocusPolicy(Qt.NoFocus)  # 避免丑陋的虚线选中框
        self.device_list.itemClicked.connect(self.show_basic_info)
        self.device_list.itemDoubleClicked.connect(self.show_interface_status)
        left_layout.addWidget(self.device_list)
        
        # 批量刷新按钮
        refresh_btn = QPushButton("刷新状态")
        refresh_btn.clicked.connect(self.start_monitoring)
        left_layout.addWidget(refresh_btn)
        
        # 自动刷新设置区域
        auto_refresh_group = QGroupBox("自动刷新设置")
        auto_refresh_layout = QHBoxLayout()
        
        # 添加自动刷新复选框
        self.auto_refresh_checkbox = QCheckBox("启用自动刷新")
        self.auto_refresh_checkbox.toggled.connect(self.toggle_auto_refresh)
        auto_refresh_layout.addWidget(self.auto_refresh_checkbox)
        
        # 刷新间隔设置
        auto_refresh_layout.addWidget(QLabel("间隔:"))
        self.refresh_interval_box = QSpinBox()
        self.refresh_interval_box.setRange(5, 300)
        self.refresh_interval_box.setSuffix(" 秒")
        self.refresh_interval_box.valueChanged.connect(self.update_refresh_interval)
        auto_refresh_layout.addWidget(self.refresh_interval_box)
        
        auto_refresh_group.setLayout(auto_refresh_layout)
        left_layout.addWidget(auto_refresh_group)
        
        # 修复按钮区域
        repair_group = QGroupBox("故障修复")
        repair_layout = QVBoxLayout()
        
        repair_selected_btn = QPushButton("修复选中设备")
        repair_selected_btn.clicked.connect(self.repair_selected)
        repair_layout.addWidget(repair_selected_btn)
        
        repair_all_btn = QPushButton("修复所有故障设备")
        repair_all_btn.clicked.connect(self.repair_all_faulty)
        repair_layout.addWidget(repair_all_btn)
        
        repair_group.setLayout(repair_layout)
        left_layout.addWidget(repair_group)
        
        # 添加线程监控按钮
        thread_monitor_btn = QPushButton("打开线程监控")
        thread_monitor_btn.clicked.connect(self.open_thread_monitor)
        left_layout.addWidget(thread_monitor_btn)
        
        # 右侧面板 - 详细信息
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 添加详细信息标题
        details_title = QLabel("设备详细信息")
        details_title.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        right_layout.addWidget(details_title)
        
        # 添加详细信息显示区域
        self.detail_label = QLabel("请选择一个设备查看详细信息")
        self.detail_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.detail_label.setStyleSheet("background-color: #f5f5f5; padding: 10px; border-radius: 5px;")
        self.detail_label.setWordWrap(True)
        right_layout.addWidget(self.detail_label)
        
        # 使用分割器组合左右面板
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 700])  # 设置初始分割比例
        
        content_layout.addWidget(splitter)

        # 添加状态栏
        status_bar = QFrame()
        status_bar.setFrameShape(QFrame.StyledPanel)
        status_bar_layout = QHBoxLayout(status_bar)
        status_bar_layout.setContentsMargins(5, 2, 5, 2)

        self.status_label = QLabel("就绪")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(15)
        self.progress_bar.setTextVisible(False)

        status_bar_layout.addWidget(self.status_label, 1)
        status_bar_layout.addWidget(self.progress_bar)

        main_layout.addWidget(status_bar)
        
        # 加载设备列表
        self.update_device_list()
        
        # 设置初始刷新间隔
        self.refresh_interval_box.setValue(self.refresh_interval)
        # 初始状态下不启用自动刷新
        self.auto_refresh_checkbox.setChecked(False)

    def toggle_auto_refresh(self, enabled):
        """切换自动刷新状态"""
        if enabled:
            interval = self.refresh_interval_box.value() * 1000  # 转换为毫秒
            self.refresh_timer.start(interval)
            self.status_label.setText(f"已启用自动刷新 (每{self.refresh_interval_box.value()}秒)")
        else:
            self.refresh_timer.stop()
            self.status_label.setText("自动刷新已禁用")
            
    def update_refresh_interval(self, value):
        """更新刷新间隔"""
        if self.auto_refresh_checkbox.isChecked():
            self.refresh_timer.start(value * 1000)  # 转换为毫秒
            self.status_label.setText(f"已更新自动刷新间隔为 {value} 秒")

    def show_interface_status(self):
        """显示接口状态详情"""
        selected = self.device_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "警告", "请先选择设备")
            return
            
        device = selected.data(Qt.UserRole)
        details = device.get('details', {})
        interfaces = details.get('interfaces', [])
        
        dialog = InterfaceStatusDialog(interfaces, self)
        dialog.exec_()

    def init_auto_refresh(self):
        """初始化自动刷新功能"""
        self.refresh_timer = QTimer()
        # 将timeout信号连接到refresh_device_status方法，而不是不存在的refresh_device_list
        self.refresh_timer.timeout.connect(self.refresh_device_status)
        # 设置刷新间隔为30秒
        self.refresh_interval_box.setValue(30)
        # 默认不启用自动刷新
        self.auto_refresh_checkbox.setChecked(False)
        self.refresh_timer.stop()

    def open_thread_monitor(self):
        """打开线程监控窗口"""
        try:
            from core.thread_monitor import ThreadMonitorDialog
            # 从线程工厂获取实例
            from core.business.thread_factory import ThreadFactory
            thread_factory = ThreadFactory.get_instance()
            
            # 打开线程监控对话框
            monitor = ThreadMonitorDialog(thread_factory, self)
            monitor.exec_()
        except Exception as e:
            import traceback
            print(f"打开线程监控失败: {str(e)}")
            traceback.print_exc()
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "警告", f"无法打开线程监控: {str(e)}")

    def refresh_device_status(self):
        """刷新设备状态"""
        # 获取所有选中的设备
        selected_devices = []
        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            if item.checkState() == Qt.Checked:
                device_info = item.data(Qt.UserRole)
                selected_devices.append(device_info)
        
        # 如果有选中的设备，则刷新它们的状态
        if selected_devices:
            self.start_monitoring(selected_devices)
    
    def update_device_list(self):
        self.device_list.clear()
        prev_region = None
        
        # 用于跟踪已经处理过的特殊设备类型
        seen_special_devices = set()
        
        for device in self.devices:
            device_type = device.get("type", "")
            
            # 处理特殊设备
            if "地域1核心交换机" in device_type or \
               "地域1出口路由器" in device_type or \
               "地域2出口路由器" in device_type:
                # 如果是特殊设备，检查是否已经添加过
                if device_type in seen_special_devices:
                    continue  # 跳过重复的特殊设备
                seen_special_devices.add(device_type)
                # 确保特殊设备的企业为企业A
                device["enterprise"] = "企业A"
            
            current_region = "地域1" if "地域1" in device_type else "地域2"
            
            # 添加分隔线
            if prev_region and current_region != prev_region:
                # 添加空白间隔
                spacing_item = QListWidgetItem()
                spacing_item.setFlags(Qt.NoItemFlags)
                spacing_item.setSizeHint(QSize(0, 10))  # 上间距
                self.device_list.addItem(spacing_item)
                
                # 创建细灰线
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setLineWidth(1)  # 线宽改为1像素
                line.setStyleSheet("color: #CCCCCC;")  # 浅灰色
                
                line_item = QListWidgetItem()
                line_item.setFlags(Qt.NoItemFlags)
                self.device_list.addItem(line_item)
                self.device_list.setItemWidget(line_item, line)
                
                # 添加下方空白
                spacing_item = QListWidgetItem()
                spacing_item.setFlags(Qt.NoItemFlags)
                spacing_item.setSizeHint(QSize(0, 10))  # 下间距
                self.device_list.addItem(spacing_item)
            
            # 添加设备项
            status = device.get('status', 'unknown')
            
            # 获取企业信息
            enterprise_info = ""
            if "地域1核心交换机" in device_type or \
               "地域1出口路由器" in device_type or \
               "地域2出口路由器" in device_type:
                # 特殊设备不显示企业信息，因为它们统一使用企业A
                enterprise_info = ""
            elif device.get("enterprise"):
                # 其他设备如果有企业信息则显示
                enterprise_info = f" ({device.get('enterprise')})"
            elif device.get("description"):
                # 如果没有企业信息但有描述信息，使用描述信息
                enterprise_info = f" ({device.get('description')})"
            
            # 设备名称显示
            device_name = f"{device_type}{enterprise_info}"
            
            item = QListWidgetItem(self.status_icon(status), device_name)
            item.setData(Qt.UserRole, device)
            # 设置文字颜色
            if "error" in status.lower():
                item.setForeground(QColor(255, 0, 0))  # 错误状态标红
            # 设置字体大小
            font = item.font()
            font.setPointSize(12)
            item.setFont(font)
            self.device_list.addItem(item)
            
            prev_region = current_region

    def status_icon(self, status):
        base_status = status.split()[0].lower()  # 新增状态解析逻辑
        pixmap = QPixmap(32, 32)
        pixmap.fill(self.status_colors.get(base_status, Qt.white))
        return QIcon(pixmap)

    def start_monitoring(self):
        self.status_label.setText("正在刷新设备状态...")
        
        # 确保特殊设备的企业字段正确设置
        for device in self.devices:
            if "地域1核心交换机" in device.get("type", "") or \
               "地域1出口路由器" in device.get("type", "") or \
               "地域2出口路由器" in device.get("type", ""):
                # 使用安全的方式设置企业信息
                device["enterprise"] = "企业A"
        
        # 使用监控服务监控所有设备
        self.monitor_service.monitor_all_devices(self.devices)

    def monitor_device(self, device):
        # 使用监控服务获取设备状态
        self.monitor_service.get_device_status(device)

    def update_device_status(self, ip, status, details):
        """更新设备状态"""
        for device in self.devices:
            if device["ip"] == ip:
                # 更新设备状态
                device.update({
                    "status": status,
                    "details": details,  # 保存完整的状态数据
                    "cpu": details.get('cpu', 0),  # 直接获取CPU使用率
                    "mem": details.get('mem', 0),  # 直接获取内存使用率
                    "last_update": details.get('last_update', time.strftime("%Y-%m-%d %H:%M:%S"))
                })
                break
        self.update_device_list()
        self.status_label.setText(f"设备 {ip} 状态已更新")

    def repair_selected(self):
        selected = self.device_list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "警告", "请先选择要修复的设备")
            return
        ips = [item.data(Qt.UserRole)["ip"] for item in selected]
        self.start_repair(ips)

    def repair_all_faulty(self):
        # 修改：改进故障设备识别逻辑，包含所有error状态设备
        faulty = [d for d in self.devices if d.get("status", "").startswith("error")]
        if not faulty:
            QMessageBox.information(self, "提示", "当前没有需要修复的设备")
            return
        ips = [d["ip"] for d in faulty]
        self.start_repair(ips)

    def start_repair(self, ips):
        self.progress_bar.setMaximum(len(ips))
        self.progress_bar.setValue(0)
        
        for index, ip in enumerate(ips):
            device = next(d for d in self.devices if d["ip"] == ip)
            
            # 根据错误类型显示不同的状态信息
            status = device.get('status', '')
            details = device.get('details', {})
            
            if '连接超时' in status or '未知错误' in status:
                self.status_label.setText(f"{ip}: 正在尝试重启设备...")
                # 使用监控服务重启设备
                self.monitor_service.repair_device(ip, "reboot")
            else:
                # 获取第一个故障接口
                faulty_intf = None
                if 'interfaces' in details:
                    for intf in details['interfaces']:
                        if intf.get('status') == 'adm_down' or intf.get('errors', 0) > 0:
                            faulty_intf = intf['name']
                            break
                
                if faulty_intf:
                    self.status_label.setText(f"{ip}: 正在修复接口 {faulty_intf}...")
                    print(f"开始修复设备 {ip} 的接口 {faulty_intf}")
                    # 使用监控服务修复接口
                    try:
                        success = self.monitor_service.repair_interface(ip, faulty_intf)
                        if not success:
                            self.status_label.setText(f"{ip}: 修复接口 {faulty_intf} 失败，请检查设备状态")
                            print(f"修复接口 {faulty_intf} 失败，返回值为 False")
                    except Exception as e:
                        self.status_label.setText(f"{ip}: 修复接口 {faulty_intf} 出现异常: {str(e)}")
                        print(f"修复接口异常: {str(e)}")
                else:
                    self.progress_bar.setValue(index+1)
                    self.status_label.setText(f"{ip}: 未找到需要修复的接口")

    def handle_repair_result(self, ip, success):
        current = self.progress_bar.value() + 1
        self.progress_bar.setValue(current)
        
        if success:
            # 修复设备状态获取逻辑
            device = next((d for d in self.devices if d["ip"] == ip), None)
            status = device.get('status', '') if device else ''
            
            msg = "重启成功" if '连接超时' in status else "修复成功"
            self.status_label.setText(f"设备 {ip} {msg}！等待重新连接...")
            QTimer.singleShot(10000, self.start_monitoring)
        else:
            QMessageBox.critical(
                self, 
                "操作失败",
                f"{ip} 操作失败，请检查：\n"
                "1. 设备是否完全离线\n"
                "2. 物理连接是否正常\n"
                "3. 是否进入bootloader模式\n\n"
                "建议进行手动检查或者根据网络监控工具检查！"
            )
            self.status_label.setText(f"设备 {ip} 操作失败！")

    def show_basic_info(self, item):
        """显示设备基本信息"""
        try:
            device_info = item.data(Qt.UserRole)
            if not device_info:
                return
            
            # 设备状态文本颜色
            status_colors = {
                "normal": "#2ecc71",  # 绿色
                "warning": "#f39c12",  # 橙色
                "error": "#e74c3c",    # 红色
                "disconnected": "#7f8c8d",  # 灰色
                "unknown": "#95a5a6"   # 浅灰色
            }
            
            # 获取设备状态
            status = device_info.get("status", "unknown")
            status_color = status_colors.get(status, "#95a5a6")
            
            # 获取CPU和内存信息
            cpu = device_info.get("cpu", 0)
            mem = device_info.get("mem", 0)
            
            # 如果从device_info中获取不到，尝试从details中获取
            if cpu == 0 or mem == 0:
                details = device_info.get("details", {})
                cpu = details.get("cpu", cpu)
                mem = details.get("mem", mem)
            
            print(f"显示设备信息 - CPU: {cpu}%, 内存: {mem}%")  # 调试输出
            
            # 创建HTML格式的信息显示
            info = f"""
            <h3>{device_info['name']} ({device_info['ip']})</h3>
            <p><b>设备类型:</b> {device_info.get('type', '未知')}</p>
            <p><b>状态:</b> <span style='color: {status_color};'>{status.upper()}</span></p>
            <p><b>CPU使用率:</b> {cpu}%</p>
            <p><b>内存使用率:</b> {mem}%</p>
            <p><b>最后更新:</b> {device_info.get('last_update', '未更新')}</p>
            """
            
            # 添加接口信息摘要
            interfaces = device_info.get("interfaces", [])
            if not interfaces and "details" in device_info:
                interfaces = device_info["details"].get("interfaces", [])
            
            if interfaces:
                total = len(interfaces)
                up = len([i for i in interfaces if i.get('status') == 'up'])
                down = len([i for i in interfaces if i.get('status') == 'down'])
                adm_down = len([i for i in interfaces if i.get('status') == 'adm_down'])
                
                info += f"""
                <h4>接口状态摘要:</h4>
                <p>总接口数: {total}</p>
                <p>UP: <span style='color: #2ecc71;'>{up}</span></p>
                <p>DOWN: <span style='color: #7f8c8d;'>{down}</span></p>
                <p>管理性关闭: <span style='color: #e74c3c;'>{adm_down}</span></p>
                <p>双击设备可查看详细接口状态</p>
                """
            
            # 设置详情标签
            self.detail_label.setText(info)
            
        except Exception as e:
            print(f"显示设备信息时出错: {str(e)}")
            import traceback
            traceback.print_exc()

    def show_details(self):
        selected = self.device_list.currentItem()
        if not selected:
            return
        device = selected.data(Qt.UserRole)
        details = device.get('details', {})
        
        info = f"=== 设备详细信息 ===\n"
        info += f"设备名称: {device.get('name')}\n"
        info += f"设备类型: {device.get('type')}\n"
        info += f"IP地址: {device.get('ip')}\n"
        info += f"状态: {device.get('status')}\n"
        info += f"最后更新: {device.get('last_update', '未知')}\n\n"
        
        if 'cpu' in details:
            info += f"CPU使用率: {details['cpu']}%\n"
        if 'mem' in details:
            info += f"内存使用率: {details['mem']}%\n"
        
        if 'interfaces' in details:
            up_count = len([i for i in details['interfaces'] if i['status'] == 'up'])
            down_count = len([i for i in details['interfaces'] if i['status'] == 'down'])
            adm_down_count = len([i for i in details['interfaces'] if i['status'] == 'adm_down'])
            error_count = len([i for i in details['interfaces'] if i['errors'] > 0])
            
            info += f"\n接口统计:\n"
            info += f"- 正常UP: {up_count}\n"
            info += f"- 物理DOWN: {down_count}\n"
            info += f"- 管理DOWN: {adm_down_count}\n"
            info += f"- 有错误: {error_count}\n"
        
        if 'error' in details:
            info += f"\n错误信息: {details['error']}\n"
        
        QMessageBox.information(self, "设备详情", info)

    def load_devices(self):
        """加载设备列表到界面"""
        # 更新设备列表界面
        self.update_device_list()
        
    def load_topology_view(self):
        """加载网络拓扑图"""
        # 简单展示一个文本，实际应用中可能会加载真实的拓扑图
        self.topology_view.setText("网络拓扑视图将在此显示")
        
        # 可以在这里加载真实的拓扑图，例如：
        # from core.services.topology_service import TopologyService
        # topology = TopologyService.get_topology()
        # self.update_topology_view(topology)

# 主程序入口
def main():
    app = QApplication(sys.argv)
    window = AutoMaintainGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()