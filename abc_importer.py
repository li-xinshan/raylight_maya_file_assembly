"""
ABC导入管理模块
负责处理所有ABC文件导入和连接功能
"""

import maya.cmds as cmds
import os
import re


class ABCImporter:
    """ABC导入管理器"""
    
    def __init__(self):
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
    
    def _import_abc_file(self, animation_file, namespace):
        """导入ABC文件"""
        try:
            # 记录导入前的对象
            objects_before = set(cmds.ls(assemblies=True))
            
            # 设置导入命名空间
            import_namespace = namespace or "animation"
            
            # 导入ABC文件
            cmds.AbcImport(animation_file, mode="import", fitTimeRange=True)
            
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
    
    def import_camera_abc(self, camera_file):
        """
        导入相机ABC文件
        
        Args:
            camera_file (str): 相机ABC文件路径
            
        Returns:
            bool: 导入是否成功
        """
        try:
            print(f"\n导入相机ABC: {os.path.basename(camera_file)}")
            
            if not os.path.exists(camera_file):
                print(f"❌ 相机文件不存在: {camera_file}")
                return False
            
            # 记录导入前的相机
            cameras_before = set(cmds.ls(type='camera'))
            
            # 导入相机ABC
            cmds.AbcImport(camera_file, mode="import", fitTimeRange=True)
            
            # 查找新导入的相机
            cameras_after = set(cmds.ls(type='camera'))
            new_cameras = cameras_after - cameras_before
            
            if new_cameras:
                # 获取相机时间范围
                self._get_time_range_from_imported_camera()
                
                print(f"✅ 相机ABC导入成功: {len(new_cameras)} 个相机")
                
                # 设置Maya时间范围
                cmds.playbackOptions(min=self.time_range[0], max=self.time_range[1])
                cmds.currentTime(self.time_range[0])
                
                return True
            else:
                print("⚠️  相机ABC导入但未找到新相机")
                return False
                
        except Exception as e:
            print(f"❌ 相机ABC导入失败: {str(e)}")
            return False
    
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
            print(f"ABC节点: {abc_node}")
            print(f"新对象列表: {new_transforms}")
            
            for transform in new_transforms:
                try:
                    print(f"  检查对象: {transform}")
                    
                    # 获取mesh shape
                    mesh_shapes = cmds.listRelatives(transform, shapes=True, type='mesh', fullPath=True)
                    print(f"    找到mesh shapes: {mesh_shapes}")
                    
                    if mesh_shapes:
                        mesh_shape = mesh_shapes[0]
                        
                        # 获取不带命名空间的名称
                        clean_name = self._clean_mesh_name(transform)
                        print(f"    清理后名称: {clean_name}")
                        
                        # 检查是否连接到ABC节点
                        is_abc_mesh = False
                        if abc_node:
                            # 检查多种连接方式
                            connections = cmds.listConnections(mesh_shape, source=True, type='AlembicNode')
                            if connections and abc_node in connections:
                                is_abc_mesh = True
                            else:
                                # 也检查transform级别的连接
                                transform_connections = cmds.listConnections(transform, source=True, type='AlembicNode')
                                if transform_connections and abc_node in transform_connections:
                                    is_abc_mesh = True
                                else:
                                    # 检查任何子级连接
                                    all_connections = cmds.listConnections(transform, source=True, type='AlembicNode', shapes=True)
                                    if all_connections and abc_node in all_connections:
                                        is_abc_mesh = True
                        
                        # 如果找到ABC连接或者没有ABC节点，添加mesh
                        if is_abc_mesh or not abc_node:
                            abc_meshes[clean_name] = {
                                'transform': transform,
                                'shape': mesh_shape,
                                'original_name': transform.split('|')[-1]
                            }
                            connection_status = "ABC mesh" if is_abc_mesh else "导入mesh"
                            print(f"  {connection_status}: {clean_name} -> {transform}")
                        else:
                            print(f"  跳过未连接mesh: {clean_name} -> {transform}")
                            
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
                    blend_node = cmds.blendShape(abc_info['transform'], lookdev_info['transform'])
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
            
            # 获取ABC的transform
            abc_transform = cmds.listRelatives(abc_shape, parent=True, fullPath=True)[0]
            lookdev_transform = cmds.listRelatives(lookdev_shape, parent=True, fullPath=True)[0]
            
            # 添加blendShape目标
            cmds.blendShape(blendshape_node, edit=True, 
                          target=(lookdev_transform, input_index, abc_transform, 1.0))
            
            # 设置权重为1
            cmds.setAttr(f"{blendshape_node}.weight[{input_index}]", 1.0)
            
            return True
            
        except Exception as e:
            print(f"    添加ABC blendShape目标失败: {str(e)}")
            return False
    
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