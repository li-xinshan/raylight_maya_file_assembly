"""
场景管理模块
负责处理场景设置、查找和管理功能
"""

import maya.cmds as cmds
import maya.mel as mel
import os
import re


class SceneManager:
    """场景管理器"""
    
    def __init__(self):
        self.assembly_status = {
            'lookdev_imported': False,
            'animation_connected': False,
            'camera_imported': False,
            'hair_setup': False,
            'materials_fixed': False,
            'scene_configured': False
        }
        self.start_frame = 1
        self.end_frame = 100
    
    def setup_scene_parameters(self, start_frame=None, end_frame=None):
        """
        设置场景参数
        
        Args:
            start_frame (int): 开始帧
            end_frame (int): 结束帧
            
        Returns:
            bool: 设置是否成功
        """
        try:
            print("\n=== 设置场景参数 ===")
            
            # 更新时间范围
            if start_frame is not None:
                self.start_frame = start_frame
            if end_frame is not None:
                self.end_frame = end_frame
            
            # 设置时间范围
            cmds.playbackOptions(min=self.start_frame, max=self.end_frame)
            cmds.currentTime(self.start_frame)
            print(f"时间范围: {self.start_frame} - {self.end_frame}")
            
            # 设置单位
            cmds.currentUnit(linear="cm", time="film")
            print("单位设置: 厘米 (长度), Film (时间)")
            
            # 设置视口显示
            self._setup_viewport_display()
            
            # 优化场景设置
            self._optimize_scene_settings()
            
            self.assembly_status['scene_configured'] = True
            print("✅ 场景参数设置完成")
            return True
            
        except Exception as e:
            print(f"❌ 场景设置失败: {str(e)}")
            return False
    
    def _setup_viewport_display(self):
        """设置视口显示"""
        try:
            # 获取当前焦点面板
            panel = cmds.getPanel(withFocus=True)
            
            if panel and cmds.modelPanel(panel, query=True, exists=True):
                # 启用纹理显示
                cmds.modelEditor(panel, edit=True, displayTextures=True)
                
                # 设置光照模式
                cmds.modelEditor(panel, edit=True, displayLights="all")
                
                # 启用材质显示
                cmds.modelEditor(panel, edit=True, useDefaultMaterial=False)
                
                print("视口显示已更新")
            
        except Exception as e:
            print(f"设置视口显示失败: {str(e)}")
    
    def _optimize_scene_settings(self):
        """优化场景设置"""
        try:
            # 设置自动关键帧
            cmds.autoKeyframe(state=False)
            
            # 设置选择高亮
            cmds.selectMode(object=True)
            
            # 优化撤销队列
            cmds.undoInfo(state=True, infinity=False, length=50)
            
            print("场景设置已优化")
            
        except Exception as e:
            print(f"优化场景设置失败: {str(e)}")
    
    def reset_assembly_status(self):
        """重置组装状态"""
        for key in self.assembly_status:
            self.assembly_status[key] = False
    
    def get_assembly_status(self):
        """获取组装状态"""
        return self.assembly_status.copy()
    
    def update_assembly_status(self, step, status):
        """更新组装状态"""
        if step in self.assembly_status:
            self.assembly_status[step] = status
    
    def is_assembly_complete(self):
        """检查组装是否完成"""
        return all(self.assembly_status.values())
    
    def get_current_config_summary(self, asset_name, lookdev_file, animation_files, camera_file, namespace):
        """
        获取当前配置摘要
        
        Returns:
            dict: 配置摘要
        """
        summary = {
            'asset': asset_name or "未设置",
            'lookdev_file': os.path.basename(lookdev_file) if lookdev_file else "未找到",
            'animation_files_count': len(animation_files) if animation_files else 0,
            'camera_file': os.path.basename(camera_file) if camera_file else "未找到",
            'namespace': namespace or "未设置",
            'time_range': f"{self.start_frame} - {self.end_frame}",
            'status': self.assembly_status.copy()
        }
        
        return summary
    
    def final_check(self):
        """最终检查"""
        try:
            print("\n=== 最终检查 ===")
            
            issues = []
            
            # 检查场景完整性
            scene_issues = self._check_scene_integrity()
            issues.extend(scene_issues)
            
            # 检查性能
            performance_issues = self._check_scene_performance()
            issues.extend(performance_issues)
            
            # 检查命名规范
            naming_issues = self._check_naming_conventions()
            issues.extend(naming_issues)
            
            if not issues:
                print("✅ 最终检查通过，场景组装完成")
                return True
            else:
                print(f"⚠️  发现 {len(issues)} 个问题:")
                for issue in issues[:10]:  # 只显示前10个问题
                    print(f"  - {issue}")
                if len(issues) > 10:
                    print(f"  ... 还有 {len(issues) - 10} 个问题")
                return False
                
        except Exception as e:
            print(f"❌ 最终检查失败: {str(e)}")
            return False
    
    def _check_scene_integrity(self):
        """检查场景完整性"""
        issues = []
        
        try:
            # 检查是否有几何体
            meshes = cmds.ls(type='mesh', noIntermediate=True)
            if not meshes:
                issues.append("场景中没有几何体")
            
            # 检查是否有相机
            cameras = cmds.ls(type='camera')
            user_cameras = [cam for cam in cameras if cam not in ['frontShape', 'perspShape', 'sideShape', 'topShape']]
            if not user_cameras:
                issues.append("场景中没有用户相机")
            
            # 检查是否有材质
            materials = cmds.ls(materials=True)
            user_materials = [mat for mat in materials if mat not in ['lambert1', 'particleCloud1', 'shaderGlow1']]
            if not user_materials:
                issues.append("场景中没有用户材质")
            
            # 检查时间范围
            if self.start_frame >= self.end_frame:
                issues.append("时间范围设置错误")
                
        except Exception as e:
            issues.append(f"检查场景完整性失败: {str(e)}")
        
        return issues
    
    def _check_scene_performance(self):
        """检查场景性能"""
        issues = []
        
        try:
            # 检查多边形数量
            total_faces = 0
            meshes = cmds.ls(type='mesh', noIntermediate=True)
            
            for mesh in meshes:
                try:
                    face_count = cmds.polyEvaluate(mesh, face=True)
                    total_faces += face_count
                except:
                    continue
            
            if total_faces > 1000000:  # 100万面
                issues.append(f"场景多边形数量过多: {total_faces:,} 面")
            
            # 检查纹理分辨率
            high_res_textures = []
            file_nodes = cmds.ls(type='file')
            
            for file_node in file_nodes:
                try:
                    texture_path = cmds.getAttr(f"{file_node}.fileTextureName")
                    if texture_path and os.path.exists(texture_path):
                        # 简单检查（基于文件大小）
                        file_size = os.path.getsize(texture_path)
                        if file_size > 50 * 1024 * 1024:  # 50MB
                            high_res_textures.append(os.path.basename(texture_path))
                except:
                    continue
            
            if high_res_textures:
                issues.append(f"发现 {len(high_res_textures)} 个大纹理文件")
            
            # 检查复杂节点网络
            complex_materials = []
            shading_groups = cmds.ls(type='shadingEngine')
            
            for sg in shading_groups:
                if sg == 'initialShadingGroup':
                    continue
                
                try:
                    # 计算连接到此着色组的节点数
                    connected_nodes = cmds.listHistory(sg)
                    if len(connected_nodes) > 50:
                        complex_materials.append(sg)
                except:
                    continue
            
            if complex_materials:
                issues.append(f"发现 {len(complex_materials)} 个复杂材质网络")
                
        except Exception as e:
            issues.append(f"检查场景性能失败: {str(e)}")
        
        return issues
    
    def _check_naming_conventions(self):
        """检查命名规范"""
        issues = []
        
        try:
            # 检查对象命名
            all_transforms = cmds.ls(type='transform')
            
            problematic_names = []
            for transform in all_transforms:
                # 检查是否有特殊字符
                if re.search(r'[^\w_:]', transform):
                    problematic_names.append(transform)
                
                # 检查是否以数字开头
                base_name = transform.split(':')[-1]  # 去除命名空间
                if base_name and base_name[0].isdigit():
                    problematic_names.append(transform)
            
            if problematic_names:
                issues.append(f"发现 {len(problematic_names)} 个命名不规范的对象")
            
            # 检查重复名称
            name_counts = {}
            for transform in all_transforms:
                base_name = transform.split(':')[-1]
                name_counts[base_name] = name_counts.get(base_name, 0) + 1
            
            duplicates = [name for name, count in name_counts.items() if count > 1]
            if duplicates:
                issues.append(f"发现 {len(duplicates)} 个重复名称")
                
        except Exception as e:
            issues.append(f"检查命名规范失败: {str(e)}")
        
        return issues


class LookdevFinder:
    """Lookdev文件查找器"""
    
    def __init__(self, file_manager):
        self.file_manager = file_manager
    
    def find_lookdev_file(self, asset_name, asset_type, lookdev_dir):
        """
        查找Lookdev文件
        
        Args:
            asset_name (str): 资产名称
            asset_type (str): 资产类型
            lookdev_dir (str): Lookdev目录
            
        Returns:
            str: Lookdev文件路径，如果未找到返回None
        """
        try:
            print(f"\n查找Lookdev文件...")
            print(f"资产: {asset_name} ({asset_type})")
            print(f"搜索目录: {lookdev_dir}")
            
            if not os.path.exists(lookdev_dir):
                print(f"❌ Lookdev目录不存在: {lookdev_dir}")
                return None
            
            # 使用FileManager查找文件
            lookdev_files = self.file_manager.find_lookdev_files(lookdev_dir)
            
            if not lookdev_files:
                print(f"❌ 未找到Lookdev文件")
                return None
            
            # 过滤匹配的文件
            matching_files = self._filter_matching_files(lookdev_files, asset_name, asset_type)
            
            if matching_files:
                # 获取最新版本
                latest_file = self.file_manager.get_latest_lookdev_file(lookdev_dir)
                
                if latest_file in matching_files:
                    print(f"✅ 找到Lookdev文件: {os.path.basename(latest_file)}")
                    return latest_file
                else:
                    # 使用匹配度最高的文件
                    best_file = matching_files[0]
                    print(f"✅ 找到Lookdev文件: {os.path.basename(best_file)}")
                    return best_file
            else:
                print(f"❌ 未找到匹配的Lookdev文件")
                return None
                
        except Exception as e:
            print(f"❌ 查找Lookdev文件失败: {str(e)}")
            return None
    
    def _filter_matching_files(self, lookdev_files, asset_name, asset_type):
        """过滤匹配的文件"""
        matching_files = []
        
        for file_path in lookdev_files:
            filename = os.path.basename(file_path)
            filename_lower = filename.lower()
            
            # 检查是否包含资产名称
            if asset_name.lower() in filename_lower:
                matching_files.append(file_path)
                continue
            
            # 检查是否包含资产类型
            if asset_type.lower() in filename_lower:
                matching_files.append(file_path)
                continue
        
        return matching_files


class GroupFinder:
    """组查找器"""
    
    @staticmethod
    def find_clothes_group(lookdev_namespace, asset_name=None):
        """
        查找lookdev中的clothes组
        
        Args:
            lookdev_namespace (str): Lookdev命名空间
            asset_name (str): 资产名称（可选）
            
        Returns:
            str: clothes组路径，如果未找到返回None
        """
        try:
            # 使用传入的asset_name或默认值
            if not asset_name:
                asset_name = 'dwl'
            
            print(f"查找clothes组，lookdev命名空间: {lookdev_namespace}, 资产名称: {asset_name}")
            
            # 方法1: 直接构建预期路径
            expected_paths = [
                # 使用动态资产名称构建路径
                f"|{lookdev_namespace}:Master|{lookdev_namespace}:GEO|{lookdev_namespace}:HIG|{lookdev_namespace}:chr_{asset_name}_hig_grp|{lookdev_namespace}:Clothes_grp|{lookdev_namespace}:{asset_name}_cloth_group",
                f"|{lookdev_namespace}:Master|{lookdev_namespace}:GEO|{lookdev_namespace}:HIG|{lookdev_namespace}:chr_{asset_name}_hig_grp|{lookdev_namespace}:Clothes_grp",
                # 保留原始dwl作为备选
                f"|{lookdev_namespace}:Master|{lookdev_namespace}:GEO|{lookdev_namespace}:HIG|{lookdev_namespace}:chr_dwl_hig_grp|{lookdev_namespace}:Clothes_grp|{lookdev_namespace}:dwl_cloth_group",
                f"|{lookdev_namespace}:Master|{lookdev_namespace}:GEO|{lookdev_namespace}:HIG|{lookdev_namespace}:chr_dwl_hig_grp|{lookdev_namespace}:Clothes_grp"
            ]
            
            for path in expected_paths:
                print(f"检查路径: {path}")
                if cmds.objExists(path):
                    print(f"✅ 找到clothes组: {path}")
                    return path
            
            # 方法2: 通过搜索查找
            print("使用搜索方法查找clothes组...")
            
            # 搜索包含"clothes"或"cloth"的组
            all_transforms = cmds.ls(f"{lookdev_namespace}:*", type='transform', long=True)
            
            for transform in all_transforms:
                transform_name = transform.split('|')[-1].lower()
                if 'clothes' in transform_name or 'cloth' in transform_name:
                    print(f"找到可能的clothes组: {transform}")
                    return transform
            
            print("❌ 未找到clothes组")
            return None
            
        except Exception as e:
            print(f"查找clothes组失败: {str(e)}")
            return None
    
    @staticmethod
    def find_growthmesh_group(lookdev_namespace):
        """查找growthmesh组"""
        try:
            print(f"查找growthmesh组，命名空间: {lookdev_namespace}")
            
            # 常见的growthmesh组路径
            possible_paths = [
                f"|{lookdev_namespace}:Master|{lookdev_namespace}:GEO|{lookdev_namespace}:HIG|{lookdev_namespace}:growthmesh_grp",
                f"|{lookdev_namespace}:Master|{lookdev_namespace}:GEO|{lookdev_namespace}:growthmesh_grp",
                f"|{lookdev_namespace}:growthmesh_grp",
            ]
            
            for path in possible_paths:
                if cmds.objExists(path):
                    print(f"✅ 找到growthmesh组: {path}")
                    return path
            
            # 搜索方法
            all_transforms = cmds.ls(f"{lookdev_namespace}:*", type='transform', long=True)
            
            for transform in all_transforms:
                transform_name = transform.split('|')[-1].lower()
                if 'growthmesh' in transform_name or 'growth' in transform_name:
                    print(f"✅ 找到growthmesh组: {transform}")
                    return transform
            
            print("❌ 未找到growthmesh组")
            return None
            
        except Exception as e:
            print(f"查找growthmesh组失败: {str(e)}")
            return None
    
    @staticmethod
    def find_special_groups(lookdev_namespace):
        """查找特殊组"""
        try:
            print(f"查找特殊组，命名空间: {lookdev_namespace}")
            
            special_groups = []
            
            # 查找所有transform
            all_transforms = cmds.ls(f"{lookdev_namespace}:*", type='transform', long=True)
            
            # 定义特殊组关键词
            special_keywords = ['special', 'extra', 'additional', 'misc', 'other']
            
            for transform in all_transforms:
                transform_name = transform.split('|')[-1].lower()
                
                for keyword in special_keywords:
                    if keyword in transform_name:
                        special_groups.append(transform)
                        break
            
            if special_groups:
                print(f"✅ 找到 {len(special_groups)} 个特殊组")
                for group in special_groups:
                    print(f"  - {group}")
            else:
                print("❌ 未找到特殊组")
            
            return special_groups
            
        except Exception as e:
            print(f"查找特殊组失败: {str(e)}")
            return []
    
    @staticmethod
    def create_fur_container_group(original_fur_group, asset_name):
        """为fur组创建管理容器组"""
        try:
            # 获取资产名称用于命名
            if not asset_name:
                asset_name = "fur"
            
            # 创建容器组名称（不使用命名空间，在根级别创建）
            container_name = f"{asset_name}_fur_cache_grp"
            
            # 检查是否已存在同名组
            if cmds.objExists(container_name):
                # 如果存在，生成唯一名称
                counter = 1
                while cmds.objExists(f"{container_name}_{counter}"):
                    counter += 1
                container_name = f"{container_name}_{counter}"
            
            # 创建空组
            container_group = cmds.group(empty=True, name=container_name)
            print(f"创建fur容器组: {container_group}")
            
            # 将原始fur组作为子组放入容器组
            try:
                cmds.parent(original_fur_group, container_group)
                print(f"将 {original_fur_group} 放入容器组")
            except Exception as e:
                print(f"⚠️  无法将fur组放入容器组: {str(e)}")
                # 如果parenting失败，删除容器组并返回None
                cmds.delete(container_group)
                return None
            
            # 设置容器组的属性
            try:
                # 添加自定义属性标识这是fur缓存组
                cmds.addAttr(container_group, longName="fur_cache_group", dataType="string")
                cmds.setAttr(f"{container_group}.fur_cache_group", "fur_simulation_cache", type="string")
                
                # 设置组的显示颜色为白色
                cmds.setAttr(f"{container_group}.useOutlinerColor", 1)
                cmds.setAttr(f"{container_group}.outlinerColor", 1.0, 1.0, 1.0)  # 白色
                
                print(f"设置fur容器组属性完成")
            except Exception as e:
                print(f"⚠️  设置容器组属性失败: {str(e)}")
            
            return container_group
            
        except Exception as e:
            print(f"❌ 创建fur容器组失败: {str(e)}")
            return None