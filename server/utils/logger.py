"""
日志系统模块
提供统一的日志管理功能
"""

import logging
import os
from datetime import datetime
from typing import Optional

class Logger:
    """统一日志管理类"""
    
    def __init__(self, name: str, level: str = "INFO", log_file: Optional[str] = None):
        """
        初始化日志器
        
        Args:
            name: 日志器名称
            level: 日志级别
            log_file: 日志文件路径
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers(log_file)
    
    def _setup_handlers(self, log_file: Optional[str]):
        """设置日志处理器"""
        # 控制台处理器
        console_handler = logging.StreamHandler()
        # 使用 logger 自身级别（已在 __init__ 设定）
        console_handler.setLevel(self.logger.level)
        
        # 文件处理器
        if log_file:
            # 确保日志目录存在
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # 文件处理器格式化器
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        
        # 控制台处理器格式化器
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger.addHandler(console_handler)
    
    def debug(self, message: str):
        """调试级别日志"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """信息级别日志"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """警告级别日志"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """错误级别日志"""
        self.logger.error(message)
    
    def critical(self, message: str):
        """严重错误级别日志"""
        self.logger.critical(message)

# 全局日志器实例
system_logger = Logger("BrainComputerSystem", level="DEBUG", log_file="logs/server.log")