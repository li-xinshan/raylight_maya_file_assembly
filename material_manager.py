"""
材质管理模块
负责处理材质检查、修复和纹理路径管理
"""

import maya.cmds as cmds
import os


class MaterialManager:
    """材质管理器"""
    
    def __init__(self):
        # 常见的纹理路径替换规则
        self.path_replacement_rules = [
            ("P:/LTT", "//192.168.50.250/public/LTT"),
            # 可以添加更多路径替换规则
        ]
    
    def check_and_fix_materials(self):
        """
        检查和修复材质问题
        
        Returns:
            dict: 检查结果统计
        """
        print("\n=== 材质检查和修复 ===")
        
        results = {
            'missing_textures': 0,
            'fixed_textures': 0,
            'unmaterialized_objects': 0
        }
        
        # 检查缺失的纹理
        texture_results = self.fix_missing_textures()
        results['missing_textures'] = texture_results['missing_count']
        results['fixed_textures'] = texture_results['fixed_count']
        
        # 检查没有材质的对象
        unmaterialized_count = self.check_unmaterialized_objects()
        results['unmaterialized_objects'] = unmaterialized_count
        
        print(f"材质检查完成: {results['missing_textures']}个缺失纹理, {results['fixed_textures']}个已修复, {results['unmaterialized_objects']}个无材质对象")
        
        return results
    
    def fix_missing_textures(self):
        """
        修复缺失的纹理路径
        
        Returns:
            dict: 修复结果 {'missing_count': int, 'fixed_count': int}
        """
        print("检查和修复纹理路径...")
        
        file_nodes = cmds.ls(type="file")
        missing_count = 0
        fixed_count = 0
        
        for node in file_nodes:
            try:
                texture_path = cmds.getAttr(f"{node}.fileTextureName")
                if texture_path and not os.path.exists(texture_path):
                    missing_count += 1
                    print(f"  缺失纹理: {os.path.basename(texture_path)}")
                    
                    # 尝试修复路径
                    if self._try_fix_texture_path(node, texture_path):
                        fixed_count += 1
                        
            except Exception as e:
                print(f"  检查纹理节点 {node} 失败: {str(e)}")
        
        if missing_count > 0:
            print(f"纹理修复完成: {missing_count}个缺失, {fixed_count}个已修复")
        else:
            print("所有纹理路径正常")
        
        return {'missing_count': missing_count, 'fixed_count': fixed_count}
    
    def _try_fix_texture_path(self, file_node, original_path):
        """
        尝试修复纹理路径
        
        Args:
            file_node (str): 文件节点名称
            original_path (str): 原始纹理路径
            
        Returns:
            bool: 是否修复成功
        """
        # 生成可能的路径列表
        possible_paths = self._generate_possible_paths(original_path)
        
        for new_path in possible_paths:
            if os.path.exists(new_path):
                try:
                    cmds.setAttr(f"{file_node}.fileTextureName", new_path, type="string")
                    print(f"    ✅ 已修复: {os.path.basename(new_path)}")
                    return True
                except Exception as e:
                    print(f"    修复失败 {new_path}: {str(e)}")
                    continue
        
        return False
    
    def _generate_possible_paths(self, original_path):
        """
        生成可能的纹理路径
        
        Args:
            original_path (str): 原始路径
            
        Returns:
            list: 可能的路径列表
        """
        possible_paths = []
        filename = os.path.basename(original_path)
        
        # 应用路径替换规则
        for old_pattern, new_pattern in self.path_replacement_rules:
            if old_pattern in original_path:
                new_path = original_path.replace(old_pattern, new_pattern)
                possible_paths.append(new_path)
        
        # 尝试项目sourceimages目录
        try:
            project_root = cmds.workspace(query=True, rootDirectory=True)
            sourceimages_path = os.path.join(project_root, "sourceimages", filename)
            possible_paths.append(sourceimages_path)
        except:
            pass
        
        # 尝试相对路径
        try:
            current_scene_dir = os.path.dirname(cmds.file(query=True, sceneName=True))
            relative_path = os.path.join(current_scene_dir, "sourceimages", filename)
            possible_paths.append(relative_path)
        except:
            pass
        
        return possible_paths
    
    def check_unmaterialized_objects(self):
        """
        检查没有材质的对象
        
        Returns:
            int: 无材质对象数量
        """
        print("检查无材质对象...")
        
        all_meshes = cmds.ls(type="mesh", noIntermediate=True)
        no_material = []
        
        for mesh in all_meshes:
            try:
                shading_groups = cmds.listConnections(mesh, type="shadingEngine")
                if not shading_groups or shading_groups[0] == "initialShadingGroup":
                    transform = cmds.listRelatives(mesh, parent=True, type="transform")
                    if transform:
                        no_material.append(transform[0])
            except Exception as e:
                print(f"  检查mesh {mesh} 失败: {str(e)}")
        
        if no_material:
            print(f"⚠️  发现 {len(no_material)} 个无材质对象:")
            # 只显示前10个
            display_count = min(10, len(no_material))
            for obj in no_material[:display_count]:
                print(f"  - {obj}")
            if len(no_material) > display_count:
                print(f"  ... 还有{len(no_material)-display_count}个")
        else:
            print("✅ 所有对象都有材质")
        
        return len(no_material)
    
    def get_material_statistics(self):
        """
        获取材质统计信息
        
        Returns:
            dict: 材质统计信息
        """
        stats = {
            'total_materials': 0,
            'total_shading_groups': 0,
            'total_textures': 0,
            'missing_textures': 0,
            'unmaterialized_meshes': 0
        }
        
        try:
            # 材质统计
            materials = cmds.ls(materials=True)
            # 排除默认材质
            default_materials = ['lambert1', 'particleCloud1', 'shaderGlow1']
            custom_materials = [mat for mat in materials if mat not in default_materials]
            stats['total_materials'] = len(custom_materials)
            
            # 着色组统计
            shading_groups = cmds.ls(type="shadingEngine")
            # 排除默认着色组
            default_sgs = ['initialShadingGroup', 'initialParticleSE']
            custom_sgs = [sg for sg in shading_groups if sg not in default_sgs]
            stats['total_shading_groups'] = len(custom_sgs)
            
            # 纹理统计
            file_nodes = cmds.ls(type="file")
            stats['total_textures'] = len(file_nodes)
            
            missing_count = 0
            for node in file_nodes:
                try:
                    texture_path = cmds.getAttr(f"{node}.fileTextureName")
                    if texture_path and not os.path.exists(texture_path):
                        missing_count += 1
                except:
                    pass
            stats['missing_textures'] = missing_count
            
            # 无材质mesh统计
            stats['unmaterialized_meshes'] = self._count_unmaterialized_meshes()
            
        except Exception as e:
            print(f"获取材质统计信息失败: {str(e)}")
        
        return stats
    
    def _count_unmaterialized_meshes(self):
        """计算无材质mesh数量"""
        all_meshes = cmds.ls(type="mesh", noIntermediate=True)
        count = 0
        
        for mesh in all_meshes:
            try:
                shading_groups = cmds.listConnections(mesh, type="shadingEngine")
                if not shading_groups or shading_groups[0] == "initialShadingGroup":
                    count += 1
            except:
                pass
        
        return count
    
    def print_material_statistics(self):
        """打印材质统计信息"""
        print("\n=== 材质统计信息 ===")
        stats = self.get_material_statistics()
        
        print(f"自定义材质数量: {stats['total_materials']}")
        print(f"自定义着色组数量: {stats['total_shading_groups']}")
        print(f"纹理节点数量: {stats['total_textures']}")
        print(f"缺失纹理数量: {stats['missing_textures']}")
        print(f"无材质对象数量: {stats['unmaterialized_meshes']}")
        
        return stats