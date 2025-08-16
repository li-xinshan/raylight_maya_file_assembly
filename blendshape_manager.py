"""
BlendShape管理模块
负责处理所有BlendShape相关的功能
"""

import maya.cmds as cmds
import re


class BlendshapeManager:
    """BlendShape管理器"""
    
    def __init__(self):
        self.blendshape_cache = {}  # 缓存已创建的BlendShape节点
    
    def create_dynamic_blendshapes(self, source_objects, target_objects, conflict_check=True):
        """
        创建动态BlendShape连接
        
        Args:
            source_objects (list): 源对象列表（组或单个mesh）
            target_objects (list): 目标对象列表（组或单个mesh）
            conflict_check (bool): 是否检查动画BlendShape冲突
            
        Returns:
            dict: 匹配结果统计
        """
        try:
            print(f"\n=== 创建动态BlendShape连接 ===")
            print(f"源对象数量: {len(source_objects)}")
            print(f"目标对象数量: {len(target_objects)}")
            
            # 获取所有源mesh
            source_meshes = self._extract_meshes_from_objects(source_objects, "源")
            
            # 获取所有目标mesh
            target_meshes = self._extract_meshes_from_objects(target_objects, "目标")
            
            if not source_meshes or not target_meshes:
                print("❌ 没有找到有效的mesh")
                return {'success': 0, 'failed': 0, 'skipped': 0}
            
            # 执行智能匹配
            return self._perform_smart_blendshape_matching(source_meshes, target_meshes, conflict_check)
            
        except Exception as e:
            print(f"❌ 创建动态BlendShape失败: {str(e)}")
            return {'success': 0, 'failed': 0, 'skipped': 0}
    
    def _extract_meshes_from_objects(self, objects, label):
        """从对象列表中提取所有mesh信息"""
        mesh_info = {}
        
        print(f"分析{label}对象:")
        for obj in objects:
            if not cmds.objExists(obj):
                print(f"  ⚠️  对象不存在: {obj}")
                continue
            
            # 检查对象类型
            if cmds.nodeType(obj) == 'transform':
                # 检查是否有mesh子节点
                mesh_shapes = cmds.listRelatives(obj, shapes=True, type='mesh')
                if mesh_shapes:
                    # 单个mesh transform
                    mesh_shape = mesh_shapes[0]
                    face_count = cmds.polyEvaluate(mesh_shape, face=True)
                    clean_name = self._clean_mesh_name(obj.split('|')[-1])
                    
                    mesh_info[obj] = {
                        'shape': mesh_shape,
                        'face_count': face_count,
                        'clean_name': clean_name,
                        'original_name': obj.split('|')[-1]
                    }
                    print(f"  📦 Mesh: {obj.split('|')[-1]} - {face_count} 面 ({clean_name})")
                else:
                    # 组 - 获取所有子mesh
                    child_meshes = cmds.listRelatives(obj, allDescendents=True, type='mesh', fullPath=True) or []
                    print(f"  📁 组: {obj.split('|')[-1]} - 找到 {len(child_meshes)} 个子mesh")
                    
                    for mesh_shape in child_meshes:
                        # 获取mesh的transform
                        mesh_transform = cmds.listRelatives(mesh_shape, parent=True, fullPath=True)[0]
                        try:
                            face_count = cmds.polyEvaluate(mesh_shape, face=True)
                            clean_name = self._clean_mesh_name(mesh_transform.split('|')[-1])
                            
                            mesh_info[mesh_transform] = {
                                'shape': mesh_shape,
                                'face_count': face_count,
                                'clean_name': clean_name,
                                'original_name': mesh_transform.split('|')[-1]
                            }
                            print(f"    - {mesh_transform.split('|')[-1]} - {face_count} 面 ({clean_name})")
                        except:
                            print(f"    ❌ 无法分析mesh: {mesh_shape}")
                            continue
            elif cmds.nodeType(obj) == 'mesh':
                # 直接是mesh shape
                mesh_transform = cmds.listRelatives(obj, parent=True, fullPath=True)[0]
                try:
                    face_count = cmds.polyEvaluate(obj, face=True)
                    clean_name = self._clean_mesh_name(mesh_transform.split('|')[-1])
                    
                    mesh_info[mesh_transform] = {
                        'shape': obj,
                        'face_count': face_count,
                        'clean_name': clean_name,
                        'original_name': mesh_transform.split('|')[-1]
                    }
                    print(f"  📦 Mesh Shape: {mesh_transform.split('|')[-1]} - {face_count} 面 ({clean_name})")
                except:
                    print(f"  ❌ 无法分析mesh shape: {obj}")
                    continue
        
        return mesh_info
    
    def _perform_smart_blendshape_matching(self, source_meshes, target_meshes, conflict_check):
        """执行智能blendShape匹配"""
        results = {'success': 0, 'failed': 0, 'skipped': 0}
        matched_pairs = []
        
        print(f"\n开始智能匹配 ({len(source_meshes)} 源 -> {len(target_meshes)} 目标)")
        
        # 为每个源mesh找到最佳目标mesh
        for source_transform, source_info in source_meshes.items():
            best_match = None
            best_score = 0
            
            for target_transform, target_info in target_meshes.items():
                # 如果目标已经被匹配过，跳过
                if any(pair[1] == target_transform for pair in matched_pairs):
                    continue
                
                # 计算匹配分数
                score = self._calculate_mesh_match_score(source_info, target_info)
                
                if score > best_score:
                    best_score = score
                    best_match = target_transform
            
            if best_match and best_score >= 10:  # 至少面数要匹配(10分)
                matched_pairs.append((source_transform, best_match))
                target_info = target_meshes[best_match]
                
                print(f"✅ 匹配: {source_info['original_name']} -> {target_info['original_name']} (分数:{best_score})")
                
                # 检查冲突
                if conflict_check and self._has_animation_blendshape_conflict(target_info['shape']):
                    print(f"  ⚠️  跳过 - 目标mesh已有动画blendShape连接")
                    results['skipped'] += 1
                    continue
                
                # 创建blendShape
                if self._create_single_blendshape_connection(source_info, target_info):
                    results['success'] += 1
                else:
                    results['failed'] += 1
            else:
                print(f"❌ 未匹配: {source_info['original_name']} (最高分数:{best_score})")
        
        # 报告未匹配的mesh
        unmatched_sources = [info['original_name'] for transform, info in source_meshes.items() 
                           if not any(pair[0] == transform for pair in matched_pairs)]
        unmatched_targets = [info['original_name'] for transform, info in target_meshes.items() 
                           if not any(pair[1] == transform for pair in matched_pairs)]
        
        if unmatched_sources:
            print(f"\n⚠️  未匹配的源mesh: {', '.join(unmatched_sources)}")
        if unmatched_targets:
            print(f"⚠️  未匹配的目标mesh: {', '.join(unmatched_targets)}")
        
        print(f"\n📊 匹配结果: 成功{results['success']}, 失败{results['failed']}, 跳过{results['skipped']}")
        return results
    
    def _calculate_mesh_match_score(self, source_info, target_info):
        """计算mesh匹配分数"""
        score = 0
        
        # 1. 面数匹配 (必须条件)
        if source_info['face_count'] == target_info['face_count']:
            score += 10
        else:
            return 0  # 面数不匹配直接返回0
        
        # 2. 名称匹配
        source_clean = source_info['clean_name'].lower()
        target_clean = target_info['clean_name'].lower()
        
        # 完全匹配
        if source_clean == target_clean:
            score += 50
        # 包含关系
        elif source_clean in target_clean or target_clean in source_clean:
            score += 30
        # 相似度匹配
        else:
            similarity = self._calculate_string_similarity(source_clean, target_clean)
            score += int(similarity * 20)
        
        # 3. 特殊命名规则加分
        if self._is_special_mesh_pair(source_info['original_name'], target_info['original_name']):
            score += 25
        
        return score
    
    def _calculate_string_similarity(self, str1, str2):
        """计算字符串相似度"""
        if not str1 or not str2:
            return 0.0
        
        # 简单的相似度算法
        common_chars = sum(1 for c in str1 if c in str2)
        max_len = max(len(str1), len(str2))
        
        return common_chars / max_len if max_len > 0 else 0.0
    
    def _is_special_mesh_pair(self, abc_name, lookdev_name):
        """检查是否是特殊的mesh配对"""
        abc_clean = abc_name.lower()
        lookdev_clean = lookdev_name.lower()
        
        # 定义特殊配对规则
        special_pairs = [
            ('body', 'body'),
            ('face', 'face'),
            ('hair', 'hair'),
            ('cloth', 'cloth'),
            ('eye', 'eye'),
        ]
        
        for abc_key, lookdev_key in special_pairs:
            if abc_key in abc_clean and lookdev_key in lookdev_clean:
                return True
        
        return False
    
    def _clean_mesh_name(self, name):
        """清理mesh名称，移除命名空间和数字后缀"""
        # 移除命名空间
        if ':' in name:
            name = name.split(':')[-1]
        
        # 移除数字后缀 (_01, _02等)
        name = re.sub(r'_\d+$', '', name)
        
        # 移除Shape后缀
        if name.endswith('Shape'):
            name = name[:-5]
        
        return name
    
    def _has_animation_blendshape_conflict(self, target_shape):
        """检查目标mesh是否已有动画blendShape连接"""
        try:
            # 查找连接到此mesh的blendShape节点
            blendshape_nodes = cmds.listConnections(target_shape, type='blendShape')
            if not blendshape_nodes:
                return False
            
            # 检查blendShape节点的权重是否有动画
            for node in blendshape_nodes:
                weight_attrs = cmds.listAttr(node, string='weight*')
                if weight_attrs:
                    for attr in weight_attrs:
                        full_attr = f"{node}.{attr}"
                        # 检查是否有动画曲线连接
                        if cmds.listConnections(full_attr, type='animCurve'):
                            print(f"    发现动画blendShape: {node}.{attr}")
                            return True
            
            return False
            
        except Exception as e:
            print(f"    检查动画blendShape冲突失败: {str(e)}")
            return False
    
    def _create_single_blendshape_connection(self, source_info, target_info):
        """创建单个BlendShape连接"""
        try:
            # 使用安全的BlendShape创建方法
            blend_node = self._create_safe_blendshape(source_info['shape'], target_info['shape'])
            
            if blend_node:
                print(f"  ✅ 创建BlendShape: {source_info['original_name']} -> {target_info['original_name']}")
                return True
            else:
                print(f"  ❌ 创建BlendShape失败: {source_info['original_name']} -> {target_info['original_name']}")
                return False
                
        except Exception as e:
            print(f"  ❌ 创建BlendShape异常: {str(e)}")
            return False
    
    def _create_safe_blendshape(self, source_mesh, target_mesh):
        """安全创建blendShape，避免循环依赖和重复连接"""
        try:
            # 获取target mesh的shape节点
            if cmds.nodeType(target_mesh) == 'transform':
                target_shapes = cmds.listRelatives(target_mesh, shapes=True, type='mesh')
                if not target_shapes:
                    print(f"    目标mesh没有shape节点: {target_mesh}")
                    return None
                target_shape = target_shapes[0]
            else:
                target_shape = target_mesh
            
            # 获取source mesh的shape节点
            if cmds.nodeType(source_mesh) == 'transform':
                source_shapes = cmds.listRelatives(source_mesh, shapes=True, type='mesh')
                if not source_shapes:
                    print(f"    源mesh没有shape节点: {source_mesh}")
                    return None
                source_shape = source_shapes[0]
            else:
                source_shape = source_mesh
            
            # 检查是否会创建循环依赖
            if self._would_create_cycle(source_shape, target_shape):
                print(f"    ⚠️  检测到潜在循环依赖，跳过创建blendShape")
                return None
            
            # 检查是否已有blendShape
            existing_blendshape = self._find_blendshape_for_mesh(target_shape)
            
            if existing_blendshape:
                print(f"    发现现有blendShape: {existing_blendshape}")
                # 检查source是否已经是此blendShape的目标
                if self._is_already_blendshape_target(existing_blendshape, source_shape):
                    print(f"    源mesh已经是此blendShape的目标，跳过")
                    return existing_blendshape
                
                # 添加新的target到现有blendShape
                if self._add_mesh_to_existing_blendshape(existing_blendshape, source_mesh, target_mesh):
                    return existing_blendshape
                else:
                    return None
            else:
                # 如果没有blendShape，创建新的（使用duplicated source避免循环）
                try:
                    # 创建源mesh的副本以避免循环依赖
                    temp_source = cmds.duplicate(source_mesh, name=f"temp_blend_source")[0]
                    
                    # 创建blendShape
                    blend_node = cmds.blendShape(temp_source, target_mesh, name=f"blendShape_{target_shape}")
                    
                    # 设置权重为1
                    if blend_node:
                        cmds.setAttr(f"{blend_node[0]}.weight[0]", 1.0)
                        print(f"    创建新blendShape: {blend_node[0]}")
                        
                        # 删除临时源mesh
                        cmds.delete(temp_source)
                        
                        return blend_node[0]
                    else:
                        # 如果创建失败，清理临时mesh
                        cmds.delete(temp_source)
                        return None
                        
                except Exception as e:
                    print(f"    创建新blendShape失败: {str(e)}")
                    return None
                    
        except Exception as e:
            print(f"    安全创建blendShape失败: {str(e)}")
            return None
    
    def _would_create_cycle(self, source_shape, target_shape):
        """检查是否会创建循环依赖"""
        try:
            # 检查target是否依赖于source
            return self._is_mesh_dependent_on(target_shape, source_shape)
        except:
            # 如果检查失败，保守起见返回True
            return True
    
    def _is_mesh_dependent_on(self, mesh1, mesh2):
        """检查mesh1是否依赖于mesh2"""
        try:
            # 获取mesh1的所有输入连接
            connections = cmds.listConnections(mesh1, source=True, destination=False)
            if not connections:
                return False
            
            # 检查直接连接
            if mesh2 in connections:
                return True
            
            # 递归检查间接连接（限制深度避免无限递归）
            return self._check_dependency_recursive(connections, mesh2, depth=0, max_depth=5)
            
        except:
            return False
    
    def _check_dependency_recursive(self, connections, target_mesh, depth, max_depth):
        """递归检查依赖关系"""
        if depth >= max_depth:
            return False
        
        for connection in connections:
            try:
                if connection == target_mesh:
                    return True
                
                # 获取下一级连接
                next_connections = cmds.listConnections(connection, source=True, destination=False)
                if next_connections:
                    if self._check_dependency_recursive(next_connections, target_mesh, depth + 1, max_depth):
                        return True
            except:
                continue
        
        return False
    
    def _find_blendshape_for_mesh(self, mesh_shape):
        """查找mesh的blendShape节点"""
        try:
            # 查找连接到mesh的blendShape节点
            blendshape_nodes = cmds.listConnections(mesh_shape, type='blendShape')
            if blendshape_nodes:
                return blendshape_nodes[0]
            return None
        except:
            return None
    
    def _is_already_blendshape_target(self, blendshape_node, source_shape):
        """检查source是否已经是blendShape的目标"""
        try:
            # 获取blendShape的所有输入target
            targets = cmds.blendShape(blendshape_node, query=True, target=True)
            if targets:
                # 获取source的transform
                source_transform = cmds.listRelatives(source_shape, parent=True)[0]
                return source_transform in targets
            return False
        except:
            return False
    
    def _add_mesh_to_existing_blendshape(self, blendshape_node, source_mesh, target_mesh):
        """将mesh添加到现有的blendShape节点"""
        try:
            # 找到可用的输入槽
            input_index = self._find_available_blendshape_input(blendshape_node)
            if input_index is None:
                print(f"      blendShape节点没有可用输入槽")
                return False
            
            # 添加新的blendShape target
            cmds.blendShape(blendshape_node, edit=True, target=(target_mesh, input_index, source_mesh, 1.0))
            # 设置权重为1
            cmds.setAttr(f"{blendshape_node}.weight[{input_index}]", 1.0)
            
            return True
            
        except Exception as e:
            print(f"      添加到现有blendShape失败: {str(e)}")
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


class ClothBlendshapeManager(BlendshapeManager):
    """布料BlendShape专用管理器"""
    
    def create_cloth_blendshapes(self, cloth_group, clothes_group):
        """为cloth和clothes创建blendShape连接"""
        try:
            print("\n创建cloth到clothes的blendShape连接...")
            
            # 获取cloth组下所有mesh（排除中间形状）
            print(f"检查cloth组结构: {cloth_group}")
            cloth_meshes = cmds.listRelatives(cloth_group, allDescendents=True, type='mesh', fullPath=True, noIntermediate=True) or []
            print(f"Cloth组中找到 {len(cloth_meshes)} 个mesh")
            
            # 显示前5个cloth mesh作为调试
            for i, mesh in enumerate(cloth_meshes[:5]):
                mesh_name = mesh.split('|')[-1]
                print(f"  Cloth mesh {i+1}: {mesh_name}")
            if len(cloth_meshes) > 5:
                print(f"  ... 还有 {len(cloth_meshes) - 5} 个cloth mesh")
            
            # 获取clothes组下所有mesh（排除中间形状）
            print(f"检查clothes组结构: {clothes_group}")
            
            clothes_meshes = cmds.listRelatives(clothes_group, allDescendents=True, type='mesh', fullPath=True, noIntermediate=True) or []
            print(f"Clothes组中找到 {len(clothes_meshes)} 个mesh")
            
            # 如果没有找到mesh，尝试包含中间形状
            if not clothes_meshes:
                print("未找到非中间形状的mesh，尝试包含中间形状...")
                clothes_meshes_with_intermediate = cmds.listRelatives(clothes_group, allDescendents=True, type='mesh', fullPath=True) or []
                print(f"包含中间形状的mesh数量: {len(clothes_meshes_with_intermediate)}")
                
                # 使用非中间形状的mesh
                clothes_meshes = [mesh for mesh in clothes_meshes_with_intermediate 
                                if not cmds.getAttr(mesh + '.intermediateObject', silent=True)]
                print(f"过滤后的Clothes组mesh数量: {len(clothes_meshes)}")
            
            if not cloth_meshes or not clothes_meshes:
                print("❌ 没有找到足够的mesh进行连接")
                return False
            
            # 创建mesh信息字典
            cloth_mesh_info = self._create_mesh_info_dict(cloth_meshes, "Cloth")
            clothes_mesh_info = self._create_mesh_info_dict(clothes_meshes, "Clothes")
            
            # 执行匹配和连接
            created_count = 0
            matched_clothes = set()
            
            # 第一轮：精确名称匹配
            print("\n第一轮：精确名称匹配...")
            for mesh_name, cloth_info in cloth_mesh_info.items():
                if mesh_name in clothes_mesh_info and mesh_name not in matched_clothes:
                    clothes_info = clothes_mesh_info[mesh_name]
                    
                    # 检查面数是否匹配
                    if cloth_info['face_count'] != clothes_info['face_count']:
                        print(f"  ⚠️  {cloth_info['original_name']}: 面数不匹配 (cloth: {cloth_info['face_count']}, clothes: {clothes_info['face_count']})")
                        continue
                    
                    try:
                        # 使用transform节点创建blendShape（cloth驱动clothes）
                        blend_node = self._create_safe_blendshape(cloth_info['transform'], clothes_info['transform'])
                        if blend_node:
                            print(f"  ✅ 创建blendShape: {cloth_info['original_name']} -> {clothes_info['original_name']}")
                            created_count += 1
                            matched_clothes.add(mesh_name)
                        else:
                            print(f"  ❌ 创建blendShape失败: {cloth_info['original_name']}")
                        
                    except Exception as e:
                        print(f"  ❌ 创建blendShape失败 {cloth_info['original_name']}: {str(e)}")
            
            # 第二轮：基于面数的模糊匹配（用于未匹配的mesh）
            print("\n第二轮：基于面数的模糊匹配...")
            unmatched_cloth = [info for name, info in cloth_mesh_info.items() if name not in matched_clothes]
            unmatched_clothes = [info for name, info in clothes_mesh_info.items() if name not in matched_clothes]
            
            for cloth_info in unmatched_cloth:
                best_match = None
                best_score = 0
                
                for clothes_info in unmatched_clothes:
                    # 计算匹配分数
                    score = 0
                    
                    # 面数必须完全匹配
                    if cloth_info['face_count'] == clothes_info['face_count'] and cloth_info['face_count'] > 0:
                        score += 100
                        
                        # 名称相似度加分
                        cloth_name = cloth_info['original_name'].lower()
                        clothes_name = clothes_info['original_name'].lower()
                        
                        # 计算共同字符
                        common_chars = sum(1 for c in cloth_name if c in clothes_name)
                        score += common_chars * 5
                        
                        if score > best_score:
                            best_score = score
                            best_match = clothes_info
                
                if best_match and best_score >= 100:  # 至少面数要匹配
                    try:
                        blend_node = self._create_safe_blendshape(cloth_info['transform'], best_match['transform'])
                        if blend_node:
                            print(f"  ✅ 模糊匹配创建blendShape: {cloth_info['original_name']} -> {best_match['original_name']} (分数:{best_score})")
                            created_count += 1
                            unmatched_clothes.remove(best_match)
                        else:
                            print(f"  ❌ 模糊匹配失败: {cloth_info['original_name']} -> {best_match['original_name']}")
                    except Exception as e:
                        print(f"  ❌ 模糊匹配异常: {str(e)}")
            
            if created_count > 0:
                print(f"\n✅ 布料blendShape创建完成，共创建 {created_count} 个连接")
                return True
            else:
                print(f"\n❌ 没有创建任何布料blendShape连接")
                return False
                
        except Exception as e:
            print(f"❌ 创建布料blendShape失败: {str(e)}")
            return False
    
    def _create_mesh_info_dict(self, meshes, label):
        """创建mesh信息字典"""
        mesh_info = {}
        
        for mesh in meshes:
            # 获取transform节点
            transform = cmds.listRelatives(mesh, parent=True, fullPath=True)[0]
            # 获取不带命名空间的名称
            mesh_name = transform.split('|')[-1]
            if ':' in mesh_name:
                mesh_name = mesh_name.split(':')[-1]
            
            # 获取面数
            try:
                face_count = cmds.polyEvaluate(mesh, face=True)
            except:
                face_count = 0
            
            mesh_info[mesh_name.lower()] = {
                'mesh': mesh,
                'transform': transform,
                'face_count': face_count,
                'original_name': mesh_name
            }
            print(f"  {label} mesh: {mesh_name} (面数: {face_count})")
        
        return mesh_info