"""
动画管理模块
负责处理动画连接、BlendShape创建和毛发布料处理
"""
import glob

import maya.cmds as cmds
import os
import re
import sys

# 简化的直接导入
try:
    from managers.blendshape_manager import BlendshapeManager
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    from blendshape_manager import BlendshapeManager


def import_abc_to_group(abc_path, namespace='cloth', group_name='group'):
    # 记录导入前的命名空间
    existing_namespaces = cmds.namespaceInfo(listOnlyNamespaces=True) or []

    # 1) 导入 Alembic
    cmds.file(
        abc_path,
        i=True,
        type="Alembic",
        ignoreVersion=True,
        ra=True,
        gr=True,
        mergeNamespacesOnClash=False,
        namespace=namespace,
        pr=True,
        importTimeRange="combine"
    )

    # 2) 找出实际使用的命名空间（可能被Maya重命名了）
    current_namespaces = cmds.namespaceInfo(listOnlyNamespaces=True) or []
    new_namespaces = [ns for ns in current_namespaces if ns not in existing_namespaces and ns.startswith(namespace)]

    if new_namespaces:
        actual_namespace = new_namespaces[0]

        # 3) 如果命名空间被重命名了，改回我们想要的名称
        if actual_namespace != namespace:
            try:
                # 如果目标命名空间已存在且有内容，先清空或重命名
                if cmds.namespace(exists=namespace):
                    existing_content = cmds.ls(f"{namespace}:*") or []
                    if existing_content:
                        # 临时重命名现有命名空间
                        temp_name = f"{namespace}_temp"
                        i = 1
                        while cmds.namespace(exists=temp_name):
                            temp_name = f"{namespace}_temp{i}"
                            i += 1
                        cmds.namespace(rename=(namespace, temp_name))

                # 重命名新导入的命名空间
                cmds.namespace(rename=(actual_namespace, namespace))
                actual_namespace = namespace

            except Exception as e:
                pass
    else:
        actual_namespace = namespace

    # 4) 查找顶层节点（没有父节点的transform节点）
    all_ns_nodes = cmds.ls(f"{actual_namespace}:*", type='transform') or []
    top_level_nodes = []

    for node in all_ns_nodes:
        # 检查父节点
        parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
        # 如果没有父节点，或者父节点不在同一命名空间，则认为是顶层节点
        is_top_level = True
        for parent in parents:
            parent_short = cmds.ls(parent, sn=True)[0] if parent else ""
            if parent_short.startswith(f"{actual_namespace}:"):
                is_top_level = False
                break

        if is_top_level:
            top_level_nodes.append(node)

    # 5) 创建目标组
    target_group = f"{actual_namespace}:{group_name}"

    if not cmds.objExists(target_group):
        original_ns = cmds.namespaceInfo(currentNamespace=True)
        try:
            cmds.namespace(setNamespace=actual_namespace)
            cmds.group(empty=True, name=group_name)
        finally:
            cmds.namespace(setNamespace=original_ns)

    # 6) 只移动顶层节点到目标组（保留原有层级结构）
    moved_count = 0
    for node in top_level_nodes:
        if node != target_group:  # 排除目标组本身
            try:
                cmds.parent(node, target_group)
                moved_count += 1
            except Exception as e:
                pass

    # 7) 清理空的无命名空间组
    if cmds.objExists(group_name) and group_name != target_group:
        children = cmds.listRelatives(group_name, children=True) or []
        if not children:
            cmds.delete(group_name)

    return target_group, actual_namespace


class AnimationManager:
    """动画管理器"""

    def __init__(self):
        self.blendshape_manager = BlendshapeManager()
        self.animation_files = []
        self.fur_files = []
        self.cloth_files = []
        self.fur_namespace = "asset_fur"
        self.cloth_namespace = "asset_cloth"
        self.actual_fur_namespace = None
        self.actual_cloth_namespace = None

    def set_animation_files(self, animation_files):
        """设置动画文件列表"""
        self.animation_files = animation_files
        print(f"设置动画文件: {len(animation_files)} 个")

    def find_fur_and_cloth_files(self, animation_files, sequence, shot, lookdev_namespace):
        """
        查找毛发和布料文件 - 使用基于模板路径的查找方法
        
        Args:
            animation_files (list): 动画文件列表（可能包含字典或字符串）
        """
        print("查找毛发和布料文件...")

        self.fur_files = []
        self.cloth_files = []

        # 如果没有找到CFX文件，使用基于模板路径的查找方法（旧版本逻辑）
        if len(self.fur_files) == 0 and len(self.cloth_files) == 0:
            print("未在扫描结果中找到CFX文件，使用基于模板路径的查找...")
            self._find_cfx_files_by_template(sequence, shot, lookdev_namespace)

        print(f"毛发文件: {len(self.fur_files)} 个")
        print(f"布料文件: {len(self.cloth_files)} 个")

    def _find_cfx_files_by_template(self, sequence, shot, lookdev_namespace):
        """基于毛发缓存模板路径查找CFX文件（旧版本逻辑）"""
        try:
            from config.config_manager import ConfigManager
            config_manager = ConfigManager()
            hair_template = config_manager.base_paths.get('hair_cache_template').format(sequence=sequence, shot=shot)

            # 查找毛发文件
            fur_file = self._find_fur_cache_file(hair_template)
            if fur_file:
                self.fur_files.append(fur_file)
                print(f"  基于模板找到毛发文件: {os.path.basename(fur_file)}")

            # 查找布料文件
            cloth_file = self._find_cloth_cache_file(hair_template, lookdev_namespace)
            if cloth_file:
                self.cloth_files.append(cloth_file)
                print(f"  基于模板找到布料文件: {os.path.basename(cloth_file)}")

        except Exception as e:
            print(f"基于模板查找CFX文件失败: {str(e)}")

    def _find_fur_cache_file(self, hair_template):
        """查找毛发解算文件（基于旧版本逻辑）"""
        try:
            print(hair_template)
            # 解析路径获取hair目录
            path_parts = hair_template.replace('\\', '/').split('/')
            hair_index = -1
            for i, part in enumerate(path_parts):
                if part == 'hair':
                    hair_index = i
                    break

            if hair_index < 0:
                print("无法从模板路径找到hair目录")
                return None

            # 构建hair目录路径
            hair_dir = '/'.join(path_parts[:hair_index + 1])
            hair_dir = hair_dir.replace('/', '\\')

            print(f"搜索毛发解算文件目录: {hair_dir}")

            if not os.path.exists(hair_dir):
                print(f"目录不存在: {hair_dir}")
                return None

            abc = glob.glob(os.path.join(hair_dir, '*/growmesh_batch/*.abc'))

            # 查找ABC文件
            if abc:
                fur_file_path = abc[0]
                print(f"找到候选毛发文件: {fur_file_path}")
                return fur_file_path

            return None

        except Exception as e:
            print(f"查找毛发解算文件失败: {str(e)}")
            return None

    def _find_cloth_cache_file(self, hair_template, lookdev_namespace):
        """查找布料解算文件（基于旧版本逻辑）"""
        try:
            # 解析路径获取基础cfx目录
            path_parts = hair_template.replace('\\', '/').split('/')
            alembic_index = -1
            for i, part in enumerate(path_parts):
                if part == 'alembic':
                    alembic_index = i
                    break

            if alembic_index < 0:
                print("无法从模板路径找到alembic目录")
                return None

            # 构建cloth目录路径
            cloth_dir = ('/'.join(path_parts[:alembic_index + 1]) + '/cloth' + r"{}_01".
                         format(lookdev_namespace.replace("_lookdev", '')))
            cloth_dir = cloth_dir.replace('/', '\\')

            print(f"搜索布料解算文件目录: {cloth_dir}")

            if not os.path.exists(cloth_dir):
                print(f"目录不存在: {cloth_dir}")
                return None

            # 查找ABC文件
            for root, dirs, files in os.walk(cloth_dir):
                for file in files:
                    if file.endswith('.abc'):
                        cloth_file_path = os.path.join(root, file)
                        print(f"找到候选布料文件: {cloth_file_path}")
                        return cloth_file_path

            return None

        except Exception as e:
            print(f"查找布料解算文件失败: {str(e)}")
            return None

    def import_and_connect_fur_cache(self):
        """导入和连接毛发缓存"""
        print("\n=== 导入毛发缓存 ===")

        if not self.fur_files:
            print("没有找到毛发文件")
            return True

        success_count = 0
        for fur_file in self.fur_files:
            if self._import_fur_file(fur_file):
                success_count += 1

        if success_count > 0:
            print(f"✅ 成功导入 {success_count} 个毛发文件")
            # 处理毛发BlendShape连接
            self._handle_fur_blendshapes()
            return True
        else:
            print("❌ 毛发文件导入失败")
            return False

    def import_and_connect_cloth_cache(self):
        """导入和连接布料缓存"""
        print("\n=== 导入布料缓存 ===")

        if not self.cloth_files:
            print("没有找到布料文件")
            return True

        success_count = 0
        for cloth_file in self.cloth_files:
            if self._import_cloth_file(cloth_file):
                success_count += 1

        if success_count > 0:
            print(f"✅ 成功导入 {success_count} 个布料文件")
            # 处理布料BlendShape
            self._handle_cloth_blendshapes()
            return True
        else:
            print("❌ 布料文件导入失败")
            return False

    def _import_fur_file(self, fur_file):
        """导入单个毛发文件"""
        try:
            print(f"导入毛发文件: {fur_file}")

            if not os.path.exists(fur_file):
                print(f"❌ 毛发文件不存在: {fur_file}")
                return False

            # 记录导入前的命名空间
            namespaces_before = set(cmds.namespaceInfo(listOnlyNamespaces=True))

            # 导入文件
            file_ext = os.path.splitext(fur_file)[1].lower()
            if file_ext == '.abc':
                import_abc_to_group(fur_file, namespace=self.fur_namespace, group_name='fur')
            else:
                # Maya文件导入
                cmds.file(
                    fur_file,
                    i=True,
                    type="mayaAscii" if file_ext == '.ma' else "mayaBinary",
                    ignoreVersion=True,
                    ra=True,
                    mergeNamespacesOnClash=False,
                    namespace=self.fur_namespace,
                    pr=True
                )

            # 检查实际创建的命名空间
            namespaces_after = set(cmds.namespaceInfo(listOnlyNamespaces=True))
            new_namespaces = namespaces_after - namespaces_before

            # 找到实际的毛发命名空间
            for ns in new_namespaces:
                if self.fur_namespace in ns:
                    self.actual_fur_namespace = ns
                    print(f"实际毛发命名空间: {ns}")
                    break

            print(f"✅ 毛发文件导入成功")
            return True

        except Exception as e:
            print(f"❌ 导入毛发文件失败: {str(e)}")
            return False

    def _import_cloth_file(self, cloth_file):
        """导入单个布料文件"""
        try:
            print(f"导入布料文件: {os.path.basename(cloth_file)}")

            if not os.path.exists(cloth_file):
                print(f"❌ 布料文件不存在: {cloth_file}")
                return False

            # 记录导入前的命名空间
            namespaces_before = set(cmds.namespaceInfo(listOnlyNamespaces=True))

            # 导入文件
            file_ext = os.path.splitext(cloth_file)[1].lower()
            if file_ext == '.abc':
                # ABC文件导入
                if not cmds.pluginInfo('AbcImport', query=True, loaded=True):
                    cmds.loadPlugin('AbcImport')
                cmds.file(
                    cloth_file,
                    i=True,
                    type="Alembic",
                    ignoreVersion=True,
                    ra=True,  # reference as - 正确的namespace导入参数
                    mergeNamespacesOnClash=False,
                    namespace=self.cloth_namespace,
                    pr=True,  # preserve references
                    importTimeRange="combine"
                )
            else:
                # Maya文件导入
                cmds.file(
                    cloth_file,
                    i=True,
                    type="mayaAscii" if file_ext == '.ma' else "mayaBinary",
                    ignoreVersion=True,
                    ra=True,
                    mergeNamespacesOnClash=False,
                    namespace=self.cloth_namespace,
                    pr=True
                )

            # 检查实际创建的命名空间
            namespaces_after = set(cmds.namespaceInfo(listOnlyNamespaces=True))
            new_namespaces = namespaces_after - namespaces_before

            # 找到实际的布料命名空间
            for ns in new_namespaces:
                if self.cloth_namespace in ns:
                    self.actual_cloth_namespace = ns
                    print(f"实际布料命名空间: {ns}")
                    break

            print(f"✅ 布料文件导入成功")
            return True

        except Exception as e:
            print(f"❌ 导入布料文件失败: {str(e)}")
            return False

    def _handle_cloth_blendshapes(self):
        """处理布料BlendShape连接 - 使用精确匹配方法"""
        print("处理布料BlendShape连接...")

        try:
            if not self.actual_cloth_namespace:
                print("❌ 没有找到布料命名空间")
                return False

            # 查找cloth组（CFX源）和lookdev目标组
            cloth_group = self._find_cloth_group()
            target_group = self._find_lookdev_target_group()

            if not cloth_group or not target_group:
                print(f"❌ 未找到必要的组: cloth_group={cloth_group}, target_group={target_group}")
                return False

            print(f"使用精确匹配: {cloth_group} -> {target_group}")

            # 使用新的精确匹配方法
            created_blendshapes = self.blendshape_manager.create_precise_blendshapes_between_groups(
                cloth_group, target_group
            )

            if len(created_blendshapes) > 0:
                print(f"✅ 布料BlendShape创建成功: {len(created_blendshapes)} 个连接")
                # 隐藏cloth组
                try:
                    cmds.setAttr(cloth_group + '.visibility', 0)
                    print("已隐藏cloth组")
                except:
                    pass
                return True
            else:
                print("❌ 布料BlendShape创建失败")
                return False

        except Exception as e:
            print(f"❌ 处理布料BlendShape失败: {str(e)}")
            return False

    def _find_cloth_group(self):
        """查找cloth组"""
        if not self.actual_cloth_namespace:
            return None

        print(f"查找布料组，命名空间: {self.actual_cloth_namespace}")

        # 查找布料命名空间下的所有transform
        transforms = cmds.ls(f"{self.actual_cloth_namespace}:*", type='transform', long=True) or []
        print(f"布料命名空间下的transform数量: {len(transforms)}")

        if transforms:
            print("布料命名空间下的前5个transform:")
            for i, transform in enumerate(transforms[:5]):
                print(f"  {i + 1}. {transform}")

        # 查找顶层组（没有父节点或父节点不在此命名空间）
        for transform in transforms:
            parent = cmds.listRelatives(transform, parent=True, fullPath=True)

            # 检查是否是顶层组
            if not parent:
                # 没有父节点，是顶层组
                print(f"找到布料顶层组: {transform}")
                return transform
            elif parent and not parent[0].startswith(f"|{self.actual_cloth_namespace}"):
                # 父节点不在此命名空间，也是顶层组
                print(f"找到布料顶层组（跨命名空间）: {transform}")
                return transform

        # 如果没有找到明确的顶层组，尝试查找包含mesh的组
        for transform in transforms:
            children = cmds.listRelatives(transform, children=True, type='mesh') or []
            if children:
                print(f"找到包含mesh的布料组: {transform}")
                return transform

        print("未找到布料组")
        return None

    def _find_lookdev_target_group(self):
        """查找Lookdev目标组 - 处理Master>GEO结构"""
        print("查找Lookdev目标组...")

        # 在场景中查找Lookdev命名空间下的组
        all_transforms = cmds.ls(type='transform', long=True)

        # 优先查找包含lookdev命名空间的组
        for transform in all_transforms:
            transform_name = transform.split('|')[-1]

            # 查找Lookdev命名空间下的Master>GEO结构
            if ':Master' in transform_name and 'lookdev' in transform_name:
                # 查找Master下的GEO组
                geo_children = cmds.listRelatives(transform, children=True, fullPath=True) or []
                for child in geo_children:
                    child_name = child.split('|')[-1]
                    if ':GEO' in child_name:
                        print(f"找到Lookdev Master>GEO目标组: {child}")
                        return child

            # 也查找直接的GEO组作为备选（Lookdev命名空间）
            elif ':GEO' in transform_name and 'lookdev' in transform_name:
                parent = cmds.listRelatives(transform, parent=True)
                if not parent:
                    print(f"找到Lookdev GEO目标组: {transform}")
                    return transform

        # 如果没有找到lookdev命名空间组，查找动画命名空间的GEO组
        for transform in all_transforms:
            transform_name = transform.split('|')[-1]
            if ':GEO' in transform_name and 'animation' in transform_name:
                parent = cmds.listRelatives(transform, parent=True)
                if not parent:
                    print(f"找到动画GEO目标组: {transform}")
                    return transform

        # 最后查找普通的GEO组
        for transform in all_transforms:
            transform_name = transform.split('|')[-1].lower()
            if 'geo' in transform_name:
                parent = cmds.listRelatives(transform, parent=True)
                if not parent:
                    print(f"找到普通GEO组: {transform}")
                    return transform

        print("未找到目标组")
        return None

    def _handle_fur_blendshapes(self):
        """处理毛发BlendShape连接 - 使用精确匹配方法"""
        print("处理毛发BlendShape连接...")

        try:
            if not self.actual_fur_namespace:
                print("❌ 没有找到毛发命名空间")
                return False

            # 查找毛发组（CFX源）和lookdev目标组
            fur_group = self._find_fur_group()
            target_group = self._find_lookdev_target_group()

            if not fur_group or not target_group:
                print(f"❌ 未找到必要的组: fur_group={fur_group}, target_group={target_group}")
                return False

            print(f"使用精确匹配: {fur_group} -> {target_group}")

            # 使用新的精确匹配方法
            created_blendshapes = self.blendshape_manager.create_precise_blendshapes_between_groups(
                fur_group, target_group
            )

            if len(created_blendshapes) > 0:
                print(f"✅ 毛发BlendShape创建成功: {len(created_blendshapes)} 个连接")
                # 隐藏毛发组
                try:
                    cmds.setAttr(fur_group + '.visibility', 0)
                    print("已隐藏毛发组")
                except:
                    pass
                return True
            else:
                print("❌ 毛发BlendShape创建失败")
                return False

        except Exception as e:
            print(f"❌ 处理毛发BlendShape失败: {str(e)}")
            return False

    def _find_fur_group(self):
        """查找毛发组"""
        if not self.actual_fur_namespace:
            return None

        print(f"查找毛发组，命名空间: {self.actual_fur_namespace}")

        # 查找毛发命名空间下的所有transform
        transforms = cmds.ls(f"{self.actual_fur_namespace}:*", type='transform', long=True) or []
        print(f"毛发命名空间下的transform数量: {len(transforms)}")

        if transforms:
            print("毛发命名空间下的前5个transform:")
            for i, transform in enumerate(transforms[:5]):
                print(f"  {i + 1}. {transform}")

        # 查找顶层组（没有父节点或父节点不在此命名空间）
        for transform in transforms:
            parent = cmds.listRelatives(transform, parent=True, fullPath=True)

            # 检查是否是顶层组
            if not parent:
                # 没有父节点，是顶层组
                print(f"找到毛发顶层组: {transform}")
                return transform
            elif parent and not parent[0].startswith(f"|{self.actual_fur_namespace}"):
                # 父节点不在此命名空间，也是顶层组
                print(f"找到毛发顶层组（跨命名空间）: {transform}")
                return transform

        # 如果没有找到明确的顶层组，尝试查找包含mesh的组
        for transform in transforms:
            children = cmds.listRelatives(transform, children=True, type='mesh') or []
            if children:
                print(f"找到包含mesh的毛发组: {transform}")
                return transform

        print("未找到毛发组")
        return None

    def handle_special_groups_blendshape(self, lookdev_namespace):
        """处理特殊组的BlendShape连接"""
        print("处理特殊组BlendShape连接...")

        try:
            cfx_fur = (f'|{self.fur_namespace}:fur'
                       f'|{self.fur_namespace}:chr_{lookdev_namespace.replace("_lookdev", "")}_growthmesh_grp')
            lookdev_fur = (f'|{lookdev_namespace}:Master|{lookdev_namespace}:GEO|{lookdev_namespace}:CFX'
                           f'|{lookdev_namespace}:chr_{lookdev_namespace.replace("_lookdev", "")}_growthmesh_grp')
            print(cfx_fur, lookdev_fur)
            self.blendshape_manager.create_precise_blendshapes_between_groups(
                cfx_fur, lookdev_fur
            )

        except Exception as e:
            print(f"❌ 处理特殊组BlendShape失败: {str(e)}")
            return False

    def get_animation_statistics(self):
        """获取动画统计信息"""
        stats = {
            'total_animation_files': len(self.animation_files),
            'fur_files': len(self.fur_files),
            'cloth_files': len(self.cloth_files),
            'fur_namespace': self.actual_fur_namespace or self.fur_namespace,
            'cloth_namespace': self.actual_cloth_namespace or self.cloth_namespace,
            'blendshape_count': 0
        }

        # 统计BlendShape数量
        try:
            blendshapes = cmds.ls(type='blendShape') or []
            stats['blendshape_count'] = len(blendshapes)
        except:
            pass

        return stats

    def print_animation_info(self):
        """打印动画信息"""
        print("\n=== 动画信息 ===")
        stats = self.get_animation_statistics()

        print(f"总动画文件: {stats['total_animation_files']}")
        print(f"毛发文件: {stats['fur_files']}")
        print(f"布料文件: {stats['cloth_files']}")
        print(f"毛发命名空间: {stats['fur_namespace']}")
        print(f"布料命名空间: {stats['cloth_namespace']}")
        print(f"BlendShape数量: {stats['blendshape_count']}")

    def cleanup_animation(self):
        """清理动画相关内容"""
        try:
            # 清理命名空间
            for namespace in [self.actual_fur_namespace, self.actual_cloth_namespace]:
                if namespace and cmds.namespace(exists=namespace):
                    cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)
                    print(f"已清理命名空间: {namespace}")

            # 重置状态
            self.animation_files.clear()
            self.fur_files.clear()
            self.cloth_files.clear()
            self.actual_fur_namespace = None
            self.actual_cloth_namespace = None

        except Exception as e:
            print(f"清理动画内容失败: {str(e)}")

    def set_namespaces(self, fur_namespace, cloth_namespace):
        """设置命名空间"""
        self.fur_namespace = fur_namespace
        self.cloth_namespace = cloth_namespace

    def get_namespaces(self):
        """获取命名空间"""
        return {
            'fur': self.actual_fur_namespace or self.fur_namespace,
            'cloth': self.actual_cloth_namespace or self.cloth_namespace
        }
