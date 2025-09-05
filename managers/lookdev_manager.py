"""
Lookdev管理模块
负责处理Lookdev文件导入和相关管理功能
"""

import maya.cmds as cmds
import os


class LookdevManager:
    """Lookdev管理器"""
    
    def __init__(self):
        self.current_lookdev_file = None
        self.lookdev_namespace = "asset_lookdev"
        self.imported_lookdev_nodes = []
    
    def import_lookdev_file(self, lookdev_file, namespace=None):
        """
        导入Lookdev文件
        
        Args:
            lookdev_file (str): Lookdev文件路径
            namespace (str): 命名空间
            
        Returns:
            bool: 是否导入成功
        """
        if namespace is None:
            namespace = self.lookdev_namespace
        
        print(f"\n=== 导入Lookdev文件 ===")
        print(f"文件: {lookdev_file}")
        print(f"命名空间: {namespace}")
        
        try:
            # 检查文件是否存在
            if not os.path.exists(lookdev_file):
                print(f"❌ Lookdev文件不存在: {lookdev_file}")
                return False
            
            # 记录导入前的节点
            transforms_before = set(cmds.ls(type="transform"))
            
            # 导入文件
            cmds.file(
                lookdev_file,
                r=True,  # Reference
                type="mayaAscii",
                ignoreVersion=True,
                prompt=False,
                mergeNamespacesOnClash=False,
                namespace=namespace,
                loadReferenceDepth="all",  # 加载所有引用层级
                returnNewNodes=True  # 返回新节点
            )
            
            # 记录导入的节点
            transforms_after = set(cmds.ls(type="transform"))
            new_transforms = transforms_after - transforms_before
            self.imported_lookdev_nodes = list(new_transforms)
            
            self.current_lookdev_file = lookdev_file
            self.lookdev_namespace = namespace
            
            print(f"✅ Lookdev文件导入成功")
            return True
            
        except Exception as e:
            print(f"❌ 导入Lookdev文件失败: {str(e)}")
            return False
    
    def get_lookdev_meshes(self, namespace=None):
        """
        获取Lookdev几何体信息
        
        Args:
            namespace (str): 命名空间
            
        Returns:
            dict: 几何体信息字典 {name: {'transform': str, 'shape': str}}
        """
        if namespace is None:
            namespace = self.lookdev_namespace
        
        lookdev_meshes = {}
        
        try:
            # 查找命名空间下的所有transform
            lookdev_transforms = cmds.ls(f"{namespace}:*", type='transform') or []
            
            for transform in lookdev_transforms:
                # 获取mesh shape
                shapes = cmds.listRelatives(transform, shapes=True, type='mesh') or []
                if shapes:
                    # 使用transform的基础名称作为key
                    base_name = transform.split(':')[-1].lower()
                    lookdev_meshes[base_name] = {
                        'transform': transform,
                        'shape': shapes[0]
                    }
            
            print(f"找到 {len(lookdev_meshes)} 个Lookdev几何体")
            return lookdev_meshes
            
        except Exception as e:
            print(f"❌ 获取Lookdev几何体失败: {str(e)}")
            return {}
    
    def get_lookdev_statistics(self):
        """
        获取Lookdev统计信息
        
        Returns:
            dict: 统计信息
        """
        stats = {
            'lookdev_file': self.current_lookdev_file,
            'namespace': self.lookdev_namespace,
            'total_nodes': len(self.imported_lookdev_nodes),
            'mesh_count': 0,
            'material_count': 0,
            'texture_count': 0
        }
        
        try:
            if self.lookdev_namespace:
                # 统计mesh
                meshes = self.get_lookdev_meshes()
                stats['mesh_count'] = len(meshes)
                
                # 统计材质
                materials = cmds.ls(f"{self.lookdev_namespace}:*", materials=True) or []
                stats['material_count'] = len(materials)
                
                # 统计纹理
                textures = cmds.ls(f"{self.lookdev_namespace}:*", type="file") or []
                stats['texture_count'] = len(textures)
            
        except Exception as e:
            print(f"获取Lookdev统计信息失败: {str(e)}")
        
        return stats
    
    def print_lookdev_info(self):
        """打印Lookdev信息"""
        print("\n=== Lookdev信息 ===")
        stats = self.get_lookdev_statistics()
        
        if stats['lookdev_file']:
            print(f"Lookdev文件: {os.path.basename(stats['lookdev_file'])}")
        else:
            print("Lookdev文件: 未加载")
        
        print(f"命名空间: {stats['namespace']}")
        print(f"总节点数: {stats['total_nodes']}")
        print(f"几何体数: {stats['mesh_count']}")
        print(f"材质数: {stats['material_count']}")
        print(f"纹理数: {stats['texture_count']}")
    
    def validate_lookdev(self):
        """
        验证Lookdev文件的完整性
        
        Returns:
            dict: 验证结果
        """
        validation = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'mesh_count': 0,
            'material_count': 0
        }
        
        try:
            # 检查是否有Lookdev文件
            if not self.current_lookdev_file:
                validation['valid'] = False
                validation['errors'].append("没有加载Lookdev文件")
                return validation
            
            # 检查命名空间是否存在
            if not cmds.namespace(exists=self.lookdev_namespace):
                validation['valid'] = False
                validation['errors'].append(f"命名空间不存在: {self.lookdev_namespace}")
                return validation
            
            # 检查几何体
            meshes = self.get_lookdev_meshes()
            validation['mesh_count'] = len(meshes)
            
            if validation['mesh_count'] == 0:
                validation['warnings'].append("没有找到几何体")
            
            # 检查材质
            materials = cmds.ls(f"{self.lookdev_namespace}:*", materials=True) or []
            validation['material_count'] = len(materials)
            
            if validation['material_count'] == 0:
                validation['warnings'].append("没有找到材质")
            
            # 检查是否有未分配材质的几何体
            unmaterialized_count = 0
            for mesh_name, mesh_data in meshes.items():
                shape = mesh_data['shape']
                shading_groups = cmds.listConnections(shape, type="shadingEngine") or []
                if not shading_groups or shading_groups[0] == "initialShadingGroup":
                    unmaterialized_count += 1
            
            if unmaterialized_count > 0:
                validation['warnings'].append(f"{unmaterialized_count} 个几何体没有材质")
            
        except Exception as e:
            validation['valid'] = False
            validation['errors'].append(f"验证过程出错: {str(e)}")
        
        return validation
    
    def cleanup_lookdev(self):
        """清理Lookdev相关内容"""
        try:
            if self.lookdev_namespace and cmds.namespace(exists=self.lookdev_namespace):
                # 删除命名空间及其内容
                cmds.namespace(removeNamespace=self.lookdev_namespace, deleteNamespaceContent=True)
                print(f"已清理Lookdev命名空间: {self.lookdev_namespace}")
            
            self.current_lookdev_file = None
            self.imported_lookdev_nodes.clear()
            
        except Exception as e:
            print(f"清理Lookdev失败: {str(e)}")
    
    def get_master_node(self):
        """
        获取Lookdev的主节点
        
        Returns:
            str: 主节点名称，如果存在的话
        """
        possible_names = ["Master", "master", "root", "Root"]
        
        for name in possible_names:
            full_name = f"{self.lookdev_namespace}:{name}"
            if cmds.objExists(full_name):
                return full_name
        
        # 如果没有找到标准名称，查找顶层组
        try:
            transforms = cmds.ls(f"{self.lookdev_namespace}:*", type="transform") or []
            top_level_nodes = []
            
            for transform in transforms:
                parents = cmds.listRelatives(transform, parent=True)
                if not parents or not parents[0].startswith(self.lookdev_namespace):
                    top_level_nodes.append(transform)
            
            if top_level_nodes:
                return top_level_nodes[0]  # 返回第一个顶层节点
                
        except Exception as e:
            print(f"查找主节点失败: {str(e)}")
        
        return None
    
    def set_namespace(self, namespace):
        """设置命名空间"""
        self.lookdev_namespace = namespace
    
    def get_namespace(self):
        """获取当前命名空间"""
        return self.lookdev_namespace