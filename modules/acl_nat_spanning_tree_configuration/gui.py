import sys
import threading
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, 
    QLineEdit, QComboBox, QSpinBox, QTextEdit, QPushButton,
    QTabWidget, QGroupBox, QRadioButton, QButtonGroup, QCheckBox,
    QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from core.services.device_service import DeviceService

# 导入配置操作类
from .acl_nat_spanning_tree_configuration import ConfigOperator

class ConfigurationWindow(QWidget):
    """ACL/NAT/生成树配置窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ACL/NAT/生成树配置")
        self.resize(800, 600)
        
        # 初始化设备列表
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
        
        # 初始化配置操作实例
        self.config_operator = None
        
        # 创建UI
        self.init_ui()
    def get_devices_from_db(self):
        """从数据库获取设备列表，使用DeviceService"""
        try:
            # 使用DeviceService获取所有设备
            devices = DeviceService.get_all_devices()
            
            # 如果成功获取了设备，则返回
            if devices:
                # 处理特殊设备的enterprise字段
                for device in devices:
                    if "地域1核心交换机" in device.get("type", "") or \
                       "地域1出口路由器" in device.get("type", "") or \
                       "地域2出口路由器" in device.get("type", ""):
                        # 为特殊设备设置默认企业为企业A
                        device["enterprise"] = "企业A"
                return devices
            return []
        except Exception as e:
            print(f"从数据库获取设备列表失败: {str(e)}")
            return []
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        
        # 设备选择区域
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("选择设备:"))
        self.device_combo = QComboBox()
        for device in self.devices:
            # 获取企业信息
            enterprise_info = ""
            if "地域1核心交换机" in device.get("type", "") or \
               "地域1出口路由器" in device.get("type", "") or \
               "地域2出口路由器" in device.get("type", ""):
                # 特殊设备显示企业A
                enterprise_info = " (企业A)"
            elif device.get("enterprise"):
                # 其他设备如果有企业信息则显示
                enterprise_info = f" ({device.get('enterprise')})"
                
            self.device_combo.addItem(f"{device['type']}{enterprise_info} ({device['ip']})")
        device_layout.addWidget(self.device_combo)
        
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self.test_connection)
        device_layout.addWidget(self.test_btn)
        
        main_layout.addLayout(device_layout)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_acl_tab(), "ACL配置")
        self.tab_widget.addTab(self.create_nat_tab(), "NAT配置")
        self.tab_widget.addTab(self.create_stp_tab(), "生成树配置")
        
        main_layout.addWidget(self.tab_widget)
        
        # 日志区域
        main_layout.addWidget(QLabel("操作日志:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        main_layout.addWidget(self.log_text)
    
    def create_acl_tab(self):
        """创建ACL配置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # ACL类型选择
        type_group = QGroupBox("ACL类型")
        type_layout = QHBoxLayout()
        
        self.acl_type_group = QButtonGroup()
        self.basic_acl_radio = QRadioButton("基本ACL (2000-2999)")
        self.advanced_acl_radio = QRadioButton("高级ACL (3000-3999)")
        
        self.acl_type_group.addButton(self.basic_acl_radio)
        self.acl_type_group.addButton(self.advanced_acl_radio)
        self.basic_acl_radio.setChecked(True)
        
        type_layout.addWidget(self.basic_acl_radio)
        type_layout.addWidget(self.advanced_acl_radio)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # ACL规则配置
        rule_group = QGroupBox("ACL规则配置")
        rule_layout = QFormLayout()
        
        self.acl_number = QSpinBox()
        self.acl_number.setRange(2000, 2999)
        self.acl_number.setValue(2000)
        rule_layout.addRow("ACL编号:", self.acl_number)
        
        self.acl_rule = QSpinBox()
        self.acl_rule.setRange(0, 2147483647)  # Changed from 4294967295 to max 32-bit signed int
        self.acl_rule.setValue(5)
        rule_layout.addRow("规则编号:", self.acl_rule)
        
        self.acl_action = QComboBox()
        self.acl_action.addItems(["permit", "deny"])
        rule_layout.addRow("动作:", self.acl_action)
        
        self.acl_source = QLineEdit()
        self.acl_source.setPlaceholderText("例如: 192.168.1.0 0.0.0.255")
        rule_layout.addRow("源地址:", self.acl_source)
        
        self.acl_dest = QLineEdit()
        self.acl_dest.setPlaceholderText("例如: 10.0.0.0 0.255.255.255")
        rule_layout.addRow("目的地址:", self.acl_dest)
        
        self.acl_protocol = QComboBox()
        self.acl_protocol.addItems(["ip", "tcp", "udp", "icmp"])
        rule_layout.addRow("协议:", self.acl_protocol)
        
        self.acl_port = QLineEdit()
        self.acl_port.setPlaceholderText("例如: destination-port eq 80")
        rule_layout.addRow("端口:", self.acl_port)
        
        rule_group.setLayout(rule_layout)
        layout.addWidget(rule_group)
        
        # 应用到接口
        interface_group = QGroupBox("应用到接口")
        interface_layout = QFormLayout()
        
        self.acl_interface = QComboBox()
        self.acl_interface.addItems(["GigabitEthernet0/0/0", "GigabitEthernet0/0/1", "GigabitEthernet0/0/2"])
        interface_layout.addRow("接口:", self.acl_interface)
        
        self.acl_direction = QComboBox()
        self.acl_direction.addItems(["inbound", "outbound"])
        interface_layout.addRow("方向:", self.acl_direction)
        
        interface_group.setLayout(interface_layout)
        layout.addWidget(interface_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.add_acl_btn = QPushButton("添加ACL规则")
        self.add_acl_btn.clicked.connect(self.add_acl_rule)
        button_layout.addWidget(self.add_acl_btn)
        
        self.apply_acl_btn = QPushButton("应用到接口")
        self.apply_acl_btn.clicked.connect(self.apply_acl_to_interface)
        button_layout.addWidget(self.apply_acl_btn)
        
        self.view_acl_btn = QPushButton("查看ACL配置")
        self.view_acl_btn.clicked.connect(self.view_acl)
        button_layout.addWidget(self.view_acl_btn)
        
        layout.addLayout(button_layout)
        
        # 更新UI状态
        self.basic_acl_radio.toggled.connect(self.update_acl_ui)
        self.advanced_acl_radio.toggled.connect(self.update_acl_ui)
        self.update_acl_ui()
        
        return tab
    
    def create_nat_tab(self):
        """创建NAT配置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # NAT类型选择
        type_group = QGroupBox("NAT类型")
        type_layout = QHBoxLayout()
        
        self.nat_type_group = QButtonGroup()
        self.static_nat_radio = QRadioButton("静态NAT")
        self.dynamic_nat_radio = QRadioButton("动态NAT")
        self.pat_radio = QRadioButton("PAT")
        
        self.nat_type_group.addButton(self.static_nat_radio)
        self.nat_type_group.addButton(self.dynamic_nat_radio)
        self.nat_type_group.addButton(self.pat_radio)
        self.static_nat_radio.setChecked(True)
        
        type_layout.addWidget(self.static_nat_radio)
        type_layout.addWidget(self.dynamic_nat_radio)
        type_layout.addWidget(self.pat_radio)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # 静态NAT配置
        self.static_nat_group = QGroupBox("静态NAT配置")
        static_layout = QFormLayout()
        
        self.static_inside_ip = QLineEdit()
        self.static_inside_ip.setPlaceholderText("例如: 192.168.1.100")
        static_layout.addRow("内部地址:", self.static_inside_ip)
        
        self.static_outside_ip = QLineEdit()
        self.static_outside_ip.setPlaceholderText("例如: 200.200.200.100")
        static_layout.addRow("外部地址:", self.static_outside_ip)
        
        self.static_nat_group.setLayout(static_layout)
        layout.addWidget(self.static_nat_group)
        
        # 动态NAT配置
        self.dynamic_nat_group = QGroupBox("动态NAT配置")
        dynamic_layout = QFormLayout()
        
        self.dynamic_inside_network = QLineEdit()
        self.dynamic_inside_network.setPlaceholderText("例如: 192.168.1.0 0.0.0.255")
        dynamic_layout.addRow("内部网络:", self.dynamic_inside_network)
        
        self.dynamic_pool_name = QLineEdit()
        self.dynamic_pool_name.setPlaceholderText("例如: NAT_POOL")
        dynamic_layout.addRow("地址池名称:", self.dynamic_pool_name)
        
        self.dynamic_pool_start = QLineEdit()
        self.dynamic_pool_start.setPlaceholderText("例如: 200.200.200.1")
        dynamic_layout.addRow("起始地址:", self.dynamic_pool_start)
        
        self.dynamic_pool_end = QLineEdit()
        self.dynamic_pool_end.setPlaceholderText("例如: 200.200.200.10")
        dynamic_layout.addRow("结束地址:", self.dynamic_pool_end)
        
        self.dynamic_nat_group.setLayout(dynamic_layout)
        layout.addWidget(self.dynamic_nat_group)
        
        # PAT配置
        self.pat_group = QGroupBox("PAT配置")
        pat_layout = QFormLayout()
        
        self.pat_inside_network = QLineEdit()
        self.pat_inside_network.setPlaceholderText("例如: 192.168.1.0 0.0.0.255")
        pat_layout.addRow("内部网络:", self.pat_inside_network)
        
        self.pat_outside_interface = QComboBox()
        self.pat_outside_interface.addItems(["GigabitEthernet0/0/0", "GigabitEthernet0/0/1", "GigabitEthernet0/0/2"])
        pat_layout.addRow("外部接口:", self.pat_outside_interface)
        
        self.pat_group.setLayout(pat_layout)
        layout.addWidget(self.pat_group)
        
        # 接口配置
        interface_group = QGroupBox("接口配置")
        interface_layout = QFormLayout()
        
        self.nat_inside_interface = QComboBox()
        self.nat_inside_interface.addItems(["GigabitEthernet0/0/0", "GigabitEthernet0/0/1", "GigabitEthernet0/0/2"])
        interface_layout.addRow("内部接口:", self.nat_inside_interface)
        
        self.nat_outside_interface = QComboBox()
        self.nat_outside_interface.addItems(["GigabitEthernet0/0/0", "GigabitEthernet0/0/1", "GigabitEthernet0/0/2"])
        interface_layout.addRow("外部接口:", self.nat_outside_interface)
        
        interface_group.setLayout(interface_layout)
        layout.addWidget(interface_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.config_nat_btn = QPushButton("配置NAT")
        self.config_nat_btn.clicked.connect(self.configure_nat)
        button_layout.addWidget(self.config_nat_btn)
        
        self.view_nat_btn = QPushButton("查看NAT配置")
        self.view_nat_btn.clicked.connect(self.view_nat)
        button_layout.addWidget(self.view_nat_btn)
        
        layout.addLayout(button_layout)
        
        # 更新UI状态
        self.static_nat_radio.toggled.connect(self.update_nat_ui)
        self.dynamic_nat_radio.toggled.connect(self.update_nat_ui)
        self.pat_radio.toggled.connect(self.update_nat_ui)
        self.update_nat_ui()
        
        return tab
    
    def create_stp_tab(self):
        """创建生成树协议配置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # STP类型选择
        type_group = QGroupBox("生成树协议类型")
        type_layout = QHBoxLayout()
        
        self.stp_type_group = QButtonGroup()
        self.stp_radio = QRadioButton("STP")
        self.rstp_radio = QRadioButton("RSTP")
        self.mstp_radio = QRadioButton("MSTP")
        
        self.stp_type_group.addButton(self.stp_radio)
        self.stp_type_group.addButton(self.rstp_radio)
        self.stp_type_group.addButton(self.mstp_radio)
        self.stp_radio.setChecked(True)
        
        type_layout.addWidget(self.stp_radio)
        type_layout.addWidget(self.rstp_radio)
        type_layout.addWidget(self.mstp_radio)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # 全局配置
        global_group = QGroupBox("全局配置")
        global_layout = QFormLayout()
        
        self.stp_mode = QComboBox()
        self.stp_mode.addItems(["stp", "rstp", "mstp"])
        global_layout.addRow("STP模式:", self.stp_mode)
        
        self.stp_priority = QSpinBox()
        self.stp_priority.setRange(0, 61440)
        self.stp_priority.setValue(32768)
        self.stp_priority.setSingleStep(4096)
        global_layout.addRow("桥优先级:", self.stp_priority)
        
        self.stp_forward_time = QSpinBox()
        self.stp_forward_time.setRange(4, 30)
        self.stp_forward_time.setValue(15)
        global_layout.addRow("Forward Time:", self.stp_forward_time)
        
        self.stp_hello_time = QSpinBox()
        self.stp_hello_time.setRange(1, 10)
        self.stp_hello_time.setValue(2)
        global_layout.addRow("Hello Time:", self.stp_hello_time)
        
        self.stp_max_age = QSpinBox()
        self.stp_max_age.setRange(6, 40)
        self.stp_max_age.setValue(20)
        global_layout.addRow("Max Age:", self.stp_max_age)
        
        global_group.setLayout(global_layout)
        layout.addWidget(global_group)
        
        # MSTP特有配置
        self.mstp_group = QGroupBox("MSTP配置")
        mstp_layout = QFormLayout()
        
        self.mstp_region = QLineEdit()
        self.mstp_region.setPlaceholderText("例如: Region1")
        mstp_layout.addRow("MST区域名称:", self.mstp_region)
        
        self.mstp_revision = QSpinBox()
        self.mstp_revision.setRange(0, 65535)
        self.mstp_revision.setValue(0)
        mstp_layout.addRow("修订级别:", self.mstp_revision)
        
        self.mstp_instance = QSpinBox()
        self.mstp_instance.setRange(0, 64)
        self.mstp_instance.setValue(1)
        mstp_layout.addRow("实例ID:", self.mstp_instance)
        
        self.mstp_vlan = QLineEdit()
        self.mstp_vlan.setPlaceholderText("例如: 1-10,20,30-40")
        mstp_layout.addRow("VLAN映射:", self.mstp_vlan)
        
        self.mstp_group.setLayout(mstp_layout)
        layout.addWidget(self.mstp_group)
        
        # 接口配置
        interface_group = QGroupBox("接口配置")
        interface_layout = QFormLayout()
        
        self.stp_interface = QComboBox()
        self.stp_interface.addItems(["GigabitEthernet0/0/1", "GigabitEthernet0/0/2", "GigabitEthernet0/0/3"])
        interface_layout.addRow("接口:", self.stp_interface)
        
        self.stp_port_priority = QSpinBox()
        self.stp_port_priority.setRange(0, 240)
        self.stp_port_priority.setValue(128)
        self.stp_port_priority.setSingleStep(16)
        interface_layout.addRow("端口优先级:", self.stp_port_priority)
        
        self.stp_port_cost = QSpinBox()
        self.stp_port_cost.setRange(1, 200000000)
        self.stp_port_cost.setValue(20000)
        interface_layout.addRow("路径开销:", self.stp_port_cost)
        
        self.stp_edge_port = QCheckBox("边缘端口")
        interface_layout.addRow("", self.stp_edge_port)
        
        self.stp_bpdu_guard = QCheckBox("BPDU保护")
        interface_layout.addRow("", self.stp_bpdu_guard)
        
        self.stp_root_guard = QCheckBox("根保护")
        interface_layout.addRow("", self.stp_root_guard)
        
        interface_group.setLayout(interface_layout)
        layout.addWidget(interface_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.config_stp_global_btn = QPushButton("配置全局STP")
        self.config_stp_global_btn.clicked.connect(self.configure_stp_global)
        button_layout.addWidget(self.config_stp_global_btn)
        
        self.config_stp_interface_btn = QPushButton("配置接口STP")
        self.config_stp_interface_btn.clicked.connect(self.configure_stp_interface)
        button_layout.addWidget(self.config_stp_interface_btn)
        
        self.view_stp_btn = QPushButton("查看STP状态")
        self.view_stp_btn.clicked.connect(self.view_stp)
        button_layout.addWidget(self.view_stp_btn)
        
        layout.addLayout(button_layout)
        
        # 更新UI状态
        self.stp_radio.toggled.connect(self.update_stp_ui)
        self.rstp_radio.toggled.connect(self.update_stp_ui)
        self.mstp_radio.toggled.connect(self.update_stp_ui)
        self.update_stp_ui()
        
        return tab
    
    def update_acl_ui(self):
        """根据ACL类型更新UI状态"""
        is_basic = self.basic_acl_radio.isChecked()
        
        # 更新ACL编号范围
        if is_basic:
            self.acl_number.setRange(2000, 2999)
            self.acl_number.setValue(2000)
        else:
            self.acl_number.setRange(3000, 3999)
            self.acl_number.setValue(3000)
        
        # 更新字段可用性
        self.acl_dest.setEnabled(not is_basic)
        self.acl_protocol.setEnabled(not is_basic)
        self.acl_port.setEnabled(not is_basic)
    
    def update_nat_ui(self):
        """根据NAT类型更新UI状态"""
        is_static = self.static_nat_radio.isChecked()
        is_dynamic = self.dynamic_nat_radio.isChecked()
        is_pat = self.pat_radio.isChecked()
        
        self.static_nat_group.setVisible(is_static)
        self.dynamic_nat_group.setVisible(is_dynamic)
        self.pat_group.setVisible(is_pat)
    
    def update_stp_ui(self):
        """根据STP类型更新UI状态"""
        is_mstp = self.mstp_radio.isChecked()
        
        # 更新STP模式
        if self.stp_radio.isChecked():
            self.stp_mode.setCurrentText("stp")
        elif self.rstp_radio.isChecked():
            self.stp_mode.setCurrentText("rstp")
        else:
            self.stp_mode.setCurrentText("mstp")
        
        # 更新MSTP特有配置可见性
        self.mstp_group.setVisible(is_mstp)
    
    def test_connection(self):
        """测试与设备的连接"""
        try:
            device_idx = self.device_combo.currentIndex()
            if device_idx < 0:
                return
            
            device = self.devices[device_idx]
            
            # 创建配置操作实例
            self.config_operator = ConfigOperator(device["ip"], device["username"], device["password"])
            
            # 测试连接
            success = self.config_operator.test_connection()
            
            if success:
                self.log_message(f"成功连接到设备: {device['name']} ({device['ip']})")
                QMessageBox.information(self, "连接成功", f"成功连接到设备: {device['name']} ({device['ip']})")
            else:
                self.log_message(f"连接设备失败: {device['name']} ({device['ip']})")
                QMessageBox.warning(self, "连接失败", f"无法连接到设备: {device['name']} ({device['ip']})")
                
        except Exception as e:
            self.log_message(f"连接错误: {str(e)}")
            QMessageBox.critical(self, "连接错误", f"发生错误: {str(e)}")
    
    def add_acl_rule(self):
        """添加ACL规则"""
        if not self._check_connection():
            return
            
        try:
            # 获取ACL参数
            acl_number = self.acl_number.value()
            rule_number = self.acl_rule.value()
            action = self.acl_action.currentText()
            source = self.acl_source.text().strip()
            
            if not source:
                self.log_message("错误: 源地址不能为空")
                QMessageBox.warning(self, "参数错误", "源地址不能为空")
                return
            
            # 高级ACL特有参数
            dest = protocol = port = None
            if self.advanced_acl_radio.isChecked():
                dest = self.acl_dest.text().strip()
                protocol = self.acl_protocol.currentText()
                port = self.acl_port.text().strip()
            
            # 添加ACL规则
            success = self.config_operator.add_acl_rule(
                acl_number, 
                rule_number, 
                action, 
                source, 
                dest, 
                protocol, 
                port
            )
            
            if success:
                self.log_message(f"成功添加ACL规则: {acl_number}-{rule_number}")
                QMessageBox.information(self, "添加成功", f"成功添加ACL规则: {acl_number}-{rule_number}")
            else:
                self.log_message(f"添加ACL规则失败")
                QMessageBox.warning(self, "添加失败", "添加ACL规则失败")
                
        except Exception as e:
            self.log_message(f"添加ACL错误: {str(e)}")
            QMessageBox.critical(self, "添加错误", f"发生错误: {str(e)}")
    
    def view_acl(self):
        """查看当前ACL配置"""
        if not self._check_connection():
            return
            
        try:
            # 获取ACL配置
            acl_config = self.config_operator.get_acl_config()
            
            if acl_config:
                self.log_message("当前ACL配置:")
                self.log_message(acl_config)
            else:
                self.log_message("获取ACL配置失败")
                QMessageBox.warning(self, "查询失败", "获取ACL配置失败")
                
        except Exception as e:
            self.log_message(f"查询ACL错误: {str(e)}")
            QMessageBox.critical(self, "查询错误", f"发生错误: {str(e)}")
    
    def apply_acl_to_interface(self):
        """将ACL应用到接口"""
        if not self._check_connection():
            return
            
        try:
            # 获取ACL参数
            acl_number = self.acl_number.value()
            interface = self.acl_interface.currentText()
            direction = self.acl_direction.currentText()
            
            # 应用ACL到接口
            success = self.config_operator.apply_acl_to_interface(acl_number, interface, direction)
            
            if success:
                self.log_message(f"成功将ACL {acl_number} 应用到接口 {interface} 的 {direction} 方向")
                QMessageBox.information(self, "应用成功", f"成功将ACL {acl_number} 应用到接口 {interface} 的 {direction} 方向")
            else:
                self.log_message(f"应用ACL到接口失败")
                QMessageBox.warning(self, "应用失败", "应用ACL到接口失败")
                
        except Exception as e:
            self.log_message(f"应用ACL错误: {str(e)}")
            QMessageBox.critical(self, "应用错误", f"发生错误: {str(e)}")
    
    def configure_nat(self):
        """配置NAT"""
        if not self._check_connection():
            return
            
        try:
            # 获取NAT类型
            nat_type = ""
            if self.static_nat_radio.isChecked():
                nat_type = "static"
            elif self.dynamic_nat_radio.isChecked():
                nat_type = "dynamic"
            else:
                nat_type = "pat"
            
            # 获取接口配置
            inside_interface = self.nat_inside_interface.currentText()
            outside_interface = self.nat_outside_interface.currentText()
            
            # 根据NAT类型获取不同参数
            nat_params = {}
            if nat_type == "static":
                inside_ip = self.static_inside_ip.text().strip()
                outside_ip = self.static_outside_ip.text().strip()
                
                if not inside_ip or not outside_ip:
                    self.log_message("错误: 内部地址和外部地址不能为空")
                    QMessageBox.warning(self, "参数错误", "内部地址和外部地址不能为空")
                    return
                
                nat_params = {
                    "inside_ip": inside_ip,
                    "outside_ip": outside_ip
                }
                
            elif nat_type == "dynamic":
                inside_network = self.dynamic_inside_network.text().strip()
                pool_name = self.dynamic_pool_name.text().strip()
                pool_start = self.dynamic_pool_start.text().strip()
                pool_end = self.dynamic_pool_end.text().strip()
                
                if not inside_network or not pool_name or not pool_start or not pool_end:
                    self.log_message("错误: 内部网络、地址池名称、起始地址和结束地址不能为空")
                    QMessageBox.warning(self, "参数错误", "内部网络、地址池名称、起始地址和结束地址不能为空")
                    return
                
                nat_params = {
                    "inside_network": inside_network,
                    "pool_name": pool_name,
                    "pool_start": pool_start,
                    "pool_end": pool_end
                }
                
            else:  # PAT
                inside_network = self.pat_inside_network.text().strip()
                outside_interface = self.pat_outside_interface.currentText()
                
                if not inside_network:
                    self.log_message("错误: 内部网络不能为空")
                    QMessageBox.warning(self, "参数错误", "内部网络不能为空")
                    return
                
                nat_params = {
                    "inside_network": inside_network,
                    "outside_interface": outside_interface
                }
            
            # 配置NAT
            success = self.config_operator.configure_nat(
                nat_type, 
                inside_interface, 
                outside_interface, 
                nat_params
            )
            
            if success:
                self.log_message(f"成功配置 {nat_type} NAT")
                QMessageBox.information(self, "配置成功", f"成功配置 {nat_type} NAT")
            else:
                self.log_message(f"配置NAT失败")
                QMessageBox.warning(self, "配置失败", "配置NAT失败")
                
        except Exception as e:
            self.log_message(f"配置NAT错误: {str(e)}")
            QMessageBox.critical(self, "配置错误", f"发生错误: {str(e)}")
    
    def view_nat(self):
        """查看NAT配置"""
        if not self._check_connection():
            return
            
        try:
            # 获取NAT配置
            nat_config = self.config_operator.get_nat_config()
            
            if nat_config:
                self.log_message("当前NAT配置:")
                self.log_message(nat_config)
            else:
                self.log_message("获取NAT配置失败")
                QMessageBox.warning(self, "查询失败", "获取NAT配置失败")
                
        except Exception as e:
            self.log_message(f"查询NAT错误: {str(e)}")
            QMessageBox.critical(self, "查询错误", f"发生错误: {str(e)}")
    
    def configure_stp_global(self):
        """配置全局STP"""
        if not self._check_connection():
            return
            
        try:
            # 获取STP参数
            mode = self.stp_mode.currentText()
            priority = self.stp_priority.value()
            forward_time = self.stp_forward_time.value()
            hello_time = self.stp_hello_time.value()
            max_age = self.stp_max_age.value()
            
            # MSTP特有参数
            mstp_params = {}
            if mode == "mstp" and self.mstp_radio.isChecked():
                region = self.mstp_region.text().strip()
                revision = self.mstp_revision.value()
                instance = self.mstp_instance.value()
                vlan_mapping = self.mstp_vlan.text().strip()
                
                if not region or not vlan_mapping:
                    self.log_message("错误: MSTP区域名称和VLAN映射不能为空")
                    QMessageBox.warning(self, "参数错误", "MSTP区域名称和VLAN映射不能为空")
                    return
                
                mstp_params = {
                    "region": region,
                    "revision": revision,
                    "instance": instance,
                    "vlan_mapping": vlan_mapping
                }
            
            # 配置全局STP
            success = self.config_operator.configure_stp_global(
                mode, 
                priority, 
                forward_time, 
                hello_time, 
                max_age, 
                mstp_params
            )
            
            if success:
                self.log_message(f"成功配置全局 {mode.upper()} 参数")
                QMessageBox.information(self, "配置成功", f"成功配置全局 {mode.upper()} 参数")
            else:
                self.log_message(f"配置全局STP失败")
                QMessageBox.warning(self, "配置失败", "配置全局STP失败")
                
        except Exception as e:
            self.log_message(f"配置STP错误: {str(e)}")
            QMessageBox.critical(self, "配置错误", f"发生错误: {str(e)}")
    
    def configure_stp_interface(self):
        """配置接口STP"""
        if not self._check_connection():
            return
            
        try:
            # 获取接口STP参数
            interface = self.stp_interface.currentText()
            port_priority = self.stp_port_priority.value()
            port_cost = self.stp_port_cost.value()
            edge_port = self.stp_edge_port.isChecked()
            bpdu_guard = self.stp_bpdu_guard.isChecked()
            root_guard = self.stp_root_guard.isChecked()
            
            # 配置接口STP
            success = self.config_operator.configure_stp_interface(
                interface, 
                port_priority, 
                port_cost, 
                edge_port, 
                bpdu_guard, 
                root_guard
            )
            
            if success:
                self.log_message(f"成功配置接口 {interface} 的STP参数")
                QMessageBox.information(self, "配置成功", f"成功配置接口 {interface} 的STP参数")
            else:
                self.log_message(f"配置接口STP失败")
                QMessageBox.warning(self, "配置失败", "配置接口STP失败")
                
        except Exception as e:
            self.log_message(f"配置接口STP错误: {str(e)}")
            QMessageBox.critical(self, "配置错误", f"发生错误: {str(e)}")
    
    def view_stp(self):
        """查看STP状态"""
        if not self._check_connection():
            return
            
        try:
            # 获取STP状态
            stp_status = self.config_operator.get_stp_status()
            
            if stp_status:
                self.log_message("当前STP状态:")
                self.log_message(stp_status)
            else:
                self.log_message("获取STP状态失败")
                QMessageBox.warning(self, "查询失败", "获取STP状态失败")
                
        except Exception as e:
            self.log_message(f"查询STP错误: {str(e)}")
            QMessageBox.critical(self, "查询错误", f"发生错误: {str(e)}")
    
    def view_acl(self):
        """查看当前ACL配置"""
        if not self._check_connection():
            return
            
        try:
            # 获取ACL配置
            acl_config = self.config_operator.get_acl_config()
            
            if acl_config:
                self.log_message("当前ACL配置:")
                self.log_message(acl_config)
            else:
                self.log_message("获取ACL配置失败")
                QMessageBox.warning(self, "查询失败", "获取ACL配置失败")
                
        except Exception as e:
            self.log_message(f"查询ACL错误: {str(e)}")
            QMessageBox.critical(self, "查询错误", f"发生错误: {str(e)}")
    
    def apply_acl_to_interface(self):
        """将ACL应用到接口"""
        if not self._check_connection():
            return
            
        try:
            # 获取ACL参数
            acl_number = self.acl_number.value()
            interface = self.acl_interface.currentText()
            direction = self.acl_direction.currentText()
            
            # 应用ACL到接口
            success = self.config_operator.apply_acl_to_interface(acl_number, interface, direction)
            
            if success:
                self.log_message(f"成功将ACL {acl_number} 应用到接口 {interface} 的 {direction} 方向")
                QMessageBox.information(self, "应用成功", f"成功将ACL {acl_number} 应用到接口 {interface} 的 {direction} 方向")
            else:
                self.log_message(f"应用ACL到接口失败")
                QMessageBox.warning(self, "应用失败", "应用ACL到接口失败")
                
        except Exception as e:
            self.log_message(f"应用ACL错误: {str(e)}")
            QMessageBox.critical(self, "应用错误", f"发生错误: {str(e)}")
    
    def _check_connection(self):
        """检查是否已连接设备"""
        if not self.config_operator:
            self.log_message("错误: 未连接设备，请先测试连接")
            QMessageBox.warning(self, "未连接", "请先连接设备")
            return False
        return True
    
    def log_message(self, message, level="info"):
        """记录日志消息"""
        # 根据级别设置颜色
        color = "black"
        if level == "error":
            color = "red"
        elif level == "success":
            color = "green"
        elif level == "warning":
            color = "orange"
        
        # 添加带颜色的消息
        self.log_text.append(f'<span style="color: {color};">{message}</span>')