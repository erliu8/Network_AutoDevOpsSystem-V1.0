# Integral_Network_Arrangement.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QLabel
from PyQt5.QtCore import Qt, QRectF, pyqtSlot
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath

# 导入连通性检测模块
from core.business.communication_detection import get_detector_instance

# 在文件开头添加导入
from core.business.thread_factory import ThreadFactory

class NetworkTopologyView(QGraphicsView):
    """网络拓扑视图类"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # 创建场景 - 增加场景大小以允许更松散的布局
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(QRectF(0, 0, 3000, 1800))
        self.setScene(self.scene)
        
        # 设置视图属性
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        # 优化配色方案 - 更专业的网络图配色
        self.enterprise_a_color = QColor(0, 129, 201)  # 专业蓝色
        self.enterprise_b_color = QColor(236, 0, 140)  # 品牌紫红色
        self.error_color = QColor(255, 0, 0)  # 保持红色不变
        self.other_device_color = QColor(95, 95, 95)  # 深灰色，更专业
        
        # 添加背景色，提高可读性
        self.setBackgroundBrush(QBrush(QColor(248, 248, 248)))
        
        # 添加初始缩放以便于查看整个拓扑
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.scale(0.85, 0.85)  # 增大初始缩放比例
        
        # 存储连接线对象的字典，用于后续更新颜色
        self.connections = {}
        
        # 存储设备节点对象的字典，用于后续更新状态
        self.devices = {}
        
        # 初始化拓扑
        self.init_topology()
        
        # 启动连通性检测并连接信号
        try:
            self.detector = get_detector_instance()
            self.detector.detection_result.connect(self.update_connection_status)
            self.detector.start_detection()
            print("网络拓扑视图已连接到连通性检测器")
        except Exception as e:
            print(f"连接到连通性检测器时出错: {str(e)}")
        
    def init_topology(self):
        """初始化网络拓扑图"""
        # 清除场景
        self.scene.clear()
        self.connections = {}  # 清空连接线字典
        self.devices = {}      # 清空设备节点字典
        
        # 调整区域背景位置和大小，确保能够容纳所有设备
        # 增加高度以确保接入交换机在区域内
        self.add_region(300, 350, 1000, 1050, QColor(235, 241, 250), "地域1")
        self.add_region(1800, 350, 1000, 1050, QColor(250, 235, 240), "地域2")
        # 运营商区域放到上面，不与其他区域重叠
        self.add_region(900, 50, 1200, 200, QColor(235, 250, 235), "运营商")
        
        # 添加设备节点 - 地域1
        # 向上移动设备，确保所有设备都在区域内
        self.add_device(800, 500, "地域1出口路由器", "router", self.other_device_color)
        self.add_device(800, 700, "地域1核心交换机", "switch", self.other_device_color)
        
        # 加大汇聚交换机之间的水平间距
        self.add_device(600, 850, "地域1汇聚交换机A", "switch", self.enterprise_a_color)
        self.add_device(1000, 850, "地域1汇聚交换机B", "switch", self.enterprise_b_color)
        
        # 接入交换机加大水平间距，避免重叠，向上移动以确保在区域内
        self.add_device(550, 1050, "接入交换机A1", "switch", self.enterprise_a_color)
        self.add_device(700, 1050, "接入交换机A2", "switch", self.enterprise_a_color)
        self.add_device(900, 1050, "接入交换机B1", "switch", self.enterprise_b_color)
        self.add_device(1050, 1050, "接入交换机B2", "switch", self.enterprise_b_color)
        
        # 添加设备节点 - 地域2
        self.add_device(2100, 500, "地域2出口路由器", "router", self.other_device_color)
        self.add_device(2000, 700, "地域2核心交换机A", "switch", self.enterprise_a_color)
        self.add_device(2400, 700, "地域2核心交换机B", "switch", self.enterprise_b_color)
        
        # 接入交换机加大水平间距，避免重叠
        self.add_device(1900, 850, "接入交换机A3", "switch", self.enterprise_a_color)
        self.add_device(2100, 850, "接入交换机A4", "switch", self.enterprise_a_color)
        self.add_device(2300, 850, "接入交换机B3", "switch", self.enterprise_b_color) 
        self.add_device(2500, 850, "接入交换机B4", "switch", self.enterprise_b_color)
        
        # 添加运营商设备 - 更均匀的分布
        self.add_device(1050, 150, "PE1", "router", self.other_device_color)
        self.add_device(1350, 150, "PE", "router", self.other_device_color)
        self.add_device(1650, 150, "PE2", "router", self.other_device_color)
        
        # 添加连接线 - 地域1
        # 核心交换机 -> 出口路由器 (企业A)
        self.add_connection(800, 650, 800, 550, "area1_core_to_router_a", "企业A")
        
        # 核心交换机 -> 汇聚交换机A (企业A)
        self.add_connection(750, 750, 650, 800, "area1_converge_to_core_a", "企业A")
        
        # 核心交换机 -> 汇聚交换机B (企业B)
        self.add_connection(850, 750, 950, 800, "area1_converge_to_core_b", "企业B")
        
        # 汇聚交换机A -> 接入交换机A1 (企业A)
        self.add_connection(580, 900, 565, 1000, "area1_access_to_converge_a", "企业A")
        
        # 汇聚交换机A -> 接入交换机A2 (企业A)
        self.add_connection(620, 900, 680, 1000, "area1_access_to_converge_a", "企业A")
        
        # 汇聚交换机B -> 接入交换机B1 (企业B)
        self.add_connection(980, 900, 920, 1000, "area1_access_to_converge_b", "企业B")
        
        # 汇聚交换机B -> 接入交换机B2 (企业B)
        self.add_connection(1020, 900, 1035, 1000, "area1_access_to_converge_b", "企业B")
        
        # 添加连接线 - 地域2
        # 出口路由器 -> 核心交换机A (企业A)
        self.add_connection(2100, 550, 2050, 650, "area2_core_to_router_a", "企业A")
        
        # 出口路由器 -> 核心交换机B (企业B)
        self.add_connection(2150, 550, 2350, 650, "area2_core_to_router_b", "企业B")
        
        # 核心交换机A -> 接入交换机A3 (企业A)
        self.add_connection(1980, 750, 1920, 800, "area2_access_to_core_a", "企业A")
        
        # 核心交换机A -> 接入交换机A4 (企业A)
        self.add_connection(2020, 750, 2080, 800, "area2_access_to_core_a", "企业A")
        
        # 核心交换机B -> 接入交换机B3 (企业B)
        self.add_connection(2380, 750, 2320, 800, "area2_access_to_core_b", "企业B")
        
        # 核心交换机B -> 接入交换机B4 (企业B)
        self.add_connection(2420, 750, 2480, 800, "area2_access_to_core_b", "企业B")
        
        # 添加运营商连接 - 调整连接位置适应新布局
        # 地域1出口 -> PE1 (企业A)
        self.add_connection(850, 470, 1000, 180, "area1_to_area2_router_a", "企业A")
        
        # PE1 -> PE
        self.add_connection(1100, 150, 1300, 150, None, None)
        
        # PE -> PE2
        self.add_connection(1400, 150, 1600, 150, None, None)
        
        # PE2 -> 地域2出口 (企业A)
        self.add_connection(1700, 180, 2050, 470, "area1_to_area2_router_a", "企业A")
        
        # 添加企业B的运营商连接
        # 地域1出口 -> PE1 (企业B)
        self.add_connection(850, 530, 1030, 180, "area1_to_area2_router_b", "企业B")
        
        # PE1 -> PE (企业B)
        self.add_connection(1100, 180, 1300, 180, None, None)
        
        # PE -> PE2 (企业B)
        self.add_connection(1400, 180, 1600, 180, None, None)
        
        # PE2 -> 地域2出口 (企业B)
        self.add_connection(1670, 180, 2050, 530, "area1_to_area2_router_b", "企业B")
        
        # 添加图例
        self.add_legend()
    
    def add_device(self, x, y, name, device_type, color):
        """添加设备节点"""
        # 添加设备图形
        if device_type == "router":
            # 路由器使用圆角矩形，更符合网络图标准
            router_width, router_height = 120, 80  # 增大路由器尺寸
            rect_item = self.scene.addRect(x-router_width/2, y-router_height/2, router_width, router_height, 
                                         QPen(Qt.black, 3), # 增大边框宽度 
                                         QBrush(color))
            # 添加路由器图标特征 - 中间横线
            line_item = self.scene.addLine(
                x-router_width/2, y, 
                x+router_width/2, y, 
                QPen(Qt.black, 2)  # 增大线宽
            )
            
            # 存储设备节点
            self.devices[name] = {'shape': rect_item, 'type': device_type, 'decorations': [line_item]}
        else:
            # 交换机使用方形，边缘稍粗
            switch_size = 100  # 增大交换机尺寸
            rect = self.scene.addRect(x-switch_size/2, y-switch_size/2, switch_size, switch_size, 
                                     QPen(Qt.black, 3.5),  # 增大边框宽度
                                     QBrush(color))
            
            # 存储设备节点
            self.devices[name] = {'shape': rect, 'type': device_type}
        
        # 添加设备名称 - 使用更大的字体
        text = self.scene.addText(name)
        text.setFont(QFont("Arial", 12, QFont.Bold))  # 增大字体
        text.setDefaultTextColor(QColor(50, 50, 50))  # 深灰色文字，更易读
        text.setPos(x - text.boundingRect().width()/2, y + 50)  # 调整位置适应更大的设备
    
    def add_connection(self, x1, y1, x2, y2, connection_key=None, enterprise=None):
        """添加设备间连接线，并存储连接线对象以便后续更新颜色"""
        # 默认使用深灰色线，使线条更明显
        pen = QPen(QColor(80, 80, 80), 3, Qt.SolidLine)  # 增大线宽
        
        # 添加连接线
        line = self.scene.addLine(x1, y1, x2, y2, pen)
        
        # 如果提供了连接键和企业信息，则存储连接线对象
        if connection_key and enterprise:
            if connection_key not in self.connections:
                self.connections[connection_key] = []
            self.connections[connection_key].append({
                'line': line,
                'enterprise': enterprise
            })
        
        return line
    
    def add_region(self, x, y, width, height, color, name):
        """添加区域背景"""
        # 添加半透明背景，圆角矩形更美观
        path = QPainterPath()
        path.addRoundedRect(x, y, width, height, 20, 20)  # 增大圆角
        rect = self.scene.addPath(path, 
                                  QPen(QColor(180, 180, 180), 2, Qt.DashLine),  # 增大线宽
                                  QBrush(color))
        rect.setZValue(-1)  # 确保背景在最底层
        
        # 添加区域名称 - 更大字体
        text = self.scene.addText(name)
        text.setFont(QFont("Arial", 16, QFont.Bold))  # 增大字体
        text.setDefaultTextColor(QColor(80, 80, 80))  # 深灰色
        text.setPos(x + 20, y + 15)
    
    def add_legend(self):
        """添加图例"""
        # 将图例放在B3和B4设备的下方，不与地域2区域重叠
        legend_x = 2400
        legend_y = 1200
        legend_width = 320  # 增大图例宽度
        legend_height = 380  # 增大图例高度
        
        # 添加图例背景 - 使用圆角矩形和半透明效果
        path = QPainterPath()
        path.addRoundedRect(legend_x, legend_y, legend_width, legend_height, 10, 10)
        self.scene.addPath(path,
                          QPen(QColor(180, 180, 180), 2),  # 增大线宽
                          QBrush(QColor(255, 255, 255, 240)))
        
        # 添加图例标题
        title = self.scene.addText("网络拓扑图例")
        title.setFont(QFont("Arial", 14, QFont.Bold))  # 增大字体
        title.setDefaultTextColor(QColor(60, 60, 60))
        title.setPos(legend_x + 80, legend_y + 15)
        
        # 添加分隔线
        self.scene.addLine(legend_x + 20, legend_y + 45, legend_x + legend_width - 20, legend_y + 45,
                          QPen(QColor(200, 200, 200), 2))  # 增大线宽
        
        # 企业A设备图例
        self.scene.addRect(legend_x + 20, legend_y + 70, 40, 25,  # 增大示例图形
                          QPen(Qt.black, 2), QBrush(self.enterprise_a_color))
        text_a = self.scene.addText("企业A设备")
        text_a.setFont(QFont("Arial", 12))  # 增大字体
        text_a.setDefaultTextColor(QColor(60, 60, 60))
        text_a.setPos(legend_x + 70, legend_y + 70)
        
        # 企业B设备图例
        self.scene.addRect(legend_x + 20, legend_y + 110, 40, 25,  # 增大示例图形
                          QPen(Qt.black, 2), QBrush(self.enterprise_b_color))
        text_b = self.scene.addText("企业B设备")
        text_b.setFont(QFont("Arial", 12))  # 增大字体
        text_b.setDefaultTextColor(QColor(60, 60, 60))
        text_b.setPos(legend_x + 70, legend_y + 110)
        
        # 其他设备图例
        self.scene.addRect(legend_x + 20, legend_y + 150, 40, 25,  # 增大示例图形
                          QPen(Qt.black, 2), QBrush(self.other_device_color))
        text_other = self.scene.addText("其他设备")
        text_other.setFont(QFont("Arial", 12))  # 增大字体
        text_other.setDefaultTextColor(QColor(60, 60, 60))
        text_other.setPos(legend_x + 70, legend_y + 150)
        
        # 添加分隔线
        self.scene.addLine(legend_x + 20, legend_y + 190, legend_x + legend_width - 20, legend_y + 190,
                          QPen(QColor(200, 200, 200), 2))  # 增大线宽
        
        # 路由器图例
        # 路由器使用圆角矩形
        router_width, router_height = 60, 35  # 增大示例图形
        self.scene.addRect(legend_x + 20, legend_y + 210, router_width, router_height, 
                          QPen(Qt.black, 2), QBrush(Qt.white))
        # 添加路由器图标特征 - 中间横线
        self.scene.addLine(
            legend_x + 20, legend_y + 210 + router_height/2, 
            legend_x + 20 + router_width, legend_y + 210 + router_height/2, 
            QPen(Qt.black, 1.5)
        )
        text_router = self.scene.addText("路由器")
        text_router.setFont(QFont("Arial", 12))  # 增大字体
        text_router.setDefaultTextColor(QColor(60, 60, 60))
        text_router.setPos(legend_x + 90, legend_y + 210)
        
        # 交换机图例
        switch_size = 40  # 增大示例图形
        self.scene.addRect(legend_x + 30, legend_y + 260, switch_size, switch_size, 
                          QPen(Qt.black, 2.5), QBrush(Qt.white))
        text_switch = self.scene.addText("交换机")
        text_switch.setFont(QFont("Arial", 12))  # 增大字体
        text_switch.setDefaultTextColor(QColor(60, 60, 60))
        text_switch.setPos(legend_x + 90, legend_y + 265)
        
        # 添加分隔线
        self.scene.addLine(legend_x + 20, legend_y + 310, legend_x + legend_width - 20, legend_y + 310,
                          QPen(QColor(200, 200, 200), 2))  # 增大线宽
        
        # 添加连接状态图例
        # 正常连接 - 企业A
        self.scene.addLine(legend_x + 20, legend_y + 330, legend_x + 70, legend_y + 330, 
                          QPen(self.enterprise_a_color, 3.5))  # 增大线宽
        text_normal_a = self.scene.addText("企业A连接正常")
        text_normal_a.setFont(QFont("Arial", 12))  # 增大字体
        text_normal_a.setDefaultTextColor(QColor(60, 60, 60))
        text_normal_a.setPos(legend_x + 80, legend_y + 320)
        
        # 正常连接 - 企业B
        self.scene.addLine(legend_x + 20, legend_y + 355, legend_x + 70, legend_y + 355, 
                          QPen(self.enterprise_b_color, 3.5))  # 增大线宽
        text_normal_b = self.scene.addText("企业B连接正常")
        text_normal_b.setFont(QFont("Arial", 12))  # 增大字体
        text_normal_b.setDefaultTextColor(QColor(60, 60, 60))
        text_normal_b.setPos(legend_x + 80, legend_y + 345)
        
        # 异常连接 - 使用红色虚线
        error_pen = QPen(self.error_color, 3.5)  # 增大线宽
        error_pen.setStyle(Qt.DashLine)  # 设置为虚线
        self.scene.addLine(legend_x + 20, legend_y + 380, legend_x + 70, legend_y + 380, error_pen)
        text_error = self.scene.addText("连接异常")
        text_error.setFont(QFont("Arial", 12))  # 增大字体
        text_error.setDefaultTextColor(QColor(60, 60, 60))
        text_error.setPos(legend_x + 80, legend_y + 370)
        
        # 添加操作说明
        help_text = self.scene.addText("操作说明: 鼠标拖动可平移视图，滚轮可缩放")
        help_text.setFont(QFont("Arial", 11))  # 增大字体
        help_text.setDefaultTextColor(QColor(80, 80, 80))
        help_text.setPos(legend_x + 20, legend_y + 410)
    
    @pyqtSlot(dict)
    def update_connection_status(self, status):
        """根据连通性检测结果更新连接线颜色"""
        try:
            # 添加调试输出，帮助排查问题
            print(f"收到连通性状态更新: {status}")
            
            for key, connections in self.connections.items():
                # 打印当前处理的连接键
                print(f"处理连接键: {key}")
                
                for connection in connections:
                    line = connection['line']
                    enterprise = connection['enterprise']
                    
                    # 获取连接状态
                    connection_status = status.get(key, 0)
                    print(f"连接 {key} 的状态: {connection_status} (企业: {enterprise})")
                    
                    # 根据连接状态和企业设置颜色，使用更粗的线条提高可视性
                    if connection_status == 1:  # 连接正常
                        if enterprise == "企业A":
                            line.setPen(QPen(self.enterprise_a_color, 3.5))  # 增大线宽
                        elif enterprise == "企业B":
                            line.setPen(QPen(self.enterprise_b_color, 3.5))  # 增大线宽
                    else:  # 连接异常
                        line.setPen(QPen(self.error_color, 3.5, Qt.DashDotLine))  # 增大线宽
            
            # 更新视图
            self.viewport().update()
            
        except Exception as e:
            print(f"更新连接状态时出错: {str(e)}")
            import traceback
            traceback.print_exc()

    def update_topology(self):
        """更新拓扑图"""
        # 获取线程工厂实例
        thread_factory = ThreadFactory.get_instance()
        
        # 使用线程工厂创建线程
        thread_factory.start_thread(
            target=self._update_topology_thread,
            name="UpdateTopology",
            module="整体网络编排模块"
        )