# Integral_Network_Arrangement.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QLabel
from PyQt5.QtCore import Qt, QRectF, pyqtSlot
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont

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
        
        # 创建场景
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(QRectF(0, 0, 1800, 1000))
        self.setScene(self.scene)
        
        # 设置视图属性
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        # 定义颜色
        self.enterprise_a_color = QColor(135, 206, 250)  # 浅蓝色
        self.enterprise_b_color = QColor(255, 182, 193)  # 粉色
        self.error_color = QColor(255, 0, 0)  # 红色
        self.other_device_color = QColor(147, 112, 219)  # 紫色
        
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
        
        # 添加区域背景
        self.add_region(50, 50, 500, 650, QColor(230, 230, 255), "地域1")
        self.add_region(750, 50, 500, 650, QColor(255, 230, 230), "地域2")
        self.add_region(350, 20, 500, 180, QColor(230, 255, 230), "运营商")
        
        # 添加设备节点 - 地域1
        self.add_device(200, 150, "地域1出口路由器", "router", self.other_device_color)
        self.add_device(200, 250, "地域1核心交换机", "switch", self.other_device_color)
        self.add_device(100, 400, "地域1汇聚交换机A", "switch", self.enterprise_a_color)
        self.add_device(300, 400, "地域1汇聚交换机B", "switch", self.enterprise_b_color)
        self.add_device(50, 550, "接入交换机A1", "switch", self.enterprise_a_color)
        self.add_device(150, 550, "接入交换机A2", "switch", self.enterprise_a_color)
        self.add_device(250, 550, "接入交换机B1", "switch", self.enterprise_b_color)
        self.add_device(350, 550, "接入交换机B2", "switch", self.enterprise_b_color)
        
        # 添加设备节点 - 地域2
        self.add_device(900, 150, "地域2出口路由器", "router", self.other_device_color)
        self.add_device(800, 250, "地域2核心交换机A", "switch", self.enterprise_a_color)
        self.add_device(1000, 250, "地域2核心交换机B", "switch", self.enterprise_b_color)
        self.add_device(750, 400, "接入交换机A3", "switch", self.enterprise_a_color)
        self.add_device(850, 400, "接入交换机A4", "switch", self.enterprise_a_color)
        self.add_device(950, 400, "接入交换机B3", "switch", self.enterprise_b_color)
        self.add_device(1050, 400, "接入交换机B4", "switch", self.enterprise_b_color)
        
        # 添加运营商设备
        self.add_device(400, 100, "PE1", "router", self.other_device_color)
        self.add_device(500, 100, "PE", "router", self.other_device_color)
        self.add_device(600, 100, "PE2", "router", self.other_device_color)
        
        # 添加连接线 - 地域1
        # 核心交换机 -> 出口路由器 (企业A)
        self.add_connection(200, 200, 200, 150, "area1_core_router_a", "企业A")
        # 核心交换机 -> 汇聚交换机A (企业A)
        self.add_connection(200, 300, 100, 350, "area1_converge_core_a", "企业A")
        # 核心交换机 -> 汇聚交换机B (企业B)
        self.add_connection(200, 300, 300, 350, "area1_converge_core_b", "企业B")
        # 汇聚交换机A -> 接入交换机A1 (企业A)
        self.add_connection(100, 450, 50, 500, "area1_access_a1_converge_a", "企业A")
        # 汇聚交换机A -> 接入交换机A2 (企业A)
        self.add_connection(100, 450, 150, 500, "area1_access_a2_converge_a", "企业A")
        # 汇聚交换机B -> 接入交换机B1 (企业B)
        self.add_connection(300, 450, 250, 500, "area1_access_a1_converge_b", "企业B")
        # 汇聚交换机B -> 接入交换机B2 (企业B)
        self.add_connection(300, 450, 350, 500, "area1_access_a2_converge_b", "企业B")
        
        # 添加连接线 - 地域2
        # 出口路由器 -> 核心交换机A (企业A)
        self.add_connection(900, 150, 800, 200, "area2_core_router_a", "企业A")
        # 出口路由器 -> 核心交换机B (企业B)
        self.add_connection(900, 150, 1000, 200, "area2_core_router_b", "企业B")
        # 核心交换机A -> 接入交换机A3 (企业A)
        self.add_connection(800, 300, 750, 350, "area2_core_a", "企业A")
        # 核心交换机A -> 接入交换机A4 (企业A)
        self.add_connection(800, 300, 850, 350, "area2_core_a", "企业A")
        # 核心交换机B -> 接入交换机B3 (企业B)
        self.add_connection(1000, 300, 950, 350, "area2_core_b", "企业B")
        # 核心交换机B -> 接入交换机B4 (企业B)
        self.add_connection(1000, 300, 1050, 350, "area2_core_b", "企业B")
        
        # 添加运营商连接
        # 地域1出口 -> PE1 (企业A)
        self.add_connection(200, 100, 400, 100, "area1_router_area2_router_a", "企业A")
        # PE1 -> PE
        self.add_connection(400, 100, 500, 100, None, None)
        # PE -> PE2
        self.add_connection(500, 100, 600, 100, None, None)
        # PE2 -> 地域2出口 (企业A)
        self.add_connection(600, 100, 900, 100, "area1_router_area2_router_a", "企业A")
        
        # 添加企业B的运营商连接
        # 地域1出口 -> PE1 (企业B)
        self.add_connection(200, 120, 400, 120, "area1_router_area2_router_b", "企业B")
        # PE1 -> PE (企业B)
        self.add_connection(400, 120, 500, 120, None, None)
        # PE -> PE2 (企业B)
        self.add_connection(500, 120, 600, 120, None, None)
        # PE2 -> 地域2出口 (企业B)
        self.add_connection(600, 120, 900, 120, "area1_router_area2_router_b", "企业B")
        
        # 添加图例
        self.add_legend()
    
    def add_device(self, x, y, name, device_type, color):
        """添加设备节点"""
        # 添加设备图形
        if device_type == "router":
            # 路由器使用椭圆形
            ellipse = self.scene.addEllipse(x-45, y-30, 90, 60, 
                                         QPen(Qt.black, 2), 
                                         QBrush(color))
            # 存储设备节点
            self.devices[name] = {'shape': ellipse, 'type': device_type}
        else:
            # 交换机使用矩形
            rect = self.scene.addRect(x-40, y-25, 80, 50, 
                                     QPen(Qt.black, 2), 
                                     QBrush(color))
            # 存储设备节点
            self.devices[name] = {'shape': rect, 'type': device_type}
        
        # 添加设备名称
        text = self.scene.addText(name)
        text.setFont(QFont("Arial", 9, QFont.Bold))
        text.setPos(x - text.boundingRect().width()/2, y + 30)
    
    def add_connection(self, x1, y1, x2, y2, connection_key=None, enterprise=None):
        """添加设备间连接线，并存储连接线对象以便后续更新颜色"""
        # 默认使用黑色线
        pen = QPen(Qt.black, 2)
        
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
        # 添加半透明背景
        rect = self.scene.addRect(x, y, width, height, 
                                 QPen(Qt.gray, 1, Qt.DashLine), 
                                 QBrush(color.lighter(150)))
        rect.setZValue(-1)  # 确保背景在最底层
        
        # 添加区域名称
        text = self.scene.addText(name)
        text.setFont(QFont("Arial", 12, QFont.Bold))
        text.setPos(x + 10, y + 10)
    
    def add_legend(self):
        """添加图例"""
        legend_x = 1200
        legend_y = 100
        legend_width = 250
        legend_height = 300  # 增加高度以容纳更多图例项
        
        # 添加图例背景
        self.scene.addRect(legend_x, legend_y, legend_width, legend_height,
                          QPen(Qt.black), QBrush(QColor(255, 255, 255, 200)))
        
        # 添加图例标题
        title = self.scene.addText("图例")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setPos(legend_x + 80, legend_y + 10)
        
        # 企业A设备图例
        self.scene.addRect(legend_x + 20, legend_y + 50, 30, 20, 
                          QPen(Qt.black), QBrush(self.enterprise_a_color))
        text_a = self.scene.addText("企业A设备")
        text_a.setPos(legend_x + 60, legend_y + 50)
        
        # 企业B设备图例
        self.scene.addRect(legend_x + 20, legend_y + 80, 30, 20, 
                          QPen(Qt.black), QBrush(self.enterprise_b_color))
        text_b = self.scene.addText("企业B设备")
        text_b.setPos(legend_x + 60, legend_y + 80)
        
        # 其他设备图例
        self.scene.addRect(legend_x + 20, legend_y + 110, 30, 20, 
                          QPen(Qt.black), QBrush(self.other_device_color))
        text_other = self.scene.addText("其他设备")
        text_other.setPos(legend_x + 60, legend_y + 110)
        
        # 路由器图例
        self.scene.addEllipse(legend_x + 20, legend_y + 140, 30, 20, 
                             QPen(Qt.black), QBrush(Qt.white))
        text_router = self.scene.addText("路由器")
        text_router.setPos(legend_x + 60, legend_y + 140)
        
        # 交换机图例
        self.scene.addRect(legend_x + 20, legend_y + 170, 30, 20, 
                          QPen(Qt.black), QBrush(Qt.white))
        text_switch = self.scene.addText("交换机")
        text_switch.setPos(legend_x + 60, legend_y + 170)
        
        # 添加连接状态图例
        # 正常连接 - 企业A
        self.scene.addLine(legend_x + 20, legend_y + 200, legend_x + 50, legend_y + 200, 
                          QPen(self.enterprise_a_color, 2))
        text_normal_a = self.scene.addText("企业A连接正常")
        text_normal_a.setPos(legend_x + 60, legend_y + 190)
        
        # 正常连接 - 企业B
        self.scene.addLine(legend_x + 20, legend_y + 220, legend_x + 50, legend_y + 220, 
                          QPen(self.enterprise_b_color, 2))
        text_normal_b = self.scene.addText("企业B连接正常")
        text_normal_b.setPos(legend_x + 60, legend_y + 210)
        
        # 异常连接
        self.scene.addLine(legend_x + 20, legend_y + 240, legend_x + 50, legend_y + 240, 
                          QPen(self.error_color, 2))
        text_error = self.scene.addText("连接异常")
        text_error.setPos(legend_x + 60, legend_y + 230)
        
        # 添加操作说明
        text_help = self.scene.addText("操作说明: 鼠标拖动可平移视图，滚轮可缩放")
        text_help.setPos(legend_x + 20, legend_y + 270)
    
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
                    
                    # 根据连接状态和企业设置颜色
                    if connection_status == 1:  # 连接正常
                        if enterprise == "企业A":
                            line.setPen(QPen(self.enterprise_a_color, 2))
                        elif enterprise == "企业B":
                            line.setPen(QPen(self.enterprise_b_color, 2))
                    else:  # 连接异常
                        line.setPen(QPen(self.error_color, 2))
            
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