from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QGridLayout, QComboBox, QLineEdit, QTabWidget, QTextEdit,
                            QGroupBox, QFormLayout, QCheckBox, QListWidget, QMessageBox,
                            QSpinBox, QRadioButton, QButtonGroup, QScrollArea, QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QIcon, QColor
import threading
import time
import re

from .route_configuration import RouteConfigOperator
from core.services.device_service import DeviceService


class RouteConfigWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("路由配置工具")
        self.resize(900, 700)
        
        # 从数据库获取设备列表
        self.devices = self.get_devices_from_db()
        
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
        
        # 路由配置操作实例
        self.route_operator = None
        
        # 初始化UI
        self.init_ui()
    
    def get_devices_from_db(self):
        """从数据库获取设备列表，使用DeviceService"""
        try:
            # 使用DeviceService获取所有设备
            devices = DeviceService.get_all_devices()
            
            # 如果成功获取了设备，则返回
            if devices:
                return devices
            return []
        except Exception as e:
            print(f"从数据库获取设备列表失败: {str(e)}")
            return []
    
    def init_ui(self):
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 创建标题标签
        title_label = QLabel("路由配置工具")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333; margin-bottom: 20px;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 创建设备选择区域
        device_group = QGroupBox("设备选择")
        device_layout = QHBoxLayout()
        
        device_layout.addWidget(QLabel("设备:"))
        self.device_combo = QComboBox()
        for device in self.devices:
            self.device_combo.addItem(f"{device['name']} ({device['ip']}) - {device['type']}")
        device_layout.addWidget(self.device_combo)
        
        self.connect_btn = QPushButton("连接测试")
        self.connect_btn.clicked.connect(self.test_connection)
        device_layout.addWidget(self.connect_btn)
        
        device_group.setLayout(device_layout)
        main_layout.addWidget(device_group)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        
        # 添加各种路由配置选项卡
        self.tab_widget.addTab(self.create_static_route_tab(), "静态路由")
        self.tab_widget.addTab(self.create_rip_tab(), "RIP")
        self.tab_widget.addTab(self.create_ospf_tab(), "OSPF")
        self.tab_widget.addTab(self.create_bgp_tab(), "BGP")
        self.tab_widget.addTab(self.create_vpn_tab(), "VPN实例")
        
        main_layout.addWidget(self.tab_widget)
        
        # 创建日志区域
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
        
        # 添加说明标签
        note_label = QLabel("注意: 路由配置将直接应用到设备，请谨慎操作。BGP配置仅适用于出口路由器。")
        note_label.setStyleSheet("color: #e74c3c; font-style: italic;")
        main_layout.addWidget(note_label)
    
    def create_static_route_tab(self):
        """创建静态路由配置选项卡"""
        tab = QWidget()
        layout = QFormLayout()
        
        # 目标网络
        self.static_network = QLineEdit()
        self.static_network.setPlaceholderText("例如: 192.168.1.0/24")
        layout.addRow("目标网络:", self.static_network)
        
        # 下一跳
        self.static_next_hop = QLineEdit()
        self.static_next_hop.setPlaceholderText("例如: 10.0.0.1")
        layout.addRow("下一跳:", self.static_next_hop)
        
        # 管理距离
        self.static_distance = QSpinBox()
        self.static_distance.setRange(1, 255)
        self.static_distance.setValue(60)
        layout.addRow("管理距离:", self.static_distance)
        
        # 添加按钮
        self.static_add_btn = QPushButton("添加静态路由")
        self.static_add_btn.clicked.connect(self.add_static_route)
        layout.addRow("", self.static_add_btn)
        
        tab.setLayout(layout)
        return tab
    
    def create_rip_tab(self):
        """创建RIP配置选项卡"""
        tab = QWidget()
        layout = QFormLayout()
        
        # RIP版本
        self.rip_version = QComboBox()
        self.rip_version.addItems(["1", "2"])
        self.rip_version.setCurrentIndex(1)  # 默认选择RIPv2
        layout.addRow("RIP版本:", self.rip_version)
        
        # 网络列表
        layout.addRow("网络列表:", QLabel("每行一个网络地址"))
        self.rip_networks = QTextEdit()
        self.rip_networks.setPlaceholderText("例如:\n10.0.0.0\n192.168.1.0")
        layout.addRow("", self.rip_networks)
        
        # 添加按钮
        self.rip_config_btn = QPushButton("配置RIP")
        self.rip_config_btn.clicked.connect(self.configure_rip)
        layout.addRow("", self.rip_config_btn)
        
        tab.setLayout(layout)
        return tab
    
    def create_ospf_tab(self):
        """创建OSPF配置选项卡"""
        tab = QWidget()
        layout = QFormLayout()
        
        # OSPF进程ID
        self.ospf_process = QSpinBox()
        self.ospf_process.setRange(1, 65535)
        self.ospf_process.setValue(1)
        layout.addRow("进程ID:", self.ospf_process)
        
        # 区域ID
        self.ospf_area = QLineEdit()
        self.ospf_area.setText("0")
        self.ospf_area.setPlaceholderText("例如: 0 或 0.0.0.0")
        layout.addRow("区域ID:", self.ospf_area)
        
        # 网络列表
        layout.addRow("网络列表:", QLabel("每行一个网络地址/掩码"))
        self.ospf_networks = QTextEdit()
        self.ospf_networks.setPlaceholderText("例如:\n10.0.0.0/8\n192.168.1.0/24")
        layout.addRow("", self.ospf_networks)
        
        # 添加按钮
        self.ospf_config_btn = QPushButton("配置OSPF")
        self.ospf_config_btn.clicked.connect(self.configure_ospf)
        layout.addRow("", self.ospf_config_btn)
        
        tab.setLayout(layout)
        return tab
    
    def create_bgp_tab(self):
        """创建BGP配置选项卡"""
        tab = QWidget()
        layout = QFormLayout()
        
        # BGP自治系统号
        self.bgp_as = QSpinBox()
        self.bgp_as.setRange(1, 65535)
        self.bgp_as.setValue(65000)
        layout.addRow("AS号:", self.bgp_as)
        
        # 路由器ID
        self.bgp_router_id = QLineEdit()
        self.bgp_router_id.setPlaceholderText("例如: 1.1.1.1")
        layout.addRow("路由器ID:", self.bgp_router_id)
        
        # 邻居列表
        layout.addRow("BGP邻居:", QLabel("每行一个邻居，格式: IP地址 AS号"))
        self.bgp_neighbors = QTextEdit()
        self.bgp_neighbors.setPlaceholderText("例如:\n192.168.1.1 65001\n10.0.0.1 65002")
        layout.addRow("", self.bgp_neighbors)
        
        # 网络列表
        layout.addRow("宣告网络:", QLabel("每行一个网络地址/掩码"))
        self.bgp_networks = QTextEdit()
        self.bgp_networks.setPlaceholderText("例如:\n10.0.0.0/8\n192.168.1.0/24")
        layout.addRow("", self.bgp_networks)
        
        # 添加按钮
        self.bgp_config_btn = QPushButton("配置BGP")
        self.bgp_config_btn.clicked.connect(self.configure_bgp)
        layout.addRow("", self.bgp_config_btn)
        
        # 警告标签
        warning = QLabel("注意: BGP配置仅适用于出口路由器!")
        warning.setStyleSheet("color: red;")
        layout.addRow("", warning)
        
        tab.setLayout(layout)
        return tab
    
    def create_vpn_tab(self):
        """创建VPN路由配置选项卡"""
        tab = QWidget()
        layout = QFormLayout()
        
        # VPN实例名称
        self.vpn_name = QLineEdit()
        self.vpn_name.setPlaceholderText("例如: VPN_CUSTOMER_A")
        layout.addRow("VPN名称:", self.vpn_name)
        
        # RD值
        self.vpn_rd = QLineEdit()
        self.vpn_rd.setPlaceholderText("例如: 65000:1")
        layout.addRow("RD值:", self.vpn_rd)
        
        # RT值
        layout.addRow("RT值:", QLabel("每行一个RT值，格式: RT值 [import|export|both]"))
        self.vpn_rt = QTextEdit()
        self.vpn_rt.setPlaceholderText("例如:\n65000:1 import\n65000:2 export\n65000:3 both")
        layout.addRow("", self.vpn_rt)
        
        # 绑定接口
        layout.addRow("绑定接口:", QLabel("每行一个接口名称"))
        self.vpn_interfaces = QTextEdit()
        self.vpn_interfaces.setPlaceholderText("例如:\nGigabitEthernet0/0/1\nGigabitEthernet0/0/2")
        layout.addRow("", self.vpn_interfaces)
        
        # 添加按钮
        self.vpn_config_btn = QPushButton("配置VPN")
        self.vpn_config_btn.clicked.connect(self.configure_vpn)
        layout.addRow("", self.vpn_config_btn)
        
        # 警告标签
        warning = QLabel("注意: VPN配置仅适用于路由器!")
        warning.setStyleSheet("color: red;")
        layout.addRow("", warning)
        
        tab.setLayout(layout)
        return tab
    
    def get_selected_device(self):
        """获取当前选中的设备信息"""
        index = self.device_combo.currentIndex()
        if index >= 0 and index < len(self.devices):
            return self.devices[index]
        return None
    
    def test_connection(self):
        """测试与设备的连接"""
        device = self.get_selected_device()
        if not device:
            self.log_message("错误: 未选择设备", "error")
            return
        
        self.log_message(f"正在连接到 {device['name']} ({device['ip']})...", "info")
        
        # 创建路由配置操作实例
        self.route_operator = RouteConfigOperator(
            device['ip'], 
            device['username'], 
            device['password'],
            device['name'],
            device['type']
        )
        
        # 连接信号
        self.route_operator.config_status.connect(self.handle_config_status)
        self.route_operator.command_output.connect(self.handle_command_output)
        
        # 在线程中执行连接测试
        threading.Thread(target=self._test_connection_thread, daemon=True).start()
    
    def _test_connection_thread(self):
        """连接测试线程"""
        if self.route_operator.connect_device():
            self.log_message(f"连接成功: {self.route_operator.device_info['ip']}", "success")
            self.route_operator.disconnect_device()
        else:
            self.log_message(f"连接失败: {self.route_operator.device_info['ip']}", "error")
    
    def add_static_route(self):
        """添加静态路由"""
        device = self.get_selected_device()
        if not device:
            self.log_message("错误: 未选择设备", "error")
            return
        
        network = self.static_network.text().strip()
        next_hop = self.static_next_hop.text().strip()
        distance = self.static_distance.value()
        
        if not network or not next_hop:
            self.log_message("错误: 目标网络和下一跳不能为空", "error")
            return
        
        self.log_message(f"正在配置静态路由: {network} -> {next_hop}...", "info")
        
        # 创建路由配置操作实例（如果不存在）
        if not self.route_operator:
            self.route_operator = RouteConfigOperator(
                device['ip'], 
                device['username'], 
                device['password'],
                device['name'],
                device['type']
            )
            self.route_operator.config_status.connect(self.handle_config_status)
            self.route_operator.command_output.connect(self.handle_command_output)
        
        # 在线程中执行配置
        threading.Thread(
            target=lambda: self.route_operator.configure_static_route(network, next_hop, distance),
            daemon=True
        ).start()
    
    def configure_rip(self):
        """配置RIP路由协议"""
        device = self.get_selected_device()
        if not device:
            self.log_message("错误: 未选择设备", "error")
            return
        
        version = self.rip_version.currentText()
        networks = self.rip_networks.toPlainText().strip().split('\n')
        
        if not networks or not networks[0]:
            self.log_message("错误: 网络列表不能为空", "error")
            return
        
        self.log_message(f"正在配置RIP路由协议，版本: {version}...", "info")
        
        # 创建路由配置操作实例（如果不存在）
        if not self.route_operator:
            self.route_operator = RouteConfigOperator(
                device['ip'], 
                device['username'], 
                device['password'],
                device['name'],
                device['type']
            )
            self.route_operator.config_status.connect(self.handle_config_status)
            self.route_operator.command_output.connect(self.handle_command_output)
        
        # 在线程中执行配置
        threading.Thread(
            target=lambda: self.route_operator.configure_rip(version, networks),
            daemon=True
        ).start()
    
    def configure_ospf(self):
        """配置OSPF路由协议"""
        device = self.get_selected_device()
        if not device:
            self.log_message("错误: 未选择设备", "error")
            return
        
        process_id = self.ospf_process.value()
        area_id = self.ospf_area.text().strip()
        networks = self.ospf_networks.toPlainText().strip().split('\n')
        
        if not networks or not networks[0]:
            self.log_message("错误: 网络列表不能为空", "error")
            return
        
        if not area_id:
            self.log_message("错误: 区域ID不能为空", "error")
            return
        
        self.log_message(f"正在配置OSPF路由协议，进程ID: {process_id}, 区域: {area_id}...", "info")
        
        # 创建路由配置操作实例（如果不存在）
        if not self.route_operator:
            self.route_operator = RouteConfigOperator(
                device['ip'], 
                device['username'], 
                device['password'],
                device['name'],
                device['type']
            )
            self.route_operator.config_status.connect(self.handle_config_status)
            self.route_operator.command_output.connect(self.handle_command_output)
        
        # 在线程中执行配置
        threading.Thread(
            target=lambda: self.route_operator.configure_ospf(process_id, area_id, networks),
            daemon=True
        ).start()
    
    def configure_bgp(self):
        """配置BGP路由协议"""
        device = self.get_selected_device()
        if not device:
            self.log_message("错误: 未选择设备", "error")
            return
        
        # 检查是否为出口路由器
        if "出口路由器" not in device['type']:
            self.log_message("错误: BGP配置仅适用于出口路由器!", "error")
            return
        
        as_number = self.bgp_as.value()
        router_id = self.bgp_router_id.text().strip()
        
        # 解析邻居列表
        neighbors_text = self.bgp_neighbors.toPlainText().strip()
        if not neighbors_text:
            self.log_message("错误: 邻居列表不能为空", "error")
            return
        
        neighbors = []
        for line in neighbors_text.split('\n'):
            parts = line.strip().split()
            if len(parts) != 2:
                self.log_message(f"错误: 邻居格式错误: {line}", "error")
                return
            neighbors.append({"ip": parts[0], "as_number": parts[1]})
        
        # 解析网络列表
        networks = self.bgp_networks.toPlainText().strip().split('\n')
        if not networks or not networks[0]:
            self.log_message("错误: 网络列表不能为空", "error")
            return
        
        self.log_message(f"正在配置BGP路由协议，AS号: {as_number}...", "info")
        
        # 创建路由配置操作实例（如果不存在）
        if not self.route_operator:
            self.route_operator = RouteConfigOperator(
                device['ip'], 
                device['username'], 
                device['password'],
                device['name'],
                device['type']
            )
            self.route_operator.config_status.connect(self.handle_config_status)
            self.route_operator.command_output.connect(self.handle_command_output)
        
        # 在线程中执行配置
        threading.Thread(
            target=lambda: self.route_operator.configure_bgp(as_number, router_id, neighbors, networks),
            daemon=True
        ).start()
    
    def configure_vpn(self):
        """配置VPN路由"""
        device = self.get_selected_device()
        if not device:
            self.log_message("错误: 未选择设备", "error")
            return
        
        # 检查是否为路由器
        if "路由器" not in device['type']:
            self.log_message("错误: VPN配置仅适用于路由器!", "error")
            return
        
        vpn_name = self.vpn_name.text().strip()
        rd_value = self.vpn_rd.text().strip()
        
        if not vpn_name or not rd_value:
            self.log_message("错误: VPN名称和RD值不能为空", "error")
            return
        
        # 解析RT值
        rt_text = self.vpn_rt.toPlainText().strip()
        if not rt_text:
            self.log_message("错误: RT值不能为空", "error")
            return
        
        rt_values = []
        for line in rt_text.split('\n'):
            parts = line.strip().split()
            if len(parts) != 2 or parts[1] not in ['import', 'export', 'both']:
                self.log_message(f"错误: RT格式错误: {line}", "error")
                return
            rt_values.append({"value": parts[0], "type": parts[1]})
        
        # 解析接口列表
        interfaces = self.vpn_interfaces.toPlainText().strip().split('\n')
        if not interfaces or not interfaces[0]:
            self.log_message("错误: 接口列表不能为空", "error")
            return
        
        self.log_message(f"正在配置VPN路由，VPN名称: {vpn_name}...", "info")
        
        # 创建路由配置操作实例（如果不存在）
        if not self.route_operator:
            self.route_operator = RouteConfigOperator(
                device['ip'], 
                device['username'], 
                device['password'],
                device['name'],
                device['type']
            )
            self.route_operator.config_status.connect(self.handle_config_status)
            self.route_operator.command_output.connect(self.handle_command_output)
        
        # 在线程中执行配置
        threading.Thread(
            target=lambda: self.route_operator.configure_vpn(vpn_name, rd_value, rt_values, interfaces),
            daemon=True
        ).start()
    
    def handle_config_status(self, ip, status, message):
        """处理配置状态信号"""
        if status:
            self.log_message(f"设备 {ip}: {message}", "success")
        else:
            self.log_message(f"设备 {ip}: {message}", "error")
    
    def handle_command_output(self, device_ip, output):
        """处理命令输出信号"""
        self.log_message(f"设备 {device_ip}: {output}", "command")
    
    def log_message(self, message, level="info"):
        """记录日志消息"""
        timestamp = time.strftime("%H:%M:%S")
        
        # 根据级别设置颜色
        if level == "error":
            color = "#e74c3c"  # 红色
            prefix = "[错误]"
        elif level == "success":
            color = "#2ecc71"  # 绿色
            prefix = "[成功]"
        elif level == "command":
            color = "#3498db"  # 蓝色
            prefix = "[命令]"
        elif level == "output":
            color = "#7f8c8d"  # 灰色
            prefix = ""
            # 缩进输出
            message = "    " + message.replace("\n", "\n    ")
        else:
            color = "#2c3e50"  # 深灰色
            prefix = "[信息]"
        
        # 构建HTML格式的日志
        log_html = f"<span style='color: #95a5a6;'>[{timestamp}]</span> "
        if prefix:
            log_html += f"<span style='color: {color};'>{prefix}</span> "
        log_html += f"<span style='color: {color};'>{message}</span><br>"
        
        # 添加到日志文本框
        self.log_text.append(log_html)
        
        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )


def configure_static_route(self):
    """配置静态路由"""
    try:
        # 获取用户输入
        dest_network = self.dest_network_entry.text()
        mask = self.mask_entry.text()
        next_hop = self.next_hop_entry.text()
        
        # 检查输入是否为空
        if not dest_network or not mask or not next_hop:
            self.log_message("错误: 目标网络、掩码和下一跳不能为空", error=True)
            return
        
        # 格式化网络地址和掩码
        if "/" not in dest_network:
            # 如果用户分别输入了网络地址和掩码，则组合它们
            dest_network = f"{dest_network} {mask}"
        
        # 获取当前选中的设备
        device_idx = self.device_combo.currentIndex()
        if device_idx < 0:
            self.log_message("错误: 请选择设备", error=True)
            return
        
        device = self.devices[device_idx]
        
        # 创建配置操作实例
        self.log_message(f"正在配置静态路由: {dest_network} -> {next_hop}...")
        
        # 创建配置操作实例
        config_operator = RouteConfigOperator(
            device["ip"], 
            device["username"], 
            device["password"],
            device["name"],
            device["type"]
        )
        
        # 连接信号
        config_operator.config_status.connect(self.handle_config_status)
        config_operator.command_output.connect(self.handle_command_output)
        
        # 配置静态路由
        success = config_operator.configure_static_route(dest_network, next_hop)
        
        self.log_message(f"{success}")
        
    except Exception as e:
        self.log_message(f"配置静态路由时出错: {str(e)}", error=True)