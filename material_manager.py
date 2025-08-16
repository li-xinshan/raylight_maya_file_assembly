"""
材质管理模块
负责处理所有材质和纹理相关的功能
"""

import maya.cmds as cmds
import os


class MaterialManager:
    """材质管理器"""
    
    def __init__(self):
        self.checked_materials = set()
        self.fixed_textures = []
        self.missing_textures = []
    
    def check_and_fix_materials(self):
        """
        检查和修复材质
        
        Returns:
            bool: 修复是否成功
        """
        try:
            print("\n=== 检查和修复材质 ===")
            
            # 检查未材质化的对象
            self._check_unmaterialized_objects()
            
            # 修复缺失的纹理
            self._fix_missing_textures()
            
            # 检查材质节点完整性
            self._check_material_node_integrity()
            
            print("✅ 材质检查修复完成")
            return True
            
        except Exception as e:
            print(f"❌ 材质修复失败: {str(e)}")
            return False
    
    def _check_unmaterialized_objects(self):
        """检查没有材质的对象"""
        try:
            print("\n检查未材质化对象...")
            
            all_meshes = cmds.ls(type="mesh", noIntermediate=True)
            no_material = []
            
            for mesh in all_meshes:
                try:
                    # 获取连接的着色组
                    shading_groups = cmds.listConnections(mesh, type="shadingEngine")
                    
                    if not shading_groups or shading_groups[0] == "initialShadingGroup":
                        # 获取transform节点
                        transform = cmds.listRelatives(mesh, parent=True, type="transform")
                        if transform:
                            no_material.append(transform[0])
                            
                except Exception as e:
                    print(f"  检查mesh材质失败 {mesh}: {str(e)}")
                    continue
            
            if no_material:
                print(f"⚠️  发现 {len(no_material)} 个对象没有材质:")
                for i, obj in enumerate(no_material[:10]):  # 只显示前10个
                    print(f"  {i+1}. {obj}")
                if len(no_material) > 10:
                    print(f"  ... 还有 {len(no_material) - 10} 个对象")
            else:
                print("✅ 所有对象都有材质分配")
                
        except Exception as e:
            print(f"检查未材质化对象失败: {str(e)}")
    
    def _fix_missing_textures(self):
        """修复缺失的纹理"""
        try:
            print("\n检查和修复纹理路径...")
            
            file_nodes = cmds.ls(type="file")
            missing_count = 0
            fixed_count = 0
            
            for node in file_nodes:
                try:
                    # 获取纹理路径
                    texture_path = cmds.getAttr(f"{node}.fileTextureName")
                    
                    if texture_path and not os.path.exists(texture_path):
                        missing_count += 1
                        texture_name = os.path.basename(texture_path)
                        print(f"  ❌ 缺失纹理: {texture_name}")
                        self.missing_textures.append(texture_path)
                        
                        # 尝试修复路径
                        fixed_path = self._try_fix_texture_path(texture_path)
                        
                        if fixed_path:
                            cmds.setAttr(f"{node}.fileTextureName", fixed_path, type="string")
                            fixed_count += 1
                            self.fixed_textures.append(fixed_path)
                            print(f"    ✅ 已修复: {os.path.basename(fixed_path)}")
                            
                except Exception as e:
                    print(f"  检查纹理节点失败 {node}: {str(e)}")
                    continue
            
            if missing_count > 0:
                print(f"\n纹理状态总结: {missing_count} 个缺失, {fixed_count} 个已修复")
            else:
                print("✅ 所有纹理路径都有效")
                
        except Exception as e:
            print(f"修复纹理失败: {str(e)}")
    
    def _try_fix_texture_path(self, texture_path):
        """尝试修复纹理路径"""
        try:
            texture_name = os.path.basename(texture_path)
            
            # 常见的路径替换规则
            possible_paths = [
                # 网络路径替换
                texture_path.replace("P:/LTT", "//192.168.50.250/public/LTT"),
                texture_path.replace("P:\\LTT", "//192.168.50.250/public/LTT"),
                
                # 本地工作区路径
                os.path.join(cmds.workspace(query=True, rootDirectory=True), "sourceimages", texture_name),
                
                # 相对路径尝试
                os.path.join(os.path.dirname(texture_path), "..", "sourceimages", texture_name),
                
                # 同级目录查找
                os.path.join(os.path.dirname(texture_path), texture_name),
            ]
            
            # 添加常见纹理目录
            common_texture_dirs = [
                "textures",
                "maps", 
                "images",
                "sourceimages",
                "texture"
            ]
            
            # 从原路径推导可能的目录
            original_dir = os.path.dirname(texture_path)
            for tex_dir in common_texture_dirs:
                possible_paths.append(os.path.join(original_dir, tex_dir, texture_name))
                
                # 上级目录查找
                parent_dir = os.path.dirname(original_dir)
                possible_paths.append(os.path.join(parent_dir, tex_dir, texture_name))
            
            # 检查每个可能的路径
            for path in possible_paths:
                if os.path.exists(path):
                    return path
            
            return None
            
        except Exception as e:
            print(f"    修复纹理路径失败: {str(e)}")
            return None
    
    def _check_material_node_integrity(self):
        """检查材质节点完整性"""
        try:
            print("\n检查材质节点完整性...")
            
            # 检查孤立的材质节点
            orphaned_materials = self._find_orphaned_materials()
            
            # 检查缺失连接的材质
            disconnected_materials = self._find_disconnected_materials()
            
            # 检查重复材质
            duplicate_materials = self._find_duplicate_materials()
            
            issues_found = len(orphaned_materials) + len(disconnected_materials) + len(duplicate_materials)
            
            if issues_found == 0:
                print("✅ 材质节点完整性检查通过")
            else:
                print(f"⚠️  发现 {issues_found} 个材质节点问题")
                
        except Exception as e:
            print(f"检查材质节点完整性失败: {str(e)}")
    
    def _find_orphaned_materials(self):
        """查找孤立的材质节点"""
        try:
            orphaned = []
            
            # 获取所有材质节点
            material_nodes = cmds.ls(materials=True)
            
            for material in material_nodes:
                # 跳过默认材质
                if material in ['lambert1', 'particleCloud1', 'shaderGlow1']:
                    continue
                
                try:
                    # 检查是否连接到着色组
                    shading_groups = cmds.listConnections(material, type='shadingEngine')
                    
                    if not shading_groups:
                        orphaned.append(material)
                        
                except:
                    continue
            
            if orphaned:
                print(f"  发现 {len(orphaned)} 个孤立材质节点:")
                for material in orphaned[:5]:  # 只显示前5个
                    print(f"    - {material}")
                if len(orphaned) > 5:
                    print(f"    ... 还有 {len(orphaned) - 5} 个")
            
            return orphaned
            
        except Exception as e:
            print(f"查找孤立材质失败: {str(e)}")
            return []
    
    def _find_disconnected_materials(self):
        """查找连接断开的材质"""
        try:
            disconnected = []
            
            # 获取所有着色组
            shading_engines = cmds.ls(type='shadingEngine')
            
            for sg in shading_engines:
                # 跳过默认着色组
                if sg == 'initialShadingGroup':
                    continue
                
                try:
                    # 检查是否有材质连接
                    materials = cmds.listConnections(f"{sg}.surfaceShader")
                    
                    if not materials:
                        disconnected.append(sg)
                        
                except:
                    continue
            
            if disconnected:
                print(f"  发现 {len(disconnected)} 个断开连接的着色组:")
                for sg in disconnected[:5]:
                    print(f"    - {sg}")
                if len(disconnected) > 5:
                    print(f"    ... 还有 {len(disconnected) - 5} 个")
            
            return disconnected
            
        except Exception as e:
            print(f"查找断开材质失败: {str(e)}")
            return []
    
    def _find_duplicate_materials(self):
        """查找重复的材质"""
        try:
            duplicates = []
            material_groups = {}
            
            # 获取所有材质节点
            material_nodes = cmds.ls(materials=True)
            
            for material in material_nodes:
                # 跳过默认材质
                if material in ['lambert1', 'particleCloud1', 'shaderGlow1']:
                    continue
                
                try:
                    # 获取材质类型和基本属性作为键
                    material_type = cmds.nodeType(material)
                    
                    # 简单的重复检测（基于名称模式）
                    base_name = material.split('_')[0] if '_' in material else material
                    key = f"{material_type}_{base_name}"
                    
                    if key not in material_groups:
                        material_groups[key] = []
                    material_groups[key].append(material)
                    
                except:
                    continue
            
            # 查找有多个材质的组
            for key, materials in material_groups.items():
                if len(materials) > 1:
                    duplicates.extend(materials[1:])  # 保留第一个，其余视为重复
            
            if duplicates:
                print(f"  发现 {len(duplicates)} 个可能重复的材质:")
                for material in duplicates[:5]:
                    print(f"    - {material}")
                if len(duplicates) > 5:
                    print(f"    ... 还有 {len(duplicates) - 5} 个")
            
            return duplicates
            
        except Exception as e:
            print(f"查找重复材质失败: {str(e)}")
            return []
    
    def cleanup_unused_materials(self):
        """清理未使用的材质节点"""
        try:
            print("\n清理未使用的材质节点...")
            
            # 查找未使用的材质
            orphaned_materials = self._find_orphaned_materials()
            
            if orphaned_materials:
                # 删除孤立的材质节点
                deleted_count = 0
                for material in orphaned_materials:
                    try:
                        cmds.delete(material)
                        deleted_count += 1
                    except:
                        continue
                
                print(f"✅ 已删除 {deleted_count} 个未使用的材质节点")
            else:
                print("✅ 没有发现未使用的材质节点")
                
        except Exception as e:
            print(f"清理材质节点失败: {str(e)}")
    
    def optimize_material_networks(self):
        """优化材质网络"""
        try:
            print("\n优化材质网络...")
            
            # 合并相同的纹理节点
            self._merge_duplicate_texture_nodes()
            
            # 优化纹理采样设置
            self._optimize_texture_sampling()
            
            print("✅ 材质网络优化完成")
            
        except Exception as e:
            print(f"优化材质网络失败: {str(e)}")
    
    def _merge_duplicate_texture_nodes(self):
        """合并重复的纹理节点"""
        try:
            file_nodes = cmds.ls(type="file")
            texture_groups = {}
            
            # 按纹理路径分组
            for node in file_nodes:
                try:
                    texture_path = cmds.getAttr(f"{node}.fileTextureName")
                    if texture_path:
                        if texture_path not in texture_groups:
                            texture_groups[texture_path] = []
                        texture_groups[texture_path].append(node)
                except:
                    continue
            
            # 合并重复的纹理节点
            merged_count = 0
            for texture_path, nodes in texture_groups.items():
                if len(nodes) > 1:
                    # 保留第一个节点，替换其他节点的连接
                    master_node = nodes[0]
                    for duplicate_node in nodes[1:]:
                        try:
                            # 获取重复节点的输出连接
                            connections = cmds.listConnections(duplicate_node, plugs=True, connections=True)
                            
                            if connections:
                                # 重新连接到主节点
                                for i in range(0, len(connections), 2):
                                    src_plug = connections[i]
                                    dst_plug = connections[i + 1]
                                    
                                    # 替换连接
                                    new_src_plug = src_plug.replace(duplicate_node, master_node)
                                    cmds.connectAttr(new_src_plug, dst_plug, force=True)
                            
                            # 删除重复节点
                            cmds.delete(duplicate_node)
                            merged_count += 1
                            
                        except:
                            continue
            
            if merged_count > 0:
                print(f"  合并了 {merged_count} 个重复纹理节点")
            
        except Exception as e:
            print(f"合并纹理节点失败: {str(e)}")
    
    def _optimize_texture_sampling(self):
        """优化纹理采样设置"""
        try:
            file_nodes = cmds.ls(type="file")
            optimized_count = 0
            
            for node in file_nodes:
                try:
                    # 设置合理的过滤类型
                    cmds.setAttr(f"{node}.filterType", 1)  # Mipmap
                    
                    # 设置合理的最大分辨率
                    cmds.setAttr(f"{node}.useMaximumRes", 1)
                    cmds.setAttr(f"{node}.maximumRes", 2048)
                    
                    optimized_count += 1
                    
                except:
                    continue
            
            if optimized_count > 0:
                print(f"  优化了 {optimized_count} 个纹理节点的采样设置")
                
        except Exception as e:
            print(f"优化纹理采样失败: {str(e)}")
    
    def get_material_report(self):
        """生成材质报告"""
        try:
            report = {
                'total_materials': len(cmds.ls(materials=True)),
                'total_shading_groups': len(cmds.ls(type='shadingEngine')),
                'total_file_nodes': len(cmds.ls(type='file')),
                'missing_textures': len(self.missing_textures),
                'fixed_textures': len(self.fixed_textures),
                'orphaned_materials': len(self._find_orphaned_materials()),
                'disconnected_shading_groups': len(self._find_disconnected_materials())
            }
            
            return report
            
        except Exception as e:
            print(f"生成材质报告失败: {str(e)}")
            return {}
    
    def reset_material_cache(self):
        """重置材质缓存"""
        self.checked_materials.clear()
        self.fixed_textures.clear()
        self.missing_textures.clear()


class XGenManager:
    """XGen管理器"""
    
    def __init__(self):
        self.xgen_palettes = []
        self.xgen_descriptions = []
    
    def check_xgen_status(self):
        """检查XGen状态"""
        try:
            print("\n=== 检查XGen状态 ===")
            
            # 检查XGen插件是否加载
            if not self._is_xgen_loaded():
                print("⚠️  XGen插件未加载")
                return False
            
            # 导入XGen模块
            try:
                import xgenm
            except ImportError:
                print("❌ 无法导入XGen模块")
                return False
            
            # 获取XGen调色板
            palettes = xgenm.palettes()
            self.xgen_palettes = palettes
            
            if not palettes:
                print("✅ 场景中没有XGen调色板")
                return True
            
            print(f"发现 {len(palettes)} 个XGen调色板:")
            
            total_descriptions = 0
            for palette in palettes:
                descriptions = xgenm.descriptions(palette)
                self.xgen_descriptions.extend(descriptions)
                total_descriptions += len(descriptions)
                
                print(f"  调色板: {palette} - {len(descriptions)} 个描述")
                
                # 检查每个描述的状态
                for desc in descriptions:
                    self._check_description_status(palette, desc)
            
            print(f"XGen总计: {len(palettes)} 个调色板, {total_descriptions} 个描述")
            return True
            
        except Exception as e:
            print(f"❌ 检查XGen状态失败: {str(e)}")
            return False
    
    def _is_xgen_loaded(self):
        """检查XGen插件是否加载"""
        try:
            return cmds.pluginInfo('xgenToolkit', query=True, loaded=True)
        except:
            return False
    
    def _check_description_status(self, palette, description):
        """检查XGen描述状态"""
        try:
            import xgenm
            
            # 检查基本属性
            active = xgenm.getAttr('active', palette, description, '')
            
            if active:
                print(f"    ✅ {description}: 活动")
            else:
                print(f"    ⚠️  {description}: 非活动")
            
            # 检查几何体绑定
            bound_geometry = xgenm.boundGeometry(palette, description)
            if bound_geometry:
                print(f"      绑定几何体: {bound_geometry}")
            else:
                print(f"      ⚠️  未绑定几何体")
                
        except Exception as e:
            print(f"    检查描述 {description} 失败: {str(e)}")
    
    def setup_xgen_cache_paths(self, cache_template):
        """设置XGen缓存路径"""
        try:
            print("\n设置XGen缓存路径...")
            
            if not self.xgen_palettes:
                print("没有XGen调色板需要设置")
                return True
            
            import xgenm
            
            for palette in self.xgen_palettes:
                descriptions = xgenm.descriptions(palette)
                
                for desc in descriptions:
                    try:
                        # 设置缓存路径
                        cache_path = cache_template.replace('${DESC}', desc)
                        
                        # 设置XGen属性
                        xgenm.setAttr('cacheFileName', cache_path, palette, desc, '')
                        
                        print(f"  设置 {desc} 缓存路径: {cache_path}")
                        
                    except Exception as e:
                        print(f"  设置 {desc} 缓存路径失败: {str(e)}")
                        continue
            
            print("✅ XGen缓存路径设置完成")
            return True
            
        except Exception as e:
            print(f"❌ 设置XGen缓存路径失败: {str(e)}")
            return False