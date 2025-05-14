class SharedDataStore:
    """共享数据存储，用于PyQt和Flask应用间共享数据"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self._data = {}
        self._monitors = {}
        self._devices = {}
        self._tasks = {}
    
    def set_data(self, key, value):
        self._data[key] = value
        
    def get_data(self, key, default=None):
        return self._data.get(key, default)
    
    # 设备相关方法
    def register_device(self, device_id, device_info):
        self._devices[device_id] = device_info
    
    def get_device(self, device_id):
        return self._devices.get(device_id)
    
    def get_all_devices(self):
        return self._devices
    
    # 监控数据相关方法
    def update_monitor_data(self, device_id, data):
        self._monitors[device_id] = data
    
    def get_monitor_data(self, device_id=None):
        if device_id:
            return self._monitors.get(device_id)
        return self._monitors
    
    # 任务相关方法
    def add_task(self, task_id, task_info):
        self._tasks[task_id] = task_info
    
    def update_task_status(self, task_id, status):
        if task_id in self._tasks:
            self._tasks[task_id]['status'] = status
    
    def get_task(self, task_id):
        return self._tasks.get(task_id)
    
    def get_all_tasks(self):
        return self._tasks
