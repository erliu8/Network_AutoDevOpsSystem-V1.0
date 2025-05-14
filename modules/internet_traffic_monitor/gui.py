# main_window.py
import sys
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox,
                             QComboBox)  # 添加QComboBox导入
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
import matplotlib

matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
# 导入监控服务
from core.business.monitor_service import MonitorService
# 导入设备服务
from core.services.device_service import DeviceService

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


class TrafficMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.monitor_service = MonitorService()  # 使用监控服务
        self.color_map = {"input": "#4A90D6", "output": "#50E3C2"}
        self.current_monitored_ip = None  # 添加当前监控的设备IP变量
        self.error_shown = False  # 添加错误弹窗标记，防止多个弹窗
        
        # 获取设备列表
        self.devices = DeviceService.get_all_devices()
        if not self.devices:
            print("未从数据库获取到设备列表，使用默认设备列表")
            self.devices = []
        else:
            print(f"从数据库获取到 {len(self.devices)} 个设备")
            
        self.initUI()
        self.setup_chart()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.check_data_update)
        
        # 连接监控服务信号
        self.monitor_service.traffic_data_updated.connect(self.update_chart)
        self.monitor_service.traffic_connection_status.connect(self.handle_connection_status)

    def initUI(self):
        self.setWindowTitle("流量监控系统")
        self.setGeometry(100, 100, 1800, 1000)  # 增加默认窗口大小，以便显示更多接口

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # 控制面板
        control_layout = QHBoxLayout()
        
        # 替换IP输入框为设备类型下拉框
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(300)
        
        # 填充设备下拉框
        device_types = set()
        for device in self.devices:
            device_type = device.get('type', '')
            if device_type:
                # 如果设备有描述信息，添加到类型中
                if device.get('description'):
                    display_text = f"{device_type} ({device.get('description')})"
                else:
                    display_text = device_type
                
                # 添加到下拉框，并存储设备信息作为用户数据
                self.device_combo.addItem(display_text, device)
                device_types.add(device_type)
        
        # 如果没有设备，添加默认设备
        if not device_types:
            default_devices = [
                {"ip": "10.1.0.3", "type": "地域1核心交换机"},
                {"ip": "10.1.200.1", "type": "地域1出口路由器"},
                {"ip": "10.1.18.1", "type": "地域2出口路由器"}
            ]
            for device in default_devices:
                self.device_combo.addItem(device["type"], device)
        
        self.monitor_btn = QPushButton("启动监控", clicked=self.toggle_monitoring)

        control_layout.addWidget(QLabel("选择设备:"))
        control_layout.addWidget(self.device_combo)
        control_layout.addWidget(self.monitor_btn)

        # 图表区域
        self.figure = Figure(figsize=(18, 12))  # 增加图表高度
        self.canvas = FigureCanvas(self.figure)
        self.ax_input = self.figure.add_subplot(211)
        self.ax_output = self.figure.add_subplot(212)

        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.canvas)

    def setup_chart(self):
        """初始化图表配置"""
        for ax in [self.ax_input, self.ax_output]:
            ax.clear()
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.set_ylabel('Bytes/sec')
            ax.tick_params(axis='x', rotation=45)
            ax.set_ylim(0, 100)  # 设置初始Y轴范围
        self.ax_input.set_title("实时接口入流量 (bytes/sec)")
        self.ax_output.set_title("实时接口出流量 (bytes/sec)")
        self.figure.tight_layout()
        self.canvas.draw()

    def toggle_monitoring(self):
        # 获取选中的设备
        current_index = self.device_combo.currentIndex()
        if current_index < 0:
            QMessageBox.critical(self, "错误", "请选择一个设备")
            return
            
        device = self.device_combo.itemData(current_index)
        if not device or not device.get("ip"):
            QMessageBox.critical(self, "错误", "所选设备没有有效的IP地址")
            return
            
        ip = device.get("ip")
        device_type = device.get("type", "未知设备")

        if self.monitor_btn.text() == "启动监控":
            try:
                # 重置错误标记
                self.error_shown = False
                
                print(f"尝试连接到设备: {device_type} (IP: {ip})")
                # 使用监控服务启动流量监控
                # 如果设备有用户名和密码，使用设备的凭据
                username = device.get("username", "1")
                password = device.get("password", "1")
                
                # 先停止所有现有监控，确保图表不会混乱
                self.monitor_service.stop_traffic_monitor()
                
                # 设置当前监控的设备IP
                self.current_monitored_ip = ip
                
                # 启动新的监控
                success = self.monitor_service.start_traffic_monitor(ip, username, password)
                
                if not success:
                    self.current_monitored_ip = None
                    raise ConnectionError("连接失败")

                self.monitor_btn.setText("停止监控")
                self.setup_chart()  # 重置图表
                self.update_timer.start(1000)
                print(f"监控已启动: {device_type}")

            except Exception as e:
                import traceback
                print(f"连接错误: {str(e)}")
                print(traceback.format_exc())
                self.show_error_message(f"连接失败: {str(e)}")
        else:
            print("停止监控")
            # 清除当前监控的设备IP
            self.current_monitored_ip = None
            # 使用监控服务停止流量监控
            self.monitor_service.stop_traffic_monitor()
            self.monitor_btn.setText("启动监控")
            self.update_timer.stop()
    
    def handle_connection_status(self, ip, connected):
        """处理连接状态信号"""
        # 如果不是当前监控的设备，忽略信号
        if self.current_monitored_ip is None or ip != self.current_monitored_ip:
            print(f"忽略非当前监控设备 {ip} 的状态更新")
            return
            
        print(f"收到设备 {ip} 连接状态更新: {'已连接' if connected else '未连接'}")
        if connected:
            # 连接成功，重置错误标记
            self.error_shown = False
            # 连接成功
            self.monitor_btn.setText("停止监控")
            # 不显示成功弹窗，避免打扰用户
        else:
            # 连接失败，如果没有显示过错误，则显示
            if not self.error_shown:
                self.show_error_message(f"连接到设备 {ip} 失败或已断开")
                self.error_shown = True
                
            # 更新UI状态，只有在按钮文本不是"启动监控"时才更新
            if self.monitor_btn.text() != "启动监控":
                self.monitor_btn.setText("启动监控")
                
            # 停止定时器，如果正在运行
            if self.update_timer.isActive():
                self.update_timer.stop()
            
            # 重置当前监控设备
            self.current_monitored_ip = None
            
            # 确保监控服务停止
            self.monitor_service.stop_traffic_monitor()
    
    def show_error_message(self, message):
        """显示错误消息，确保只显示一次"""
        QMessageBox.critical(self, "错误", message)
        
    def update_chart(self, data):
        """更新图表（线程安全）"""
        # 如果没有正在监控的设备，忽略数据更新
        if self.current_monitored_ip is None:
            print("没有正在监控的设备，忽略数据更新")
            return
            
        try:
            if not data:
                print("收到空数据")
                return
                
            # 检查数据结构是否符合预期
            if not isinstance(data, dict):
                print(f"收到非预期数据类型: {type(data)}")
                return
                
            # 添加调试信息
            print(f"收到数据更新: {len(data)}个接口")
            
            # 数据验证 - 确保每个接口都有input和output字段
            for iface, stats in list(data.items()):
                if 'input' not in stats or 'output' not in stats:
                    print(f"接口 {iface} 数据不完整，已移除")
                    del data[iface]
            
            if not data:
                print("数据验证后没有有效数据")
                return

            # 接口排序
            interfaces = sorted(data.keys(),
                                key=lambda x: [int(n) if n.isdigit() else n for n in re.findall(r'\d+|\D+', x)])

            # 提取数据
            input_rates = [data[iface]["input"] for iface in interfaces]
            output_rates = [data[iface]["output"] for iface in interfaces]
            
            print(f"处理后的数据: 接口数量={len(interfaces)}")

            # 清除并重置图表
            self.ax_input.clear()
            self.ax_output.clear()

            # 配置通用参数 - 根据接口数量自动调整
            interface_count = len(interfaces)
            
            # 动态调整条形图宽度
            if interface_count <= 15:
                bar_width = 0.8
            elif interface_count <= 30:
                bar_width = 0.6
            else:
                bar_width = 0.4  # 接口非常多时，使用更窄的条形图
            
            # 根据接口数量动态调整字体大小
            if interface_count <= 15:
                font_size = 9
            elif interface_count <= 30:
                font_size = 7
            elif interface_count <= 50:
                font_size = 6
            else:
                font_size = 5  # 接口极多时使用最小字体

            # 设置Y轴范围 - 确保有最小值
            max_input = max(input_rates) if input_rates else 100
            max_output = max(output_rates) if output_rates else 100
            self.ax_input.set_ylim(0, max(max_input * 1.2 + 1, 100))
            self.ax_output.set_ylim(0, max(max_output * 1.2 + 1, 100))

            # 设置网格
            self.ax_input.grid(True, linestyle='--', alpha=0.6)
            self.ax_output.grid(True, linestyle='--', alpha=0.6)

            # 设置标题和标签
            self.ax_input.set_title(f"实时接口入流量 (bytes/sec) - 共{interface_count}个接口")
            self.ax_output.set_title(f"实时接口出流量 (bytes/sec) - 共{interface_count}个接口")
            self.ax_input.set_ylabel('Bytes/sec')
            self.ax_output.set_ylabel('Bytes/sec')

            # 设置X轴 - 使用数字索引而不是接口名称作为位置
            x = list(range(len(interfaces)))
            
            # 当接口数量过多时，调整x轴刻度密度
            if interface_count <= 20:
                self.ax_input.set_xticks(x)
                self.ax_output.set_xticks(x)
            else:
                # 对于大量接口，只显示部分刻度，避免拥挤
                step = max(1, interface_count // 20)  # 计算合适的步长
                self.ax_input.set_xticks(x[::step])
                self.ax_output.set_xticks(x[::step])
                # 如果接口太多，考虑只显示一部分标签
                if interface_count > 50:
                    interfaces_display = []
                    for i, iface in enumerate(interfaces):
                        if i % step == 0:
                            interfaces_display.append(iface)
                        else:
                            interfaces_display.append("")
                    interfaces = interfaces_display
            
            # 当接口较多时，设置X轴标签旋转角度更大
            rotation_angle = 45 if interface_count <= 30 else 90
            
            self.ax_input.set_xticklabels(interfaces, rotation=rotation_angle, 
                                          ha='right' if rotation_angle < 90 else 'center', 
                                          fontsize=font_size)
            self.ax_output.set_xticklabels(interfaces, rotation=rotation_angle, 
                                           ha='right' if rotation_angle < 90 else 'center', 
                                           fontsize=font_size)

            # 绘制条形图 - 使用数字索引作为位置
            bars_input = self.ax_input.bar(x, input_rates, width=bar_width, 
                                         color=self.color_map["input"], edgecolor='black')
            bars_output = self.ax_output.bar(x, output_rates, width=bar_width,
                                           color=self.color_map["output"], edgecolor='black')

            # 添加数值标签，只有接口较少时才显示数值
            if interface_count <= 15:
                self.ax_input.bar_label(bars_input, fmt='%d', padding=3, fontsize=font_size)
                self.ax_output.bar_label(bars_output, fmt='%d', padding=3, fontsize=font_size)

            # 调整布局并刷新
            self.figure.tight_layout()
            self.canvas.draw()
            self.canvas.flush_events()  # 强制刷新

            print("图表更新完成")

        except Exception as e:
            import traceback
            print(f"图表更新失败: {str(e)}")
            print(traceback.format_exc())  # 打印完整的错误堆栈

    def check_data_update(self):
        """定时检查数据更新"""
        # 保留空实现以保持定时器功能
        pass
        
    # 添加run方法以支持模块接口
    def run(self):
        self.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TrafficMonitorApp()
    window.show()
    sys.exit(app.exec_())