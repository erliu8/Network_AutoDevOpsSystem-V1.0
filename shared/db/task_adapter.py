class DBTaskQueue:
    """
    数据库任务队列
    负责管理任务状态轮询和任务处理
    """
    def __init__(self, polling_interval=5, processing_interval=5):
        self.polling_interval = polling_interval  # 状态轮询间隔（秒）
        self.processing_interval = processing_interval  # 任务处理间隔（秒）
        self.polling_thread = None
        self.processing_thread = None
        self.polling_active = False
        self.processing_active = False
        self.polling_finished = threading.Event()
        self.processing_finished = threading.Event()
        self.task_repository = get_task_repository()
        self.callbacks = {}
        
    def register_callback(self, task_type, callback_func):
        """
        注册任务回调函数
        
        Args:
            task_type (str): 任务类型
            callback_func (callable): 回调函数，接受task_id和task_data参数
        """
        self.callbacks[task_type] = callback_func
        print(f"已注册任务类型 {task_type} 的回调函数: {callback_func.__name__}")
        
    def start_polling(self):
        """
        启动状态轮询线程
        
        Returns:
            bool: 是否成功启动
        """
        if self.polling_thread is not None and self.polling_thread.is_alive():
            print("状态轮询线程已经在运行")
            return False
            
        self.polling_active = True
        self.polling_finished.clear()
        self.polling_thread = threading.Thread(target=self._polling_thread, daemon=True)
        self.polling_thread.start()
        print(f"已启动状态轮询线程，间隔 {self.polling_interval} 秒")
        return True
        
    def start_processing(self):
        """
        启动任务处理线程
        
        Returns:
            bool: 是否成功启动
        """
        if self.processing_thread is not None and self.processing_thread.is_alive():
            print("任务处理线程已经在运行")
            return False
            
        self.processing_active = True
        self.processing_finished.clear()
        self.processing_thread = threading.Thread(target=self._processing_thread, daemon=True)
        self.processing_thread.start()
        print(f"已启动任务处理线程，间隔 {self.processing_interval} 秒")
        return True
        
    def stop_polling(self):
        """
        停止状态轮询线程
        
        Returns:
            bool: 是否成功停止
        """
        if self.polling_thread is None or not self.polling_thread.is_alive():
            print("状态轮询线程未在运行")
            return False
            
        self.polling_active = False
        self.polling_finished.wait(timeout=self.polling_interval + 5)
        print("已停止状态轮询线程")
        return True
        
    def stop_processing(self):
        """
        停止任务处理线程
        
        Returns:
            bool: 是否成功停止
        """
        if self.processing_thread is None or not self.processing_thread.is_alive():
            print("任务处理线程未在运行")
            return False
            
        self.processing_active = False
        self.processing_finished.wait(timeout=self.processing_interval + 5)
        print("已停止任务处理线程")
        return True
        
    def _polling_thread(self):
        """状态轮询线程"""
        print("状态轮询线程已启动")
        while self.polling_active:
            try:
                # 执行状态轮询
                self._poll_task_status()
            except Exception as e:
                print(f"状态轮询发生错误: {str(e)}")
                import traceback
                traceback.print_exc()
                
            # 等待下一次轮询
            time.sleep(self.polling_interval)
            
        self.polling_finished.set()
        print("状态轮询线程已停止")
        
    def _processing_thread(self):
        """任务处理线程"""
        print("任务处理线程已启动")
        print(f"已注册的任务类型回调: {list(self.callbacks.keys())}")
        
        while self.processing_active:
            try:
                # 处理待执行任务
                self._process_pending_tasks()
            except Exception as e:
                print(f"任务处理发生错误: {str(e)}")
                import traceback
                traceback.print_exc()
                
            # 等待下一次处理
            time.sleep(self.processing_interval)
            
        self.processing_finished.set()
        print("任务处理线程已停止")
        
    def _poll_task_status(self):
        """轮询任务状态"""
        # 获取需要轮询的任务状态
        status_to_poll = ["running", "pending"]
        
        # 获取这些状态的任务
        tasks = self.task_repository.get_tasks_by_status(status_to_poll)
        
        if tasks:
            print(f"发现 {len(tasks)} 个需要轮询状态的任务")
            
            # 遍历任务
            for task in tasks:
                task_id = task.get("id")
                task_type = task.get("type")
                task_status = task.get("status")
                task_data = task.get("data", {})
                
                print(f"检查任务状态: {task_id} ({task_type}) - {task_status}")
                
                # 根据任务类型和状态处理
                if task_status == "running":
                    # 检查任务是否已完成
                    # 这里可以添加实际的检查逻辑
                    print(f"任务 {task_id} 运行中，将在下一次轮询检查状态")
        else:
            # 没有需要轮询的任务
            pass
            
    def _process_pending_tasks(self):
        """处理待执行的已批准任务"""
        # 获取待执行的已批准任务
        tasks = self.task_repository.get_tasks_by_status(["approved"])
        processed_count = 0
        
        if tasks:
            print(f"发现 {len(tasks)} 个待执行的已批准任务")
            
            # 遍历任务
            for task in tasks:
                task_id = task.get("id")
                task_type = task.get("type")
                
                print(f"处理已批准任务: {task_id} ({task_type})")
                
                # 更新任务状态为正在执行
                self.task_repository.update_task_status(task_id, "running", by="TaskProcessor")
                
                try:
                    # 检查是否有回调函数处理该任务类型
                    if task_type in self.callbacks:
                        # 获取任务数据
                        task_data = task.get("data", {})
                        
                        # 获取回调函数
                        callback = self.callbacks[task_type]
                        
                        print(f"调用任务 {task_id} 的回调函数: {callback.__name__}")
                        
                        # 执行回调函数
                        result = callback(task_id, task_data)
                        
                        # 处理回调结果，更新任务状态
                        if isinstance(result, dict):
                            status = result.get("status", "unknown")
                            message = result.get("message", "无消息")
                            
                            print(f"任务 {task_id} 处理结果: {status} - {message}")
                            
                            if status == "success":
                                self.task_repository.update_task_status(task_id, "completed", result=result, by="TaskProcessor")
                            elif status == "error":
                                self.task_repository.update_task_status(task_id, "failed", result=result, by="TaskProcessor")
                            elif status == "warning":
                                self.task_repository.update_task_status(task_id, "warning", result=result, by="TaskProcessor")
                            else:
                                self.task_repository.update_task_status(task_id, "unknown", result=result, by="TaskProcessor")
                        else:
                            print(f"任务 {task_id} 的回调未返回有效结果: {result}")
                            self.task_repository.update_task_status(task_id, "failed", result={"error": "回调未返回有效结果"}, by="TaskProcessor")
                    else:
                        print(f"任务类型 {task_type} 没有注册回调函数")
                        self.task_repository.update_task_status(task_id, "failed", result={"error": f"未找到任务类型 {task_type} 的处理器"}, by="TaskProcessor")
                        
                    processed_count += 1
                except Exception as e:
                    print(f"处理任务 {task_id} 时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    self.task_repository.update_task_status(task_id, "failed", result={"error": str(e)}, by="TaskProcessor")
        
        return processed_count
            
    def add_task(self, task_type, task_data, status="pending"):
        """
        添加任务
        
        Args:
            task_type (str): 任务类型
            task_data (dict): 任务数据
            status (str, optional): 初始状态. 默认为 "pending".
            
        Returns:
            str: 任务ID
        """
        # 添加任务到数据库
        task_id = self.task_repository.add_task(task_type, task_data, status)
        print(f"添加任务: {task_id} ({task_type}) - {status}")
        return task_id 