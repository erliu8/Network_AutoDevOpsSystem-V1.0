# module_loader.py
import importlib
import os
import logging
import sys  # 新增sys模块导入
from pathlib import Path
from typing import List, Dict, Optional
from PyQt5.QtWidgets import QWidget

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ModuleLoader")

class ModuleInterface:
    """模块接口基类 (所有模块必须继承此类)"""
    def __init__(self):
        self.name = "Unnamed Module"
        self.description = "No description"
        self.icon_path = ""
        self.version = "1.0.0"

    def get_widget(self) -> QWidget:
        """返回模块的主界面组件"""
        raise NotImplementedError("必须实现 get_widget 方法")

    def get_menu_entry(self) -> Optional[dict]:
        """返回菜单项配置 (可选)"""
        return None

class ModuleLoader:
    def __init__(self, module_dir: str = "modules"):
        """
        模块加载器
        
        :param module_dir: 模块目录路径 (相对于主程序)
        """
        self.module_dir = Path(module_dir)
        self.loaded_modules: List[ModuleInterface] = []
        self._module_metadata: Dict[str, dict] = {}

    def discover_modules(self) -> List[str]:
        """发现可用模块"""
        if not self.module_dir.exists():
            logger.error(f"模块目录不存在: {self.module_dir}")
            return []

        valid_modules = []
        for item in self.module_dir.iterdir():
            if self._is_valid_module(item):
                valid_modules.append(item.name)
        return valid_modules

    def load_all_modules(self) -> None:
        """加载所有有效模块"""
        modules = self.discover_modules()
        for module_name in modules:
            self.load_module(module_name)

    def load_module(self, module_name: str) -> Optional[ModuleInterface]:
        try:
            import sys
            # 添加项目根目录到系统路径
            project_root = Path(__file__).parent.parent.resolve()
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            # 修正后的模块导入逻辑
            module = importlib.import_module(f"modules.{module_name}")
            
            # Revised validation logic with clearer error messages
            if not hasattr(module, 'Module'):
                logger.error(f"模块 {module_name} 必须包含名为 'Module' 的主类")
                return None
                
            module_class = getattr(module, 'Module')
            
            # Verify inheritance and interface implementation
            if not issubclass(module_class, ModuleInterface):
                logger.error(f"模块类必须继承 ModuleInterface (模块: {module_name})")
                return None
            
            # 实例化模块
            module_instance = module.Module()
            
            # 验证接口实现
            if not isinstance(module_instance, ModuleInterface):
                logger.error(f"模块 {module_name} 未继承 ModuleInterface")
                return None
                
            # 收集元数据
            # 在load_module方法中确认元数据收集
            self._module_metadata[module_name] = {
                "name": module_instance.name,  # 必须从实例获取
                "description": module_instance.description,
                "version": module_instance.version,
                "icon": module_instance.icon_path
            }
            
            self.loaded_modules.append(module_instance)
            logger.info(f"成功加载模块: {module_name} ({module_instance.name})")
            return module_instance

        except Exception as e:
            logger.error(f"加载模块 {module_name} 失败: {str(e)}", exc_info=True)
            return None

    def get_module_widgets(self) -> Dict[str, QWidget]:
        """获取所有模块的界面组件"""
        return {
            module.name: module.get_widget()
            for module in self.loaded_modules
        }

    def get_module_metadata(self) -> Dict[str, dict]:
        """获取模块元数据"""
        return self._module_metadata.copy()

    def _is_valid_module(self, path: Path) -> bool:
        """验证是否为有效模块目录"""
        return all([
            path.is_dir(),
            (path / "__init__.py").exists(),
            not path.name.startswith("_")  # 忽略以_开头的目录
        ])

MODULES = [
    'vpn_deploy',  # 已存在
    'network_monitor',
    'internet_traffic_monitor'
]

