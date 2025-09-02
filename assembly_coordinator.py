"""
组装协调器模块
负责协调各个管理器的执行流程和状态管理
"""

from lookdev_manager import LookdevManager
from animation_manager import AnimationManager
from abc_importer import ABCImporter
from scene_manager import SceneManager
from material_manager import MaterialManager
from xgen_manager import XGenManager


class AssemblyCoordinator:
    """组装协调器"""

    def __init__(self):
        # 初始化所有管理器
        self.lookdev_manager = LookdevManager()
        self.animation_manager = AnimationManager()
        self.abc_importer = ABCImporter()
        self.scene_manager = SceneManager()
        self.material_manager = MaterialManager()
        self.xgen_manager = XGenManager()

        # 状态跟踪
        self.assembly_status = {
            'lookdev_imported': False,
            'animation_connected': False,
            'camera_imported': False,
            'hair_configured': False,
            'materials_fixed': False,
            'scene_configured': False
        }

        # 执行配置
        self.current_asset = None
        self.current_lookdev_file = None
        self.current_animation_files = []
        self.current_camera_file = None

    def step1_import_lookdev(self, lookdev_file, namespace):
        """
        步骤1: 导入Lookdev文件
        
        Args:
            lookdev_file (str): Lookdev文件路径
            namespace (str): 命名空间
            
        Returns:
            bool: 是否成功
        """
        print("\n=== 步骤1: 导入Lookdev文件 ===")

        success = self.lookdev_manager.import_lookdev_file(lookdev_file, namespace)

        if success:
            self.assembly_status['lookdev_imported'] = True
            self.current_lookdev_file = lookdev_file

            # 验证导入结果
            validation = self.lookdev_manager.validate_lookdev()
            if validation['warnings']:
                print("⚠️  警告:")
                for warning in validation['warnings']:
                    print(f"  - {warning}")

        return success

    def step2_import_and_connect_animations(self, animation_files, lookdev_namespace, animation_namespace, sequence, shot):
        """
        步骤2: 导入动画文件并连接
        
        Args:
            animation_files (list): 动画文件列表
            lookdev_namespace (str): Lookdev命名空间
            animation_namespace (str): 动画命名空间
            sequence
            shot

        Returns:
            bool: 是否成功
        """
        print("\n=== 步骤2: 导入动画文件并连接 ===")

        if not self.assembly_status['lookdev_imported']:
            print("❌ 请先导入Lookdev文件")
            return False

        # 分离毛发、布料和其他动画文件
        self.animation_manager.find_fur_and_cloth_files(animation_files, sequence, shot, lookdev_namespace)

        # 获取非毛发布料的动画文件
        regular_animation_files = []
        for file_path in animation_files:
            if (file_path not in self.animation_manager.fur_files and
                    file_path not in self.animation_manager.cloth_files):
                regular_animation_files.append(file_path)

        success_count = 0

        # 导入常规动画文件
        if regular_animation_files:
            print(f"处理 {len(regular_animation_files)} 个常规动画文件...")
            if self.abc_importer.import_and_connect_animations(
                    regular_animation_files, lookdev_namespace, animation_namespace):
                success_count += 1

        # 导入毛发缓存
        if self.animation_manager.fur_files:
            if self.animation_manager.import_and_connect_fur_cache():
                success_count += 1

        # 导入布料缓存
        if self.animation_manager.cloth_files:
            if self.animation_manager.import_and_connect_cloth_cache():
                success_count += 1

        # 处理特殊组BlendShape
        if self.animation_manager.handle_special_groups_blendshape(lookdev_namespace):
            print("✅ 特殊组BlendShape处理完成")

        if success_count > 0:
            self.assembly_status['animation_connected'] = True
            print("✅ 动画文件导入并连接成功")
            return True
        else:
            print("❌ 动画文件导入失败")
            return False

    def step3_import_camera(self, camera_file):
        """
        步骤3: 导入相机
        
        Args:
            camera_file (str): 相机文件路径
            
        Returns:
            tuple: (success, start_frame, end_frame)
        """
        print("\n=== 步骤3: 导入相机 ===")

        success, start_frame, end_frame, abc_node = self.abc_importer.import_camera_abc(camera_file)

        if success:
            self.assembly_status['camera_imported'] = True
            self.current_camera_file = camera_file
            return True, start_frame, end_frame
        else:
            return False, None, None

    def step4_setup_hair_cache(self, hair_cache_template, sequence, shot):
        """
        步骤4: 设置毛发缓存
        
        Args:
            hair_cache_template (str): 毛发缓存模板
            sequence (str): 场景
            shot (str): 镜头
        Returns:
            bool: 是否成功
        """
        print("\n=== 步骤4: 设置毛发缓存 ===")

        a = hair_cache_template.format(sequence=sequence, shot=shot)
        print(a)
        results = self.xgen_manager.setup_hair_cache(a)
        print(results)
        success = results['updated_descriptions'] > 0 or results['total_palettes'] == 0
        if success:
            self.assembly_status['hair_configured'] = True

        return success

    def step5_fix_materials(self):
        """
        步骤5: 修复材质
        
        Returns:
            bool: 是否成功
        """
        print("\n=== 步骤5: 修复材质 ===")

        results = self.material_manager.check_and_fix_materials()

        self.assembly_status['materials_fixed'] = True
        print(f"✅ 材质修复完成: {results['fixed_textures']} 个纹理已修复")

        return True

    def step6_setup_scene(self, start_frame, end_frame, lookdev_namespace):
        """
        步骤6: 设置场景参数
        
        Args:
            start_frame (int): 开始帧
            end_frame (int): 结束帧
            lookdev_namespace (str): Lookdev命名空间
            
        Returns:
            bool: 是否成功
        """
        print("\n=== 步骤6: 设置场景参数 ===")

        # 优化场景
        self.scene_manager.optimize_scene(lookdev_namespace)
        self.assembly_status['scene_configured'] = True
        return True

    def execute_all_steps(self, config):
        """
        执行所有步骤
        
        Args:
            config (dict): 配置参数
            
        Returns:
            bool: 是否全部成功
        """
        print("\n" + "=" * 50)
        print("开始执行所有步骤")
        print("=" * 50)

        steps = [
            (self.step1_import_lookdev, [config['lookdev_file'], config['lookdev_namespace']]),
            (self.step2_import_and_connect_animations, [
                config['animation_files'],
                config['lookdev_namespace'],
                config['animation_namespace'],
                config['sequence'],
                config['shot']
            ]),
            (self.step3_import_camera, [config['camera_file']]),
            (self.step4_setup_hair_cache, [
                config.get('hair_cache_template'),
                config['sequence'],
                config['shot']
            ]),
            (self.step5_fix_materials, []),
            (self.step6_setup_scene, [
                config['start_frame'],
                config['end_frame'],
                config['lookdev_namespace']
            ])
        ]

        success_count = 0

        for i, (step_func, args) in enumerate(steps, 1):
            try:
                print(f"\n执行步骤 {i}...")

                if step_func == self.step3_import_camera:
                    # 相机步骤返回不同的格式
                    success, start_frame, end_frame = step_func(*args)
                    if success and start_frame is not None:
                        config['start_frame'] = start_frame
                        config['end_frame'] = end_frame
                else:
                    success = step_func(*args)

                if success:
                    success_count += 1
                    print(f"✅ 步骤 {i} 完成")
                else:
                    print(f"❌ 步骤 {i} 失败")

            except Exception as e:
                print(f"❌ 步骤 {i} 执行出错: {str(e)}")

        overall_success = success_count == len(steps)

        if overall_success:
            print("\n🎉 所有步骤执行完成！")
        else:
            print(f"\n⚠️  执行完成，成功率: {success_count}/{len(steps)}")

        return overall_success

    def get_assembly_status(self):
        """获取组装状态"""
        return self.assembly_status.copy()

    def get_assembly_summary(self):
        """获取组装摘要"""
        summary = {
            'status': self.assembly_status.copy(),
            'lookdev_info': self.lookdev_manager.get_lookdev_statistics(),
            'animation_info': self.animation_manager.get_animation_statistics(),
            'scene_info': self.scene_manager.get_scene_info(),
            'material_info': self.material_manager.get_material_statistics(),
            'xgen_info': self.xgen_manager.get_xgen_statistics()
        }
        return summary

    def print_assembly_summary(self):
        """打印组装摘要"""
        print("\n" + "=" * 50)
        print("组装摘要")
        print("=" * 50)

        # 打印状态
        print("执行状态:")
        for step, status in self.assembly_status.items():
            status_icon = "✅" if status else "❌"
            print(f"  {step}: {status_icon}")

        # 打印各模块信息
        print("\n模块统计:")

        # Lookdev信息
        lookdev_stats = self.lookdev_manager.get_lookdev_statistics()
        print(f"  Lookdev: {lookdev_stats['mesh_count']} 个几何体, {lookdev_stats['material_count']} 个材质")

        # 动画信息
        animation_stats = self.animation_manager.get_animation_statistics()
        print(
            f"  动画: {animation_stats['total_animation_files']} 个文件, {animation_stats['blendshape_count']} 个BlendShape")

        # 场景信息
        scene_stats = self.scene_manager.get_scene_info()
        if scene_stats:
            print(
                f"  场景: {scene_stats.get('mesh_count', 0)} 个几何体, {scene_stats.get('abc_nodes_count', 0)} 个ABC节点")

        # 材质信息
        material_stats = self.material_manager.get_material_statistics()
        print(f"  材质: {material_stats['total_materials']} 个材质, {material_stats['missing_textures']} 个缺失纹理")

        # XGen信息
        xgen_stats = self.xgen_manager.get_xgen_statistics()
        print(f"  XGen: {xgen_stats['palette_count']} 个调色板, {xgen_stats['description_count']} 个描述")

    def reset_assembly_status(self):
        """重置组装状态"""
        self.assembly_status = {
            'lookdev_imported': False,
            'animation_connected': False,
            'camera_imported': False,
            'hair_configured': False,
            'materials_fixed': False,
            'scene_configured': False
        }

        # 清理各管理器
        self.lookdev_manager.cleanup_lookdev()
        self.animation_manager.cleanup_animation()
        self.abc_importer.clear_imported_nodes()

        print("✅ 组装状态已重置")

    def cleanup_all(self):
        """清理所有内容"""
        print("清理所有组装内容...")

        try:
            # 重置场景
            self.scene_manager.reset_scene()

            # 重置状态
            self.reset_assembly_status()

            print("✅ 清理完成")

        except Exception as e:
            print(f"❌ 清理失败: {str(e)}")

    def validate_assembly(self):
        """验证组装完整性"""
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # 验证Lookdev
        if self.assembly_status['lookdev_imported']:
            lookdev_validation = self.lookdev_manager.validate_lookdev()
            if not lookdev_validation['valid']:
                validation['errors'].extend(lookdev_validation['errors'])
            validation['warnings'].extend(lookdev_validation['warnings'])
        else:
            validation['errors'].append("Lookdev未导入")

        # 验证其他状态
        critical_steps = ['animation_connected', 'camera_imported']
        for step in critical_steps:
            if not self.assembly_status[step]:
                validation['warnings'].append(f"步骤未完成: {step}")

        validation['valid'] = len(validation['errors']) == 0

        return validation
