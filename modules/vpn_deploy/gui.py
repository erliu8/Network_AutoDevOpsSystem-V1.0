# a_window_app.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                             QLineEdit, QPushButton, QMessageBox, QGridLayout, QProgressDialog, QTextEdit, QApplication)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont

# 修改导入语句
import sys
import os
from pathlib import Path
import time

# 添加模块路径
sys.path.append(str(Path(__file__).parent.parent.parent))
from core.business.vpn_service import VPNService


class VPNConfigApp(QWidget):
    def __init__(self):
        super().__init__()
        self.vpn_service = VPNService()  # 创建VPN服务实例
        self.init_ui()
        self.setMinimumSize(QSize(1200, 900))

    def init_ui(self):
        self.setWindowTitle("VPN配置系统")
        self.setStyleSheet("""
            QWidget {
                font-family: '微软雅黑';
                font-size: 16px;
            }
            QLabel {
                font-weight: bold;
            }
            QLineEdit, QComboBox {
                padding: 8px;
                min-width: 300px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px;
                border-radius: 6px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QTextEdit {
                font-family: Consolas, monospace;
                font-size: 14px;
                background-color: #f8f8f8;
                border: 1px solid #ccc;
                padding: 5px;
            }
        """)

        # 初始化输入控件
        self.vpn_name_input = QLineEdit()
        self.vlan_input = QLineEdit()
        self.rt_input = QLineEdit()
        self.rd_input = QLineEdit()
        self.ip_input = QLineEdit()
        self.mask_input = QLineEdit()

        # 创建日志区域
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(200)
        
        # 创建主分割器布局
        from PyQt5.QtWidgets import QSplitter
        splitter = QSplitter(Qt.Vertical)
        
        # 顶部配置面板
        config_panel = QWidget()
        config_layout = QVBoxLayout(config_panel)
        config_layout.setContentsMargins(40, 30, 40, 30)
        config_layout.setSpacing(30)

        # 标题
        title = QLabel("VPN配置系统")
        title.setFont(QFont("微软雅黑", 28, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 30px;")
        config_layout.addWidget(title)

        # 主内容布局
        content_layout = QGridLayout()
        content_layout.setHorizontalSpacing(50)
        content_layout.setVerticalSpacing(30)

        # 设备选择
        content_layout.addWidget(QLabel("选择目标设备:"), 0, 0)
        self.device_combo = QComboBox()
        self.device_combo.addItems([
            "地域1出口路由器 (10.1.200.1)",
            "地域2出口路由器 (10.1.18.1)"
        ])
        self.device_combo.setFont(QFont("微软雅黑", 16))
        content_layout.addWidget(self.device_combo, 0, 1)

        # 输入字段
        input_fields = [
            ("VPN实例名称:", self.vpn_name_input),
            ("VLAN ID:", self.vlan_input),
            ("RT (格式如 100:1):", self.rt_input),
            ("RD (格式如 200:1):", self.rd_input),
            ("IP地址:", self.ip_input),
            ("子网掩码:", self.mask_input)
        ]

        for row, (label_text, input_widget) in enumerate(input_fields, start=1):
            label = QLabel(label_text)
            label.setFont(QFont("微软雅黑", 16))
            content_layout.addWidget(label, row, 0)
            input_widget.setFont(QFont("微软雅黑", 14))
            input_widget.setMinimumHeight(40)
            content_layout.addWidget(input_widget, row, 1)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        btn_submit = QPushButton("提交配置")
        btn_submit.setFixedSize(200, 60)
        btn_submit.clicked.connect(self.validate_input)
        button_layout.addWidget(btn_submit)
        button_layout.addStretch()

        config_layout.addLayout(content_layout)
        config_layout.addLayout(button_layout)
        
        # 日志区域
        log_panel = QWidget()
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(20, 10, 20, 20)
        
        log_title = QLabel("操作日志")
        log_title.setFont(QFont("微软雅黑", 16, QFont.Bold))
        log_title.setAlignment(Qt.AlignCenter)
        log_layout.addWidget(log_title)
        log_layout.addWidget(self.log_area)
        
        # 清除日志按钮
        clear_log_btn = QPushButton("清除日志")
        clear_log_btn.clicked.connect(self.log_area.clear)
        log_layout.addWidget(clear_log_btn)
        
        # 添加组件到分割器
        splitter.addWidget(config_panel)
        splitter.addWidget(log_panel)
        splitter.setSizes([600, 300])  # 设置初始高度比例
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(splitter)
        
        # 添加初始日志消息
        self.add_log("VPN配置系统已初始化，请填写配置信息")

    def add_log(self, message):
        """添加日志到日志区域"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_text = f"[{timestamp}] {message}"
        self.log_area.append(log_text)
        # 自动滚动到底部
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())
        # 刷新UI
        QApplication.processEvents()

    def validate_input(self):
        """输入验证与配置触发"""
        device = self.device_combo.currentText()
        
        # 获取输入参数
        vpn_name = self.vpn_name_input.text()
        vlan = self.vlan_input.text()
        rt = self.rt_input.text()
        rd = self.rd_input.text()
        current_ip = self.ip_input.text()
        current_mask = self.mask_input.text()

        # 验证主输入
        if not self._check_inputs(vpn_name, vlan, rt, rd, current_ip, current_mask):
            return

        # 准备配置参数
        current_config = {
            "vpn_name": vpn_name,
            "rt": rt,
            "rd": rd,
            "vlan": vlan,
            "ip_address": current_ip,
            "subnet_mask": self._convert_mask(current_mask)
        }

        # 记录开始配置
        self.add_log(f"开始配置VPN: {vpn_name} - 设备: {device}")
        self.add_log(f"配置参数: {current_config}")

        # 创建进度对话框
        progress = QProgressDialog("正在配置VPN，请稍候...", "取消", 0, 0, self)
        progress.setWindowTitle("配置进行中")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)  # 禁用取消按钮
        progress.setAutoClose(True)
        progress.show()
        
        # 使用QTimer处理长时间操作的UI更新
        def perform_configuration():
            try:
                # 使用VPN服务配置设备
                # 注册用于接收设备配置输出的处理方法
                def handle_command_output(output):
                    self.add_log(output)
                
                # 使用VPN服务配置设备
                success, message = self.vpn_service.configure_vpn(device, current_config, handle_command_output)
                
                # 关闭进度对话框
                progress.close()
                
                # 显示结果
                if success:
                    self.add_log(f"配置成功: {message}")
                    QMessageBox.information(
                        self, "成功",
                        f"设备配置完成！\n"
                        f"设备: {device}\n"
                        f"接口: {current_ip}/{current_mask}\n\n"
                        f"消息: {message}"
                    )
                    self._clear_inputs()
                else:
                    self.add_log(f"配置失败: {message}")
                    QMessageBox.critical(self, "错误", message)
            except Exception as e:
                progress.close()
                error_msg = f"配置失败: {str(e)}"
                self.add_log(error_msg)
                QMessageBox.critical(self, "错误", error_msg)
        
        # 使用QTimer启动配置，以便先显示进度对话框
        QTimer.singleShot(100, perform_configuration)

    def _convert_mask(self, mask):
        """统一转换掩码格式"""
        if mask.isdigit():
            return mask
        else:
            return self._dotmask_to_cidr(mask)

    def _dotmask_to_cidr(self, mask):
        """点分十进制转CIDR"""
        try:
            octets = list(map(int, mask.split('.')))
            binary_str = ''.join([format(o, '08b') for o in octets])
            return str(binary_str.count('1'))
        except:
            raise ValueError("无效的子网掩码")

    def _check_inputs(self, vpn_name, vlan, rt, rd, ip, mask):
        """主输入验证"""
        if not all([vpn_name, vlan, rt, rd, ip, mask]):
            QMessageBox.warning(self, "错误", "所有字段必须填写")
            return False

        # 验证VLAN ID
        try:
            if not 2 <= int(vlan) <= 4094:
                raise ValueError
        except:
            QMessageBox.warning(self, "错误", "VLAN ID必须为2-4094的整数")
            return False

        # 验证RT/RD格式
        if rt.count(':') != 1 or rd.count(':') != 1:
            QMessageBox.warning(self, "错误", "RT/RD格式应为X:X")
            return False

        # 验证IP地址
        try:
            octets = ip.split('.')
            if len(octets) != 4 or any(not 0 <= int(o) <= 255 for o in octets):
                raise ValueError
        except:
            QMessageBox.warning(self, "错误", "IP地址格式错误")
            return False

        # 验证子网掩码
        try:
            if mask.isdigit():
                if not 0 <= int(mask) <= 32:
                    raise ValueError
            else:
                self._dotmask_to_cidr(mask)
        except:
            QMessageBox.warning(self, "错误", "子网掩码格式错误")
            return False

        return True

    def _clear_inputs(self):
        """清空所有输入框"""
        self.vpn_name_input.clear()
        self.vlan_input.clear()
        self.rt_input.clear()
        self.rd_input.clear()
        self.ip_input.clear()
        self.mask_input.clear()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    window = VPNConfigApp()
    window.show()
    sys.exit(app.exec_())
