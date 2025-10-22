"""
精简的核心组装器模块
只保留核心调度逻辑，所有具体功能都委托给专门的管理器
"""

import os
import sys

# 简化的直接导入
from config.config_manager import ConfigManager
from utils.file_manager import FileManager
from utils.path_utils import PathUtils
from core.assembly_coordinator import AssemblyCoordinator


class CoreAssembler:
    """精简的核心组装器类"""
    
    def __init__(self, config_file=None):
        """
        初始化核心组装器
        
        Args:
            config_file (str): JSON配置文件路径（可选）
        """
        # 初始化基础组件
        self.config_manager = ConfigManager(config_file)
        self.file_manager = FileManager()
        self.path_utils = PathUtils()
        
        # 初始化组装协调器（包含所有专业管理器）
        self.coordinator = AssemblyCoordinator()
        
        # 当前工作配置
        self.current_asset = None
        self.current_lookdev_file = None
        self.current_animation_files = []
        self.current_camera_file = None
        self.manual_camera_file = None
        self.sequence = None
        self.shot = None
        
        # 命名空间配置
        self.lookdev_namespace = "asset_lookdev"
        self.animation_namespace = "asset_animation"
        self.fur_namespace = "asset_fur"
        self.cloth_namespace = "asset_cloth"
        
        # 时间范围设置
        self.start_frame = 1001
        self.end_frame = 1100
    
    def load_config(self, config_file):
        """
        加载新的配置文件
        
        Args:
            config_file (str): JSON配置文件路径
            
        Returns:
            bool: 是否加载成功
        """
        success = self.config_manager.load_config(config_file)
        
        if success:
            # 重置组装状态
            self.coordinator.reset_assembly_status()
            print("配置加载完成，已重置组装状态")
        
        return success
    
    def set_current_asset(self, asset_name):
        """
        设置当前工作的资产
        
        Args:
            asset_name (str): 资产名称
            
        Returns:
            bool: 是否设置成功
        """
        asset_config = self.config_manager.get_asset_config(asset_name)
        
        if not asset_config:
            print(f"未找到资产配置: {asset_name}")
            return False
        
        self.current_asset = asset_config
        
        # 更新命名空间
        self._update_namespaces(asset_name)
        
        # 查找相关文件
        self._find_asset_files()
        
        print(f"当前资产设置为: {asset_name}")
        self._print_asset_summary()
        
        return True
    
    def _update_namespaces(self, asset_name):
        """更新所有命名空间"""
        self.lookdev_namespace = f"{asset_name}_lookdev"
        self.animation_namespace = f"{asset_name}_animation"
        self.fur_namespace = f"{asset_name}_fur"
        self.cloth_namespace = f"{asset_name}_cloth"
        
        # 同步到协调器的管理器
        self.coordinator.lookdev_manager.set_namespace(self.lookdev_namespace)
        self.coordinator.animation_manager.set_namespaces(self.fur_namespace, self.cloth_namespace)
    
    def _find_asset_files(self):
        """查找资产相关的所有文件"""
        if not self.current_asset:
            return
        
        # 查找lookdev文件
        self._find_lookdev_file()
        
        # 设置动画文件
        self._set_animation_files()
        
        # 查找相机文件
        self._find_camera_file()

        # 获取当前场景和镜头信息
        self._current_scene_and_shot()

    def _find_lookdev_file(self):
        """查找当前资产的lookdev文件"""
        if not self.current_asset:
            return
        
        asset_name = self.current_asset['asset_name']
        asset_type = self.current_asset['asset_type']
        
        # 生成lookdev目录路径
        lookdev_dir = self.config_manager.generate_lookdev_path(asset_name, asset_type)
        
        # 查找最新的lookdev文件
        latest_file = self.file_manager.get_latest_lookdev_file(lookdev_dir)
        self.current_lookdev_file = latest_file
        
        if latest_file:
            print(f"找到lookdev文件: {os.path.basename(latest_file)}")
        else:
            print(f"未找到lookdev文件")
    
    def _set_animation_files(self):
        """设置动画文件列表"""
        if not self.current_asset:
            return
        
        outputs = self.current_asset.get('outputs', [])
        self.current_animation_files = [path for path in outputs if path.endswith(('.abc', '.ma'))]
        
        print(f"找到 {len(self.current_animation_files)} 个动画文件")
    
    def _find_camera_file(self):
        """查找相机文件"""
        # 如果有手动指定的相机文件，优先使用
        if self.manual_camera_file and os.path.exists(self.manual_camera_file):
            self.current_camera_file = self.manual_camera_file
            print(f"使用手动指定的相机文件: {os.path.basename(self.current_camera_file)}")
            return
        
        if not self.current_animation_files:
            self.current_camera_file = None
            return
        
        # 使用第一个动画文件推导相机路径
        first_animation = self.current_animation_files[0]
        camera_path = self.path_utils.get_best_camera_file(first_animation)
        self.current_camera_file = camera_path
        
        if camera_path:
            print(f"找到相机文件: {os.path.basename(camera_path)}")
        else:
            print("未找到相机文件")

    def _current_scene_and_shot(self):
        """获取当前场景和镜头信息"""

        if self.current_camera_file:
            result = self.path_utils.extract_shot_info_from_animation_path(self.current_animation_files[0])
            print(result)
            if result:
                self.sequence, self.shot = result.get('sequence'), result.get('shot')

    def _print_asset_summary(self):
        """打印资产摘要"""
        if not self.current_asset:
            return
        
        print("\n当前资产信息:")
        print(f"  名称: {self.current_asset['asset_name']}")
        print(f"  类型: {self.current_asset['asset_type']}")
        print(f"  Lookdev文件: {'✅' if self.current_lookdev_file else '❌'}")
        print(f"  动画文件: {len(self.current_animation_files)} 个")
        print(f"  相机文件: {'✅' if self.current_camera_file else '❌'}")
        print(f"  命名空间: {self.lookdev_namespace}")
    
    def set_manual_camera_file(self, camera_file):
        """设置手动指定的相机文件"""
        if os.path.exists(camera_file):
            self.manual_camera_file = camera_file
            self.current_camera_file = camera_file
            return True
        return False
    
    # ===== 执行步骤方法 =====
    
    def step1_import_lookdev(self):
        """步骤1: 导入Lookdev文件"""
        if not self.current_lookdev_file:
            print("❌ 没有可用的Lookdev文件")
            return False
        
        return self.coordinator.step1_import_lookdev(self.current_lookdev_file, self.lookdev_namespace)
    
    def step2_import_and_connect_animation_abc(self):
        """步骤2: 导入动画ABC并连接"""
        if not self.current_animation_files:
            print("❌ 没有可用的动画文件")
            return False
        
        return self.coordinator.step2_import_and_connect_animations(
            self.current_animation_files,
            self.lookdev_namespace,
            self.animation_namespace,
            self.sequence,
            self.shot
        )
    
    def step3_import_camera_abc(self):
        """步骤3: 导入动画相机ABC"""
        if not self.current_camera_file:
            print("❌ 没有可用的相机文件")
            return False
        
        success, start_frame, end_frame = self.coordinator.step3_import_camera(self.current_camera_file)
        
        if success and start_frame is not None:
            self.start_frame = start_frame
            self.end_frame = end_frame
        
        return success
    
    def step4_setup_hair_cache(self):
        """步骤4: 设置毛发缓存路径"""
        hair_template = self.config_manager.base_paths.get('hair_cache_template')
        return self.coordinator.step4_setup_hair_cache(hair_template, self.sequence, self.shot, self.lookdev_namespace)
    
    def step5_fix_materials(self):
        """步骤5: 检查修复材质"""
        return self.coordinator.step5_fix_materials()
    
    def step6_setup_scene(self):
        """步骤6: 设置场景参数"""
        return self.coordinator.step6_setup_scene(self.start_frame, self.end_frame, self.lookdev_namespace)
    
    def execute_all_steps(self):
        """一键执行所有步骤"""
        if not self.current_asset:
            print("❌ 请先选择资产")
            return False

        if not self.sequence or not self.shot:
            print("❌ 无法确定当前场景和镜头信息")
            return False
        
        config = {
            'lookdev_file': self.current_lookdev_file,
            'animation_files': self.current_animation_files,
            'camera_file': self.current_camera_file,
            'lookdev_namespace': self.lookdev_namespace,
            'animation_namespace': self.animation_namespace,
            'start_frame': self.start_frame,
            'end_frame': self.end_frame,
            'hair_cache_template': self.config_manager.base_paths.get('hair_cache_template'),
            'sequence': self.sequence,
            'shot': self.shot
        }
        
        return self.coordinator.execute_all_steps(config)
    
    # ===== 状态和信息方法 =====
    
    def get_assembly_status(self):
        """获取组装状态"""
        return self.coordinator.get_assembly_status()
    
    def get_current_config_summary(self):
        """获取当前配置摘要"""
        status = self.coordinator.get_assembly_status()
        
        summary = {
            'asset': self.current_asset['asset_name'] if self.current_asset else None,
            'lookdev_file': os.path.basename(self.current_lookdev_file) if self.current_lookdev_file else None,
            'animation_files_count': len(self.current_animation_files),
            'camera_file': os.path.basename(self.current_camera_file) if self.current_camera_file else None,
            'namespace': self.lookdev_namespace,
            'time_range': f"{self.start_frame} - {self.end_frame}",
            'status': status
        }
        
        return summary
    
    def print_assembly_summary(self):
        """打印组装摘要"""
        self.coordinator.print_assembly_summary()
    
    def reset_assembly_status(self):
        """重置组装状态"""
        self.coordinator.reset_assembly_status()
    
    def validate_assembly(self):
        """验证组装完整性"""
        return self.coordinator.validate_assembly()
    
    def cleanup_all(self):
        """清理所有内容"""
        self.coordinator.cleanup_all()
        
        # 重置当前配置
        self.current_asset = None
        self.current_lookdev_file = None
        self.current_animation_files = []
        self.current_camera_file = None
        self.manual_camera_file = None