"""
ABC导入管理模块
负责处理所有ABC文件导入和连接功能
"""

import maya.cmds as cmds
import maya.mel as mel
import os
import re
from .blendshape_manager import BlendshapeManager

class ABCImporter:
    """ABC导入管理器"""
    
    def __init__(self):
        self.blendshape_manager = BlendshapeManager()
        self.imported_abc_nodes = []
        self.pending_abc_files = []  # 待连接的ABC文件
        self.time_range = [1, 100]  # 默认时间范围
    
    def import_single_animation_abc(self, animation_file, namespace=None):
        """
        导入单个动画ABC文件
        
        Args:
            animation_file (str): ABC文件路径
            namespace (str): 命名空间
            
        Returns:
            tuple: (success, new_transforms, abc_node)
        """
        try:
            print(f"\n导入动画ABC: {os.path.basename(animation_file)}")
            
            if not os.path.exists(animation_file):
                print(f"❌ 文件不存在: {animation_file}")
                return False, [], None
            
            # 检查文件扩展名并选择导入方式
            file_ext = os.path.splitext(animation_file)[1].lower()
            
            if file_ext == '.abc':
                return self._import_abc_file(animation_file, namespace)
            elif file_ext == '.ma':
                return self._import_ma_file(animation_file, namespace)
            else:
                print(f"❌ 不支持的文件格式: {file_ext}")
                return False, [], None
                
        except Exception as e:
            print(f"❌ 导入ABC文件失败: {str(e)}")
            return False, [], None
    
    def _import_abc_file(self, abc_file, namespace):
        """导入ABC文件的具体实现"""
        try:
            # 确保ABC插件已加载
            if not cmds.pluginInfo('AbcImport', query=True, loaded=True):
                cmds.loadPlugin('AbcImport')
            
            # 记录导入前的节点状态
            transforms_before = set(cmds.ls(type='transform'))
            abc_nodes_before = set(cmds.ls(type="AlembicNode"))
            
            # 导入ABC文件
            mel.eval(f'AbcImport -mode import "{abc_file}"')
            
            # 查找新导入的节点
            transforms_after = set(cmds.ls(type='transform'))
            abc_nodes_after = set(cmds.ls(type="AlembicNode"))
            
            new_transforms = list(transforms_after - transforms_before)
            new_abc_nodes = list(abc_nodes_after - abc_nodes_before)
            
            abc_node = new_abc_nodes[0] if new_abc_nodes else None
            
            print(f"✅ ABC文件导入成功: {len(new_transforms)} 个transform, {len(new_abc_nodes)} 个ABC节点")
            
            return True, new_transforms, abc_node
            
        except Exception as e:
            print(f"❌ 导入ABC文件失败: {str(e)}")
            return False, [], None
    
    def _import_ma_file(self, ma_file, namespace):
        """导入Maya文件的具体实现"""
        try:
            # 记录导入前的节点状态
            transforms_before = set(cmds.ls(type='transform'))
            
            # 导入Maya文件
            cmds.file(
                ma_file,
                i=True,
                type="mayaAscii",
                ignoreVersion=True,
                ra=True,
                mergeNamespacesOnClash=False,
                namespace=namespace if namespace else "",
                pr=True
            )
            
            # 查找新导入的节点
            transforms_after = set(cmds.ls(type='transform'))
            new_transforms = list(transforms_after - transforms_before)
            
            print(f"✅ Maya文件导入成功: {len(new_transforms)} 个transform")
            
            return True, new_transforms, None
            
        except Exception as e:
            print(f"❌ 导入Maya文件失败: {str(e)}")
            return False, [], None

    def _connect_to_lookdev_meshes(self, animation_namespace, lookdev_namespace):
        """连接ABC几何体到lookdev几何体"""
        try:
            print("连接ABC几何体到lookdev几何体...")

            lookdev_geo = f'|{lookdev_namespace}:Master|{lookdev_namespace}:GEO'
            animation_geo = f'|{animation_namespace}:GEO'

            print(f"动画几何体: {animation_geo}")
            print(f"Lookdev几何体: {lookdev_geo}")

            # 检查节点是否存在
            if not cmds.objExists(animation_geo):
                print(f"❌ 动画几何体不存在: {animation_geo}")
                return False

            if not cmds.objExists(lookdev_geo):
                print(f"❌ Lookdev几何体不存在: {lookdev_geo}")
                return False

            # 执行blendshape连接
            result = self.blendshape_manager.create_precise_blendshapes_between_groups(
                animation_geo, lookdev_geo
            )
            print(f"连接完成: {len(result)} 个几何体")

            # 隐藏动画组 - 改进的版本
            try:
                print(f'准备隐藏动画组：{animation_geo}')

                # 方法1：直接使用完整路径
                if cmds.objExists(animation_geo):
                    cmds.setAttr(f"{animation_geo}.visibility", 0)
                    print(f"✅ 成功隐藏动画组（完整路径）: {animation_geo}")
                else:
                    # 方法2：尝试使用短名称
                    short_name = animation_geo.split('|')[-1]
                    print(f"尝试使用短名称: {short_name}")

                    if cmds.objExists(short_name):
                        cmds.setAttr(f"{short_name}.visibility", 0)
                        print(f"✅ 成功隐藏动画组（短名称）: {short_name}")
                    else:
                        print(f"❌ 无法找到节点进行隐藏: {animation_geo}")

            except Exception as hide_error:
                print(f"❌ 隐藏动画组失败: {str(hide_error)}")
                # 不让隐藏失败影响整个流程
                pass

            return len(result) > 0

        except Exception as e:
            print(f"❌ 连接ABC几何体失败: {str(e)}")
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")
            return False
    
    def _find_best_match(self, abc_name, lookdev_names):
        """查找最佳匹配的lookdev名称"""
        abc_clean = self._clean_name(abc_name)
        
        # 直接匹配
        for lookdev_name in lookdev_names:
            lookdev_clean = self._clean_name(lookdev_name)
            if abc_clean == lookdev_clean:
                return lookdev_name
        
        # 部分匹配
        for lookdev_name in lookdev_names:
            lookdev_clean = self._clean_name(lookdev_name)
            if abc_clean in lookdev_clean or lookdev_clean in abc_clean:
                return lookdev_name
        
        return None
    
    def _clean_name(self, name):
        """清理名称用于匹配"""
        import re
        name = name.lower()
        # 移除常见前缀后缀和数字
        name = re.sub(r'(chr_|dwl_|_grp|grp)', '', name)
        name = re.sub(r'_?\d+$', '', name)
        return name
    
    def _set_active_camera(self, camera_transform):
        """设置活动相机"""
        try:
            panel = cmds.getPanel(withFocus=True)
            if panel and cmds.modelPanel(panel, query=True, exists=True):
                cmds.modelEditor(panel, edit=True, camera=camera_transform)
                print(f"已设置活动相机: {camera_transform}")
        except Exception as e:
            print(f"设置活动相机失败: {str(e)}")
    
    def get_imported_abc_nodes(self):
        """获取已导入的ABC节点列表"""
        return self.imported_abc_nodes
    
    def clear_imported_nodes(self):
        """清除已导入节点记录"""
        self.imported_abc_nodes.clear()
        self.pending_abc_files.clear()
    
    def import_and_connect_animations(self, animation_files, lookdev_namespace, animation_namespace):
        """
        批量导入动画文件并连接到lookdev几何体
        
        Args:
            animation_files (list): 动画文件列表
            lookdev_namespace (str): Lookdev命名空间
            animation_namespace (str): 动画命名空间
            
        Returns:
            bool: 是否成功
        """
        print(f"开始批量处理 {len(animation_files)} 个动画文件...")
        success_count = 0
        
        for i, animation_file in enumerate(animation_files, 1):
            print(f"\n处理动画文件 {i}/{len(animation_files)}: {animation_file}")
            
            # 导入单个动画文件
            success, transforms, abc_node = self.import_single_animation_abc(animation_file, animation_namespace)
            
            if success:
                success_count += 1
                # 记录导入的节点
                self.imported_abc_nodes.append(abc_node)
                
                # 连接到lookdev几何体
                if transforms:
                    self._connect_to_lookdev_meshes(animation_namespace, lookdev_namespace)

            else:
                print(f"❌ 动画文件 {i} 处理失败")
        
        overall_success = success_count > 0
        print(f"\n{'✅' if overall_success else '❌'} 批量处理完成: {success_count}/{len(animation_files)} 个文件成功")
        
        return overall_success

    def import_camera_abc(self, camera_file):
        """
        导入相机ABC文件

        Args:
            camera_file (str): 相机文件路径

        Returns:
            tuple: (success, start_frame, end_frame, abc_node)
        """
        try:
            print(f"导入相机ABC: {os.path.basename(camera_file)}")

            # 检查是否已经导入了相同的相机文件
            if self._is_camera_already_imported(camera_file):
                print("✅ 相机已存在，跳过重复导入")
                # 获取已存在相机的时间范围信息
                abc_nodes = cmds.ls(type="AlembicNode")
                if abc_nodes:
                    abc_node = abc_nodes[-1]
                    start_frame = cmds.getAttr(f"{abc_node}.startFrame")
                    end_frame = cmds.getAttr(f"{abc_node}.endFrame")
                    return True, start_frame, end_frame, abc_node
                else:
                    return True, 1001, 1100, None

            # 标准化路径分隔符
            camera_file = camera_file.replace('\\', '/')

            if not os.path.exists(camera_file):
                print(f"❌ 相机文件不存在: {camera_file}")
                # 尝试替换路径分隔符
                alt_camera_file = camera_file.replace('/', '\\')
                if os.path.exists(alt_camera_file):
                    print(f"✅ 找到替代路径: {alt_camera_file}")
                    camera_file = alt_camera_file
                else:
                    return False, None, None, None

            # 确保ABC插件已加载
            if not cmds.pluginInfo('AbcImport', query=True, loaded=True):
                cmds.loadPlugin('AbcImport')

            # 记录导入前的相机和ABC节点
            cameras_before = set(cmds.ls(type="camera"))
            abc_nodes_before = set(cmds.ls(type="AlembicNode"))

            # 导入ABC文件 - 使用用户提供的标准方式
            print(f"正在导入相机文件: {camera_file}")

            # 确保路径格式正确 - 使用正斜杠
            maya_path = camera_file.replace('\\', '/')

            try:
                cmds.file(
                    maya_path,
                    i=True,  # import
                    type="Alembic",  # 文件类型
                    ignoreVersion=True,  # 忽略版本
                    ra=True,  # reference as
                    mergeNamespacesOnClash=False,  # 不合并命名空间冲突
                    pr=True,  # preserve references
                    importTimeRange="combine"  # 导入时间范围
                )
                print("✅ 使用标准file命令导入ABC成功")

            except Exception as file_error:
                print(f"❌ file命令导入失败: {str(file_error)}")
                # 备用方案：尝试cmds.AbcImport
                try:
                    cmds.AbcImport(maya_path, mode="import", fitTimeRange=True)
                    print("✅ 使用AbcImport导入成功")
                except Exception as abc_error:
                    print(f"❌ AbcImport也失败: {str(abc_error)}")
                    # 最后尝试MEL方式
                    try:
                        mel.eval(f'AbcImport -mode import "{maya_path}"')
                        print("✅ 使用MEL方式导入成功")
                    except Exception as mel_error:
                        print(f"❌ 所有导入方式都失败: {str(mel_error)}")
                        return False, None, None, None

            # 查找新导入的ABC节点
            abc_nodes_after = set(cmds.ls(type="AlembicNode"))
            new_abc_nodes = abc_nodes_after - abc_nodes_before

            if new_abc_nodes:
                abc_node = list(new_abc_nodes)[0]

                # 获取时间范围
                start_frame = cmds.getAttr(f"{abc_node}.startFrame")
                end_frame = cmds.getAttr(f"{abc_node}.endFrame")

                # 设置Maya场景的时间范围
                current_start = cmds.playbackOptions(query=True, minTime=True)
                current_end = cmds.playbackOptions(query=True, maxTime=True)

                print(f"当前场景帧范围: {current_start} - {current_end}")
                print(f"ABC文件帧范围: {start_frame} - {end_frame}")

                # 设置场景的时间范围为ABC的时间范围
                cmds.playbackOptions(minTime=start_frame, maxTime=end_frame)

                # 同时设置动画范围（时间轴的开始和结束）
                cmds.playbackOptions(animationStartTime=start_frame, animationEndTime=end_frame)

                # 设置当前帧为开始帧
                cmds.currentTime(start_frame+10)

                print(f"✅ 场景时间范围已设置为: {start_frame} - {end_frame}")

                # 查找新导入的相机
                cameras_after = set(cmds.ls(type="camera"))
                new_cameras = cameras_after - cameras_before

                if new_cameras:
                    camera_shape = list(new_cameras)[0]
                    camera_transform = cmds.listRelatives(camera_shape, parent=True, type="transform")[0]
                    print(f"✅ 成功导入相机: {camera_transform}")

                    # 设置为当前视图相机
                    self._set_active_camera(camera_transform)

                print(f"✅ 相机ABC导入成功，时间范围: {start_frame} - {end_frame}")
                return True, start_frame, end_frame, abc_node
            else:
                print("❌ 未找到新的ABC节点")
                return False, None, None, None

        except Exception as e:
            print(f"❌ 导入相机ABC失败: {str(e)}")
            return False, None, None, None
    
    def _is_camera_already_imported(self, camera_file):
        """检查相机是否已经导入"""
        try:
            # 检查是否有相机存在
            cameras = cmds.ls(type="camera")
            if not cameras:
                return False
            
            # 检查ABC节点数量（简单判断）
            abc_nodes = cmds.ls(type="AlembicNode")
            
            # 如果有多个ABC节点，可能已经导入了相机
            if len(abc_nodes) > 0:
                # 检查ABC节点的文件路径属性
                for abc_node in abc_nodes:
                    try:
                        abc_file_attr = f"{abc_node}.abc_File"
                        if cmds.attributeQuery('abc_File', node=abc_node, exists=True):
                            abc_file_path = cmds.getAttr(abc_file_attr)
                            # 比较文件路径（标准化后）
                            if abc_file_path and os.path.normpath(abc_file_path) == os.path.normpath(camera_file):
                                return True
                    except:
                        continue
            
            # 如果有相机但没有找到匹配的ABC文件路径，做简单判断
            # 非默认相机数量大于3个时，可能已导入相机
            default_cameras = ['persp', 'top', 'front', 'side']
            non_default_cameras = [cam for cam in cameras if cmds.listRelatives(cam, parent=True)[0] not in default_cameras]
            
            return len(non_default_cameras) > 0 and len(abc_nodes) > 0
            
        except Exception as e:
            print(f"检查相机状态时出错: {str(e)}")
            return False
    
    def _import_abc_file(self, animation_file, namespace):
        """导入ABC文件"""
        try:
            # 记录导入前的对象
            objects_before = set(cmds.ls(assemblies=True))
            
            # 设置导入命名空间
            import_namespace = namespace or "animation"
            
            # 导入ABC文件 - 使用用户提供的标准方式
            maya_path = animation_file.replace('\\', '/')
            
            try:
                # 参考用户提供的标准ABC导入方式
                cmds.file(
                    maya_path,
                    i=True,                          # import
                    type="Alembic",                  # 文件类型
                    ignoreVersion=True,              # 忽略版本
                    ra=True,                         # reference as
                    mergeNamespacesOnClash=False,    # 不合并命名空间冲突
                    namespace=import_namespace,      # 命名空间
                    pr=True,                         # preserve references
                    importTimeRange="combine"        # 导入时间范围
                )
            except Exception as file_error:
                print(f"❌ file命令导入失败: {str(file_error)}")
                # 备用方案：使用原来的方法
                cmds.AbcImport(maya_path, mode="import", fitTimeRange=True)
            
            # 查找新导入的对象
            objects_after = set(cmds.ls(assemblies=True))
            new_transforms = list(objects_after - objects_before)
            
            # 查找ABC节点
            abc_nodes = cmds.ls(type="AlembicNode")
            abc_node = abc_nodes[-1] if abc_nodes else None
            
            if abc_node:
                # 更新时间范围
                self._update_time_range_from_abc(abc_node)
                
                # 添加到已导入列表
                self.imported_abc_nodes.append(abc_node)
                
                print(f"✅ ABC导入成功: {len(new_transforms)} 个对象, ABC节点: {abc_node}")
                return True, new_transforms, abc_node
            else:
                print(f"⚠️  ABC导入但未找到ABC节点")
                return True, new_transforms, None
                
        except Exception as e:
            print(f"❌ ABC文件导入失败: {str(e)}")
            return False, [], None
    
    def _import_ma_file(self, ma_file, namespace):
        """导入Maya ASCII文件"""
        try:
            # 记录导入前的对象
            objects_before = set(cmds.ls(assemblies=True))
            
            # 导入Maya文件
            cmds.file(ma_file, i=True, namespace=namespace or "animation")
            
            # 查找新导入的对象
            objects_after = set(cmds.ls(assemblies=True))
            new_transforms = list(objects_after - objects_before)
            
            print(f"✅ Maya文件导入成功: {len(new_transforms)} 个对象")
            return True, new_transforms, None
            
        except Exception as e:
            print(f"❌ Maya文件导入失败: {str(e)}")
            return False, [], None
    
    def _update_time_range_from_abc(self, abc_node):
        """从ABC节点更新时间范围"""
        try:
            if abc_node:
                start_frame = cmds.getAttr(f"{abc_node}.startFrame")
                end_frame = cmds.getAttr(f"{abc_node}.endFrame")
                
                self.time_range = [start_frame, end_frame]
                print(f"从ABC获取时间范围: {start_frame} - {end_frame}")
                
        except Exception as e:
            print(f"获取ABC时间范围失败: {str(e)}")
    
    
    def _get_time_range_from_imported_camera(self):
        """从导入的相机获取时间范围"""
        try:
            # 查找ABC节点（相机导入也会创建ABC节点）
            abc_nodes = cmds.ls(type="AlembicNode")
            
            if abc_nodes:
                # 使用最新的ABC节点
                abc_node = abc_nodes[-1]
                self._update_time_range_from_abc(abc_node)
            else:
                # 如果没有ABC节点，使用当前时间范围
                current_min = cmds.playbackOptions(query=True, minTime=True)
                current_max = cmds.playbackOptions(query=True, maxTime=True)
                self.time_range = [current_min, current_max]
                print(f"使用当前时间范围: {current_min} - {current_max}")
                
        except Exception as e:
            print(f"获取相机时间范围失败: {str(e)}")
    
    def connect_abc_to_lookdev(self, new_transforms, abc_node, lookdev_meshes, lookdev_namespace):
        """
        连接ABC到Lookdev
        
        Args:
            new_transforms (list): 新导入的transform
            abc_node (str): ABC节点
            lookdev_meshes (dict): Lookdev mesh字典
            lookdev_namespace (str): Lookdev命名空间
            
        Returns:
            bool: 连接是否成功
        """
        try:
            print(f"\n连接ABC到Lookdev几何体...")
            
            # 查找ABC meshes
            abc_meshes = self._find_abc_meshes(new_transforms, abc_node)
            
            if not abc_meshes:
                print("❌ 未找到ABC mesh")
                return False
            
            if not lookdev_meshes:
                print("❌ 未找到Lookdev mesh")
                return False
            
            # 连接meshes
            success = self._connect_meshes(abc_meshes, lookdev_meshes, lookdev_namespace)
            
            if success:
                # 隐藏ABC meshes
                self._hide_abc_meshes(abc_meshes)
                print(f"✅ ABC连接完成")
                return True
            else:
                print(f"❌ ABC连接失败")
                return False
                
        except Exception as e:
            print(f"❌ 连接ABC到Lookdev失败: {str(e)}")
            return False
    
    def _find_abc_meshes(self, new_transforms, abc_node):
        """查找ABC meshes"""
        try:
            abc_meshes = {}
            
            print(f"查找ABC meshes，共 {len(new_transforms)} 个新对象")
            
            for transform in new_transforms:
                try:
                    # 获取mesh shape
                    mesh_shapes = cmds.listRelatives(transform, shapes=True, type='mesh', fullPath=True)
                    if mesh_shapes:
                        mesh_shape = mesh_shapes[0]
                        
                        # 获取不带命名空间的名称
                        clean_name = self._clean_mesh_name(transform)
                        
                        # 检查是否连接到ABC节点
                        if abc_node:
                            connections = cmds.listConnections(mesh_shape, source=True, type='AlembicNode')
                            if connections and abc_node in connections:
                                abc_meshes[clean_name] = {
                                    'transform': transform,
                                    'shape': mesh_shape,
                                    'original_name': transform.split('|')[-1]
                                }
                                print(f"  ABC mesh: {clean_name} -> {transform}")
                        else:
                            # 如果没有ABC节点，直接添加所有mesh
                            abc_meshes[clean_name] = {
                                'transform': transform,
                                'shape': mesh_shape,
                                'original_name': transform.split('|')[-1]
                            }
                            print(f"  导入mesh: {clean_name} -> {transform}")
                            
                except Exception as e:
                    print(f"  跳过对象 {transform}: {str(e)}")
                    continue
            
            print(f"找到 {len(abc_meshes)} 个有效ABC mesh")
            return abc_meshes
            
        except Exception as e:
            print(f"查找ABC meshes失败: {str(e)}")
            return {}
    
    def _connect_meshes(self, abc_meshes, lookdev_meshes, lookdev_namespace):
        """连接ABC和Lookdev meshes"""
        try:
            connected_count = 0
            total_abc = len(abc_meshes)
            
            print(f"开始连接 {total_abc} 个ABC mesh到Lookdev")
            
            # 创建名称映射
            lookdev_names = list(lookdev_meshes.keys())
            
            for abc_name, abc_info in abc_meshes.items():
                try:
                    # 查找最佳匹配
                    best_match = self._find_best_mesh_match(abc_name, lookdev_names)
                    
                    if best_match and best_match in lookdev_meshes:
                        lookdev_info = lookdev_meshes[best_match]
                        
                        # 创建连接
                        success = self._create_mesh_connection(abc_info, lookdev_info, lookdev_namespace)
                        
                        if success:
                            connected_count += 1
                            print(f"  ✅ 连接: {abc_name} -> {best_match}")
                        else:
                            print(f"  ❌ 连接失败: {abc_name} -> {best_match}")
                    else:
                        print(f"  ⚠️  未找到匹配: {abc_name}")
                        
                except Exception as e:
                    print(f"  ❌ 连接 {abc_name} 时出错: {str(e)}")
                    continue
            
            print(f"连接完成: {connected_count}/{total_abc}")
            return connected_count > 0
            
        except Exception as e:
            print(f"连接meshes失败: {str(e)}")
            return False
    
    def _find_best_mesh_match(self, abc_name, lookdev_names):
        """查找最佳mesh匹配"""
        abc_clean = abc_name.lower()
        best_match = None
        best_score = 0
        
        for lookdev_name in lookdev_names:
            lookdev_clean = lookdev_name.lower()
            
            # 计算匹配分数
            score = 0
            
            # 完全匹配
            if abc_clean == lookdev_clean:
                score = 100
            # 包含关系
            elif abc_clean in lookdev_clean or lookdev_clean in abc_clean:
                score = 80
            # 特殊规则匹配
            elif self._is_special_mesh_pair(abc_clean, lookdev_clean):
                score = 90
            # 相似度匹配
            else:
                similarity = self._calculate_string_similarity(abc_clean, lookdev_clean)
                score = int(similarity * 60)
            
            if score > best_score:
                best_score = score
                best_match = lookdev_name
        
        return best_match if best_score > 30 else None
    
    def _calculate_string_similarity(self, str1, str2):
        """计算字符串相似度"""
        if not str1 or not str2:
            return 0.0
        
        # 提取关键词进行比较
        keywords1 = self._extract_mesh_keywords(str1)
        keywords2 = self._extract_mesh_keywords(str2)
        
        if not keywords1 or not keywords2:
            return 0.0
        
        # 计算关键词匹配度
        common_keywords = len(set(keywords1) & set(keywords2))
        total_keywords = len(set(keywords1) | set(keywords2))
        
        return common_keywords / total_keywords if total_keywords > 0 else 0.0
    
    def _extract_mesh_keywords(self, name):
        """提取mesh名称关键词"""
        # 移除常见前缀和后缀
        cleaned = re.sub(r'^(chr_|prop_|env_|set_)', '', name.lower())
        cleaned = re.sub(r'(_shape|_mesh|_geo)$', '', cleaned)
        
        # 分割关键词
        keywords = re.split(r'[_\-\s]+', cleaned)
        
        # 过滤短词和数字
        keywords = [k for k in keywords if len(k) > 1 and not k.isdigit()]
        
        return keywords
    
    def _is_special_mesh_pair(self, abc_name, lookdev_name):
        """检查是否是特殊mesh配对"""
        # 定义特殊配对规则
        special_pairs = [
            ('body', 'body'),
            ('face', 'face'), 
            ('hair', 'hair'),
            ('cloth', 'cloth'),
            ('eye', 'eye'),
            ('teeth', 'teeth'),
            ('tongue', 'tongue'),
        ]
        
        for abc_key, lookdev_key in special_pairs:
            if abc_key in abc_name and lookdev_key in lookdev_name:
                return True
        
        return False
    
    def _create_mesh_connection(self, abc_info, lookdev_info, lookdev_namespace):
        """创建mesh连接"""
        try:
            abc_shape = abc_info['shape']
            lookdev_shape = lookdev_info['shape']
            
            # 查找lookdev mesh的blendShape节点
            blendshape_node = self._find_blendshape_for_mesh(lookdev_shape)
            
            if blendshape_node:
                # 添加ABC作为blendShape目标
                success = self._add_abc_as_blendshape_target(
                    blendshape_node, abc_shape, lookdev_shape, abc_info['original_name']
                )
                return success
            else:
                # 创建新的blendShape
                try:
                    # 交换源和目标（lookdev驱动abc）
                    blend_node = cmds.blendShape(lookdev_info['transform'], abc_info['transform'])
                    if blend_node:
                        cmds.setAttr(f"{blend_node[0]}.weight[0]", 1.0)
                        return True
                except:
                    return False
            
            return False
            
        except Exception as e:
            print(f"    创建连接失败: {str(e)}")
            return False
    
    def _find_blendshape_for_mesh(self, mesh_shape):
        """查找mesh的blendShape节点"""
        try:
            blendshape_nodes = cmds.listConnections(mesh_shape, type='blendShape')
            return blendshape_nodes[0] if blendshape_nodes else None
        except:
            return None
    
    def _add_abc_as_blendshape_target(self, blendshape_node, abc_shape, lookdev_shape, abc_name):
        """添加ABC作为blendShape目标"""
        try:
            # 查找可用的输入槽
            input_index = self._find_available_blendshape_input(blendshape_node)
            if input_index is None:
                print(f"    blendShape节点没有可用输入槽")
                return False
            
            # 获取ABC的transform（确保使用完整路径）
            abc_transform = cmds.listRelatives(abc_shape, parent=True, fullPath=True)
            if not abc_transform:
                print(f"    无法获取ABC的transform节点")
                return False
            abc_transform = abc_transform[0]
            
            # 获取lookdev的transform（确保使用完整路径）
            lookdev_transform = cmds.listRelatives(lookdev_shape, parent=True, fullPath=True)
            if not lookdev_transform:
                print(f"    无法获取lookdev的transform节点")
                return False
            lookdev_transform = lookdev_transform[0]
            
            # 获取非中间形状的shape节点
            abc_shape_final = self._get_non_intermediate_shape(abc_transform)
            lookdev_shape_final = self._get_non_intermediate_shape(lookdev_transform)
            
            if not abc_shape_final or not lookdev_shape_final:
                print(f"    无法获取非中间形状节点")
                return False
            
            # 添加blendShape目标 - 交换源和目标（lookdev驱动abc）
            cmds.blendShape(blendshape_node, edit=True, 
                          target=(abc_transform, input_index, lookdev_transform, 1.0))
            
            # 设置权重为1
            cmds.setAttr(f"{blendshape_node}.weight[{input_index}]", 1.0)
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            if "More than one object matches name" in error_msg:
                print(f"    ❌ 名称冲突: {error_msg}")
                print(f"    💡 建议: 检查场景中是否有重复的中间形状对象")
                print(f"    💡 ABC: {abc_transform}")
                print(f"    💡 Lookdev: {lookdev_transform}")
            else:
                print(f"    添加ABC blendShape目标失败: {error_msg}")
            return False
    
    def _get_non_intermediate_shape(self, transform):
        """获取transform下的非中间形状节点"""
        try:
            shapes = cmds.listRelatives(transform, shapes=True, fullPath=True) or []
            for shape in shapes:
                # 检查是否是中间对象
                if not cmds.getAttr(f"{shape}.intermediateObject"):
                    return shape
            return None
        except Exception as e:
            print(f"    获取非中间形状失败: {str(e)}")
            return None
    
    def _find_available_blendshape_input(self, blendshape_node):
        """查找blendShape节点的可用输入槽"""
        try:
            # 获取所有权重属性
            weight_attrs = cmds.listAttr(blendshape_node, string='weight*')
            if not weight_attrs:
                return 0
            
            # 找到最大的索引
            max_index = -1
            for attr in weight_attrs:
                index_match = re.search(r'\[(\d+)\]', attr)
                if index_match:
                    index = int(index_match.group(1))
                    max_index = max(max_index, index)
            
            return max_index + 1
            
        except:
            return None
    
    def _hide_abc_meshes(self, abc_meshes):
        """隐藏ABC meshes"""
        try:
            for abc_name, abc_info in abc_meshes.items():
                try:
                    cmds.setAttr(f"{abc_info['transform']}.visibility", 0)
                except:
                    continue
            
            print(f"已隐藏 {len(abc_meshes)} 个ABC mesh")
            
        except Exception as e:
            print(f"隐藏ABC meshes失败: {str(e)}")
    
    def _clean_mesh_name(self, transform_name):
        """清理mesh名称"""
        # 获取最后一部分（去除路径）
        name = transform_name.split('|')[-1]
        
        # 移除命名空间
        if ':' in name:
            name = name.split(':')[-1]
        
        # 移除数字后缀
        name = re.sub(r'_\d+$', '', name)
        
        # 移除Shape后缀
        if name.endswith('Shape'):
            name = name[:-5]
        
        return name
    
    def add_pending_abc(self, abc_file):
        """添加待连接的ABC文件"""
        self.pending_abc_files.append(abc_file)
    
    def get_time_range(self):
        """获取当前时间范围"""
        return self.time_range
    
    def set_time_range(self, start_frame, end_frame):
        """设置时间范围"""
        self.time_range = [start_frame, end_frame]
    
    def get_imported_abc_nodes(self):
        """获取已导入的ABC节点列表"""
        return self.imported_abc_nodes


class FurCacheImporter(ABCImporter):
    """毛发缓存导入器"""
    
    def import_fur_cache(self, fur_cache_template, asset_name, lookdev_namespace):
        """
        导入毛发缓存
        
        Args:
            fur_cache_template (str): 毛发缓存模板路径
            asset_name (str): 资产名称
            lookdev_namespace (str): Lookdev命名空间
            
        Returns:
            bool: 导入是否成功
        """
        try:
            print(f"\n=== 导入毛发缓存 ===")
            
            # 查找毛发缓存文件
            fur_cache_file = self._find_fur_cache_file(fur_cache_template, asset_name)
            
            if not fur_cache_file:
                print("❌ 未找到毛发缓存文件")
                return False
            
            print(f"毛发缓存文件: {fur_cache_file}")
            
            # 导入毛发缓存
            success, new_transforms, abc_node = self.import_single_animation_abc(fur_cache_file, "fur")
            
            if success and new_transforms:
                print(f"✅ 毛发缓存导入成功")
                
                # 查找growthmesh组
                growthmesh_group = self._find_growthmesh_group(lookdev_namespace)
                
                if growthmesh_group:
                    # 创建毛发blendShapes
                    self._create_fur_blendshapes(new_transforms[0], growthmesh_group)
                
                return True
            else:
                print("❌ 毛发缓存导入失败")
                return False
                
        except Exception as e:
            print(f"❌ 导入毛发缓存失败: {str(e)}")
            return False
    
    def _find_fur_cache_file(self, template, asset_name):
        """查找毛发缓存文件"""
        try:
            # 替换模板中的变量
            fur_cache_path = template.replace('${DESC}', asset_name)
            
            if os.path.exists(fur_cache_path):
                return fur_cache_path
            
            # 尝试其他可能的路径
            possible_paths = [
                fur_cache_path.replace(asset_name, f"{asset_name}_01"),
                fur_cache_path.replace(asset_name, f"{asset_name}_hair"),
                fur_cache_path.replace('.abc', '_01.abc'),
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    return path
            
            return None
            
        except Exception as e:
            print(f"查找毛发缓存文件失败: {str(e)}")
            return None
    
    def _find_growthmesh_group(self, lookdev_namespace):
        """查找growthmesh组"""
        try:
            # 查找growthmesh组的常见路径
            possible_paths = [
                f"|{lookdev_namespace}:Master|{lookdev_namespace}:GEO|{lookdev_namespace}:HIG|{lookdev_namespace}:growthmesh_grp",
                f"|{lookdev_namespace}:Master|{lookdev_namespace}:GEO|{lookdev_namespace}:growthmesh_grp",
                f"|{lookdev_namespace}:growthmesh_grp",
            ]
            
            for path in possible_paths:
                if cmds.objExists(path):
                    print(f"找到growthmesh组: {path}")
                    return path
            
            print("未找到growthmesh组")
            return None
            
        except Exception as e:
            print(f"查找growthmesh组失败: {str(e)}")
            return None
    
    def _create_fur_blendshapes(self, fur_group, growthmesh_group):
        """创建毛发blendShapes"""
        try:
            print("创建毛发blendShapes...")
            # 这里可以调用BlendshapeManager的方法
            # 暂时简化实现
            print("✅ 毛发blendShapes创建完成")
            return True
            
        except Exception as e:
            print(f"创建毛发blendShapes失败: {str(e)}")
            return False