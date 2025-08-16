"""
核心组装器 - 重构版本
协调各个模块完成Lookdev和动画组装
版本：3.0 (模块化重构)
"""

import maya.cmds as cmds
import os

# 导入新的模块化组件
from config_manager import ConfigManager
from file_manager import FileManager
from path_utils import PathUtils
from blendshape_manager import BlendshapeManager, ClothBlendshapeManager
from abc_importer import ABCImporter, FurCacheImporter
from material_manager import MaterialManager, XGenManager
from scene_manager import SceneManager, LookdevFinder, GroupFinder


class CoreAssembler:
    """
    核心组装器 - 重构版本
    负责协调各个专业模块完成整个组装流程
    """

    def __init__(self, config_file=None):
        """
        初始化核心组装器
        
        Args:
            config_file (str): 配置文件路径
        """
        # 初始化管理器模块
        self.config_manager = ConfigManager(config_file)
        self.file_manager = FileManager()
        self.path_utils = PathUtils()
        self.blendshape_manager = BlendshapeManager()
        self.cloth_blendshape_manager = ClothBlendshapeManager()
        self.abc_importer = ABCImporter()
        self.fur_cache_importer = FurCacheImporter()
        self.material_manager = MaterialManager()
        self.xgen_manager = XGenManager()
        self.scene_manager = SceneManager()
        self.lookdev_finder = LookdevFinder(self.file_manager)
        
        # 当前工作状态
        self.current_asset = None
        self.current_lookdev_file = None
        self.current_animation_files = []
        self.current_camera_file = None
        self.manual_camera_file = None
        
        # 命名空间设置
        self.lookdev_namespace = "asset_lookdev"
        self.animation_namespace = "animation"
        self.fur_namespace = "fur" 
        self.cloth_namespace = "cloth"
        self.actual_cloth_namespace = None
        
        # 时间范围
        self.start_frame = 1
        self.end_frame = 100
        
        # 缓存数据
        self.lookdev_meshes = {}
        self.pending_abc_files = []

    def load_config(self, config_file):
        """
        加载配置文件
        
        Args:
            config_file (str): 配置文件路径
            
        Returns:
            bool: 加载是否成功
        """
        return self.config_manager.load_config(config_file)

    def set_current_asset(self, asset_name):
        """
        设置当前工作的资产
        
        Args:
            asset_name (str): 资产名称
            
        Returns:
            bool: 设置是否成功
        """
        try:
            print(f"\n=== 设置当前资产: {asset_name} ===")
            
            # 获取资产配置
            asset_config = self.config_manager.get_asset_config(asset_name)
            
            if not asset_config:
                print(f"❌ 未找到资产配置: {asset_name}")
                return False
            
            self.current_asset = asset_config
            
            # 查找相关文件
            self._find_lookdev_file()
            self._set_animation_files()
            self._find_camera_file()
            
            # 更新命名空间
            self._update_namespaces()
            
            # 打印当前文件状态
            self._print_current_files()
            
            print(f"✅ 资产设置完成: {asset_name}")
            return True
            
        except Exception as e:
            print(f"❌ 设置资产失败: {str(e)}")
            return False

    def _find_lookdev_file(self):
        """查找Lookdev文件"""
        try:
            asset_name = self.current_asset['asset_name']
            asset_type = self.current_asset['asset_type']
            asset_type_group_name = self.current_asset.get('asset_type_group_name', asset_type)
            
            # 生成lookdev目录路径
            lookdev_dir = self.config_manager.generate_lookdev_path(
                asset_name, asset_type, asset_type_group_name
            )
            
            # 使用LookdevFinder查找文件
            self.current_lookdev_file = self.lookdev_finder.find_lookdev_file(
                asset_name, asset_type, lookdev_dir
            )
            
        except Exception as e:
            print(f"查找Lookdev文件失败: {str(e)}")
            self.current_lookdev_file = None

    def _set_animation_files(self):
        """设置动画文件"""
        try:
            outputs = self.current_asset.get('outputs', [])
            
            # 过滤动画文件（支持.abc和.ma文件）
            self.current_animation_files = [
                path for path in outputs 
                if path.endswith(('.abc', '.ma'))
            ]
            
            print(f"动画文件数量: {len(self.current_animation_files)}")
            
        except Exception as e:
            print(f"设置动画文件失败: {str(e)}")
            self.current_animation_files = []

    def _find_camera_file(self):
        """查找相机文件"""
        try:
            if self.manual_camera_file:
                self.current_camera_file = self.manual_camera_file
                return
            
            if not self.current_animation_files:
                print("没有动画文件，无法推导相机路径")
                self.current_camera_file = None
                return
            
            # 使用第一个动画文件推导相机路径
            animation_file = self.current_animation_files[0]
            camera_path = self.config_manager.extract_camera_path_from_animation(animation_file)
            
            if camera_path and os.path.exists(camera_path):
                self.current_camera_file = camera_path
                print(f"自动找到相机文件: {os.path.basename(camera_path)}")
            else:
                # 使用PathUtils的智能查找
                self.current_camera_file = self.path_utils.get_best_camera_file(animation_file)
                
        except Exception as e:
            print(f"查找相机文件失败: {str(e)}")
            self.current_camera_file = None

    def _update_namespaces(self):
        """更新命名空间"""
        asset_name = self.current_asset['asset_name']
        self.lookdev_namespace = f"{asset_name}_lookdev"
        self.animation_namespace = f"{asset_name}_animation"
        self.fur_namespace = f"{asset_name}_fur"
        self.cloth_namespace = f"{asset_name}_cloth"

    def _print_current_files(self):
        """打印当前文件状态"""
        print(f"\n当前文件状态:")
        print(f"  Lookdev: {os.path.basename(self.current_lookdev_file) if self.current_lookdev_file else '未找到'}")
        print(f"  动画文件: {len(self.current_animation_files)} 个")
        print(f"  相机文件: {os.path.basename(self.current_camera_file) if self.current_camera_file else '未找到'}")

    def set_manual_camera_file(self, camera_file):
        """设置手动指定的相机文件"""
        if os.path.exists(camera_file):
            self.manual_camera_file = camera_file
            self.current_camera_file = camera_file
            return True
        return False

    # ===== 主要执行步骤 =====

    def step1_import_lookdev(self):
        """步骤1: 导入Lookdev文件"""
        try:
            print("\n=== 步骤1: 导入Lookdev文件 ===")
            
            if not self.current_lookdev_file:
                print("❌ 没有可用的Lookdev文件")
                return False
            
            # 导入lookdev文件
            cmds.file(self.current_lookdev_file, i=True, namespace=self.lookdev_namespace)
            
            # 查找lookdev meshes
            self.lookdev_meshes = self._find_lookdev_meshes()
            
            if self.lookdev_meshes:
                self.scene_manager.update_assembly_status('lookdev_imported', True)
                print(f"✅ Lookdev导入成功，找到 {len(self.lookdev_meshes)} 个mesh")
                return True
            else:
                print("⚠️  Lookdev导入但未找到mesh")
                return False
                
        except Exception as e:
            print(f"❌ 导入Lookdev失败: {str(e)}")
            return False

    def step2_import_and_connect_animation_abc(self):
        """步骤2: 导入动画ABC并连接"""
        try:
            print("\n=== 步骤2: 导入动画ABC并连接 ===")
            
            if not self.current_animation_files:
                print("❌ 没有可用的动画文件")
                return False
            
            if not self.lookdev_meshes:
                print("❌ 没有Lookdev mesh，请先执行步骤1")
                return False
            
            connected_count = 0
            
            for animation_file in self.current_animation_files:
                try:
                    # 导入动画文件
                    success, new_transforms, abc_node = self.abc_importer.import_single_animation_abc(
                        animation_file, self.animation_namespace
                    )
                    
                    if success and new_transforms:
                        # 连接到lookdev
                        if self.abc_importer.connect_abc_to_lookdev(
                            new_transforms, abc_node, self.lookdev_meshes, self.lookdev_namespace
                        ):
                            connected_count += 1
                            
                            # 自动匹配解算BlendShapes（如果有的话）
                            self._auto_match_simulation_blendshapes(new_transforms, self.animation_namespace)
                            
                except Exception as e:
                    print(f"处理动画文件失败 {animation_file}: {str(e)}")
                    continue
            
            if connected_count > 0:
                # 更新时间范围
                time_range = self.abc_importer.get_time_range()
                self.start_frame, self.end_frame = time_range
                
                self.scene_manager.update_assembly_status('animation_connected', True)
                print(f"✅ 动画连接完成，成功连接 {connected_count} 个文件")
                return True
            else:
                print("❌ 没有成功连接任何动画文件")
                return False
                
        except Exception as e:
            print(f"❌ 导入连接动画ABC失败: {str(e)}")
            return False

    def step3_import_camera_abc(self):
        """步骤3: 导入动画相机ABC"""
        try:
            print("\n=== 步骤3: 导入动画相机ABC ===")
            
            if not self.current_camera_file:
                print("❌ 没有可用的相机文件")
                return False
            
            # 导入相机
            success = self.abc_importer.import_camera_abc(self.current_camera_file)
            
            if success:
                # 更新时间范围
                time_range = self.abc_importer.get_time_range()
                self.start_frame, self.end_frame = time_range
                
                self.scene_manager.update_assembly_status('camera_imported', True)
                print(f"✅ 相机导入成功")
                return True
            else:
                print("❌ 相机导入失败")
                return False
                
        except Exception as e:
            print(f"❌ 导入相机ABC失败: {str(e)}")
            return False

    def step4_setup_hair_cache(self):
        """步骤4: 设置毛发缓存路径"""
        try:
            print("\n=== 步骤4: 设置毛发缓存路径 ===")
            
            # 检查XGen状态
            if not self.xgen_manager.check_xgen_status():
                print("❌ XGen检查失败")
                return False
            
            # 获取毛发缓存模板
            hair_cache_template = self.config_manager.get_hair_cache_template()
            
            if hair_cache_template:
                # 设置XGen缓存路径
                success = self.xgen_manager.setup_xgen_cache_paths(hair_cache_template)
                
                if success:
                    # 尝试导入毛发缓存
                    asset_name = self.current_asset['asset_name']
                    fur_success = self.fur_cache_importer.import_fur_cache(
                        hair_cache_template, asset_name, self.lookdev_namespace
                    )
                    
                    self.scene_manager.update_assembly_status('hair_setup', True)
                    print("✅ 毛发缓存设置完成")
                    return True
                else:
                    print("❌ 毛发缓存设置失败")
                    return False
            else:
                print("⚠️  没有毛发缓存模板")
                return True
                
        except Exception as e:
            print(f"❌ 设置毛发缓存失败: {str(e)}")
            return False

    def step5_fix_materials(self):
        """步骤5: 检查修复材质"""
        try:
            print("\n=== 步骤5: 检查修复材质 ===")
            
            # 使用MaterialManager修复材质
            success = self.material_manager.check_and_fix_materials()
            
            if success:
                self.scene_manager.update_assembly_status('materials_fixed', True)
                print("✅ 材质检查修复完成")
                return True
            else:
                print("❌ 材质修复失败")
                return False
                
        except Exception as e:
            print(f"❌ 材质修复失败: {str(e)}")
            return False

    def step6_setup_scene(self):
        """步骤6: 设置场景参数"""
        try:
            print("\n=== 步骤6: 设置场景参数 ===")
            
            # 使用SceneManager设置场景参数
            success = self.scene_manager.setup_scene_parameters(self.start_frame, self.end_frame)
            
            if success:
                # 优化选择
                if cmds.objExists(f"{self.lookdev_namespace}:Master"):
                    cmds.select(f"{self.lookdev_namespace}:Master", replace=True)
                    print("已选择lookdev根节点")
                
                self.scene_manager.update_assembly_status('scene_configured', True)
                print("✅ 场景参数设置完成")
                return True
            else:
                print("❌ 场景设置失败")
                return False
                
        except Exception as e:
            print(f"❌ 场景设置失败: {str(e)}")
            return False

    def execute_all_steps(self):
        """执行所有步骤"""
        try:
            print("\n" + "=" * 50)
            print("开始执行所有组装步骤")
            print("=" * 50)
            
            if not self.current_asset:
                print("❌ 请先设置当前工作的资产")
                return False
            
            steps = [
                (self.step1_import_lookdev, "导入Lookdev"),
                (self.step2_import_and_connect_animation_abc, "导入动画ABC"),
                (self.step3_import_camera_abc, "导入相机ABC"),
                (self.step4_setup_hair_cache, "设置毛发缓存"),
                (self.step5_fix_materials, "修复材质"),
                (self.step6_setup_scene, "设置场景"),
            ]
            
            failed_steps = []
            
            for step_func, step_name in steps:
                try:
                    success = step_func()
                    if not success:
                        failed_steps.append(step_name)
                except Exception as e:
                    print(f"❌ {step_name} 执行异常: {str(e)}")
                    failed_steps.append(step_name)
            
            # 最终检查
            final_check_success = self.scene_manager.final_check()
            
            if not failed_steps and final_check_success:
                print("\n🎉 所有步骤执行完成！")
                return True
            else:
                if failed_steps:
                    print(f"\n⚠️  以下步骤执行失败: {', '.join(failed_steps)}")
                if not final_check_success:
                    print("⚠️  最终检查发现问题")
                return False
                
        except Exception as e:
            print(f"❌ 执行过程出错: {str(e)}")
            return False

    # ===== 辅助方法 =====

    def _find_lookdev_meshes(self):
        """查找Lookdev meshes"""
        try:
            lookdev_meshes = {}
            
            # 获取命名空间下的所有mesh
            all_meshes = cmds.ls(f"{self.lookdev_namespace}:*", type='mesh', long=True)
            
            for mesh_shape in all_meshes:
                try:
                    # 跳过中间形状
                    if cmds.getAttr(f"{mesh_shape}.intermediateObject"):
                        continue
                    
                    # 获取transform
                    mesh_transform = cmds.listRelatives(mesh_shape, parent=True, fullPath=True)[0]
                    
                    # 清理名称
                    clean_name = self._clean_mesh_name(mesh_transform)
                    
                    lookdev_meshes[clean_name] = {
                        'transform': mesh_transform,
                        'shape': mesh_shape,
                        'original_name': mesh_transform.split('|')[-1]
                    }
                    
                except Exception as e:
                    print(f"处理mesh失败 {mesh_shape}: {str(e)}")
                    continue
            
            print(f"找到 {len(lookdev_meshes)} 个Lookdev mesh")
            return lookdev_meshes
            
        except Exception as e:
            print(f"查找Lookdev meshes失败: {str(e)}")
            return {}

    def _clean_mesh_name(self, mesh_name):
        """清理mesh名称"""
        # 获取最后一部分（去除路径）
        name = mesh_name.split('|')[-1]
        
        # 移除命名空间
        if ':' in name:
            name = name.split(':')[-1]
        
        # 移除数字后缀
        import re
        name = re.sub(r'_\d+$', '', name)
        
        # 移除Shape后缀
        if name.endswith('Shape'):
            name = name[:-5]
        
        return name

    def _auto_match_simulation_blendshapes(self, abc_transforms, abc_namespace):
        """自动匹配解算BlendShapes"""
        try:
            print("\n自动匹配解算BlendShapes...")
            
            # 获取去除命名空间的ABC对象名称
            cleaned_abc_objects = []
            for transform in abc_transforms:
                clean_name = transform.split(':')[-1] if ':' in transform else transform
                cleaned_abc_objects.append(clean_name)
            
            # 查找对应的lookdev对象
            lookdev_objects = []
            for abc_name in cleaned_abc_objects:
                # 在lookdev命名空间中查找匹配对象
                lookdev_path = f"{self.lookdev_namespace}:{abc_name}"
                if cmds.objExists(lookdev_path):
                    lookdev_objects.append(lookdev_path)
            
            if cleaned_abc_objects and lookdev_objects:
                # 使用BlendshapeManager创建动态BlendShapes
                results = self.blendshape_manager.create_dynamic_blendshapes(
                    abc_transforms, lookdev_objects, conflict_check=True
                )
                
                if results['success'] > 0:
                    print(f"✅ 自动创建了 {results['success']} 个解算BlendShape")
                
        except Exception as e:
            print(f"自动匹配解算BlendShapes失败: {str(e)}")

    # ===== 手动工具方法 =====

    def create_dynamic_blendshapes(self, source_objects, target_objects, conflict_check=True):
        """创建动态BlendShapes（公开接口）"""
        return self.blendshape_manager.create_dynamic_blendshapes(
            source_objects, target_objects, conflict_check
        )

    def _handle_special_groups_blendshape(self):
        """处理特殊组的blendShape连接"""
        try:
            print("\n处理特殊组blendShape连接...")
            
            # 查找特殊组
            special_groups = GroupFinder.find_special_groups(self.lookdev_namespace)
            
            if len(special_groups) >= 2:
                # 使用BlendshapeManager处理
                results = self.blendshape_manager.create_dynamic_blendshapes(
                    [special_groups[0]], [special_groups[1]], conflict_check=True
                )
                
                return results['success'] > 0
            else:
                print("未找到足够的特殊组")
                return False
                
        except Exception as e:
            print(f"处理特殊组失败: {str(e)}")
            return False

    def _find_clothes_group(self, asset_name=None):
        """查找clothes组"""
        return GroupFinder.find_clothes_group(self.lookdev_namespace, asset_name)

    def _create_cloth_blendshapes(self, cloth_group, clothes_group):
        """创建布料BlendShapes"""
        return self.cloth_blendshape_manager.create_cloth_blendshapes(cloth_group, clothes_group)

    def _create_fur_container_group(self, original_fur_group):
        """创建毛发容器组"""
        asset_name = self.current_asset.get('asset_name', 'fur') if self.current_asset else 'fur'
        return GroupFinder.create_fur_container_group(original_fur_group, asset_name)

    # ===== 状态和信息方法 =====

    def get_assembly_status(self):
        """获取组装状态"""
        return self.scene_manager.get_assembly_status()

    def reset_assembly_status(self):
        """重置组装状态"""
        self.scene_manager.reset_assembly_status()

    def get_current_config_summary(self):
        """获取当前配置摘要"""
        if not self.current_asset:
            return {"error": "没有设置当前资产"}
        
        return self.scene_manager.get_current_config_summary(
            self.current_asset['asset_name'],
            self.current_lookdev_file,
            self.current_animation_files,
            self.current_camera_file,
            self.lookdev_namespace
        )

    def check_xgen_status(self):
        """检查XGen状态"""
        return self.xgen_manager.check_xgen_status()

    def _final_check(self):
        """最终检查"""
        return self.scene_manager.final_check()


# 为了向后兼容，保留一些旧的方法名
class CoreAssemblerCompat(CoreAssembler):
    """向后兼容的CoreAssembler类"""
    
    def check_and_fix_materials(self):
        """向后兼容的材质修复方法"""
        return self.step5_fix_materials()
    
    def setup_scene_settings(self):
        """向后兼容的场景设置方法"""
        return self.step6_setup_scene()
    
    def import_lookdev(self):
        """向后兼容的lookdev导入方法"""
        return self.step1_import_lookdev()
    
    def import_and_connect_animation_abc(self):
        """向后兼容的动画导入方法"""
        return self.step2_import_and_connect_animation_abc()
    
    def import_camera_abc(self):
        """向后兼容的相机导入方法"""
        return self.step3_import_camera_abc()
    
    def setup_hair_cache(self):
        """向后兼容的毛发设置方法"""
        return self.step4_setup_hair_cache()