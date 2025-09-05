"""
XGen管理模块
负责处理XGen毛发缓存路径设置和状态检查
"""
import glob

import maya.cmds as cmds
import os
import xgenm


class XGenManager:
    """XGen管理器"""

    def __init__(self):
        self.default_hair_cache_template = "P:/LHSN/cache/dcc/shot/s310/c0990/cfx/alembic/hair/dwl_01/outcurve/cache_${DESC}.0001.abc"
        self.primitive_type = 'SplinePrimitive'

    def setup_hair_cache(self, cache_template=None):
        """
        设置毛发缓存路径
        
        Args:
            cache_template (str): 缓存路径模板，${DESC}会被替换为描述名称
            
        Returns:
            dict: 设置结果统计
        """
        if cache_template is None:
            cache_template = self.default_hair_cache_template

        print(f"设置XGen毛发缓存路径...")
        print(f"缓存模板: {cache_template}")

        all_fur_abc = glob.glob(cache_template)

        # 拷贝abc到当前maya文件路径
        current_scene = cmds.file(q=True, sceneName=True)
        if not current_scene:
            print("❌ 当前没有打开的Maya场景")
            return

        results = {
            'total_palettes': 0,
            'total_descriptions': 0,
            'updated_descriptions': 0,
            'failed_descriptions': 0
        }

        try:
            # 确保XGen插件已加载
            if not self._ensure_xgen_loaded():
                print("❌ XGen插件加载失败")
                return results

            # 获取所有XGen调色板
            palettes = xgenm.palettes()
            if not palettes:
                print("⚠️  场景中没有找到XGen调色板")
                return results

            results['total_palettes'] = len(palettes)
            print(f"找到 {len(palettes)} 个XGen调色板")

            # 遍历所有调色板和描述
            for palette in palettes:
                descriptions = xgenm.descriptions(palette)
                print(f"  调色板 '{palette}' 包含 {len(descriptions)} 个描述")
                # 如果有缓存，拷贝最新的abc到当前maya场景路径
                self.copy_latest_abc_to_maya_scene(cache_template, palette)

                results['total_descriptions'] += len(descriptions)

                for desc in descriptions:
                    desc_name = desc.split(':')[-1]

                    # 将${DESC}替换为实际的描述名称
                    cache_path = cache_template.replace('${DESC}', desc_name)

                    # 获取实际的名字
                    for _ in all_fur_abc:
                        if desc_name in _:
                            cache_path = _.replace('\\', '/')
                            break

                    if self._set_cache_for_description(palette, desc, desc_name, cache_path):
                        results['updated_descriptions'] += 1
                    else:
                        results['failed_descriptions'] += 1

            print(f"毛发缓存设置完成: {results['updated_descriptions']}/{results['total_descriptions']} 个描述已更新")

            return results

        except Exception as e:
            print(f"设置毛发缓存路径失败: {str(e)}")
            return results

    def copy_latest_abc_to_maya_scene(self, cache_template, namespaces):
        """拷贝最新的abc文件到当前Maya场景路径"""
        import os
        import shutil
        import glob
        import re
        import maya.cmds as cmds

        # 获取当前Maya场景目录
        current_scene = cmds.file(q=True, sceneName=True)
        if not current_scene:
            print("❌ 当前没有打开的Maya场景")
            return None

        current_dir = os.path.dirname(current_scene)
        scene_name = os.path.basename(current_scene)

        # # 查找所有序列文件
        print('开始寻找毛发生长面的缓存abc文件...')
        cache_dir = os.path.abspath(os.path.join(cache_template, '../../growmesh_batch'))
        search_pattern = os.path.join(cache_dir, "*.abc").replace('\\', '/')
        print(f"寻找模板：{search_pattern}")
        abc_files = glob.glob(search_pattern)

        if not abc_files:
            print("❌ 未找到abc文件")
            return None

        max_seq = -1
        latest_file = None

        for file_path in abc_files:
            filename = os.path.basename(file_path)
            seq_match = re.search(rf'\.(\d+)\.abc$', filename)

            if seq_match:
                seq_num = int(seq_match.group(1))
                if seq_num > max_seq:
                    max_seq = seq_num
                    latest_file = file_path

        # 如果没找到有序列号的文件，就用第一个
        if not latest_file and abc_files:
            latest_file = abc_files[0]
            print(f"未找到序列号文件，使用第一个: {os.path.basename(latest_file)}")

        if not latest_file:
            print("❌ 未找到有效序列文件")
            return None

        print(f"📄 找到最新文件: {os.path.basename(latest_file)}")

        # 构建目标路径 - 保持alembic目录结构
        cache_relative = cache_template.replace("P:\\LHSN\\cache\\dcc\\shot\\", "")
        parts = cache_relative.split("\\")

        try:
            alembic_index = parts.index('alembic')
            alembic_path = "\\".join(parts[alembic_index:])
        except ValueError:
            alembic_path = os.path.basename(latest_file)

        # 更新为最新序列号文件名
        target_dir = os.path.join(current_dir, os.path.dirname(alembic_path))
        target_filename = f"{scene_name.split('.')[0]}__{namespaces.split(':')[0]}__ns__{namespaces.split(':')[1]}.abc"
        target_path = os.path.join(target_dir, target_filename).replace('\\', '/')

        # 创建目录并拷贝
        os.makedirs(target_dir, exist_ok=True)

        try:
            shutil.copy2(latest_file, target_path)
            print(f"✅ 拷贝完成: {target_path}")
            return target_path
        except Exception as e:
            print(f"❌ 拷贝失败: {e}")
            return None

    def _ensure_xgen_loaded(self):
        """确保XGen插件已加载"""
        try:
            if not cmds.pluginInfo('xgenToolkit', query=True, loaded=True):
                cmds.loadPlugin('xgenToolkit')
                print("已加载xgenToolkit插件")
            return True
        except Exception as e:
            print(f"加载XGen插件失败: {str(e)}")
            return False

    def _set_cache_for_description(self, palette, desc, desc_name, cache_path):
        """
        为特定描述设置缓存
        
        Args:
            palette (str): 调色板名称
            desc (str): 描述名称
            desc_name (str): 清理后的描述名称
            cache_path (str): 缓存文件路径
            
        Returns:
            bool: 是否设置成功
        """
        try:
            # 检查缓存文件是否存在
            cache_exists = os.path.exists(cache_path)

            # 设置XGen属性
            xgenm.setAttr('useCache', 'true' if cache_exists else 'false', palette, desc, self.primitive_type)
            xgenm.setAttr('liveMode', 'false', palette, desc, self.primitive_type)
            xgenm.setAttr('cacheFileName', cache_path, palette, desc, self.primitive_type)

            status = "✅" if cache_exists else "⚠️"
            existence_msg = "存在" if cache_exists else "不存在"
            print(f"    {status} 描述 '{desc_name}': {existence_msg} - {os.path.basename(cache_path)}")

            return True

        except Exception as e:
            print(f"    ❌ 描述 '{desc_name}' 设置失败: {str(e)}")
            return False

    def check_xgen_status(self):
        """
        检查XGen状态
        
        Returns:
            dict: XGen状态信息
        """
        print("\n=== XGen状态检查 ===")

        status_info = {
            'total_palettes': 0,
            'total_descriptions': 0,
            'cached_descriptions': 0,
            'missing_cache_files': 0,
            'details': []
        }

        try:
            if not self._ensure_xgen_loaded():
                print("❌ XGen插件未加载")
                return status_info

            palettes = xgenm.palettes()
            if not palettes:
                print("场景中没有XGen调色板")
                return status_info

            status_info['total_palettes'] = len(palettes)
            print(f"XGen调色板数量: {len(palettes)}")

            for palette in palettes:
                descriptions = xgenm.descriptions(palette)
                palette_info = {
                    'palette': palette,
                    'descriptions': []
                }

                print(f"\n调色板: {palette}")
                print(f"  描述数量: {len(descriptions)}")
                status_info['total_descriptions'] += len(descriptions)

                for desc in descriptions:
                    desc_info = self._get_description_info(palette, desc)
                    palette_info['descriptions'].append(desc_info)

                    if desc_info['use_cache']:
                        status_info['cached_descriptions'] += 1

                    if desc_info['use_cache'] and not desc_info['cache_file_exists']:
                        status_info['missing_cache_files'] += 1

                    self._print_description_info(desc_info)

                status_info['details'].append(palette_info)

            # 打印总结
            print(f"\n=== XGen状态总结 ===")
            print(f"调色板总数: {status_info['total_palettes']}")
            print(f"描述总数: {status_info['total_descriptions']}")
            print(f"使用缓存的描述: {status_info['cached_descriptions']}")
            print(f"缺失缓存文件的描述: {status_info['missing_cache_files']}")

            return status_info

        except Exception as e:
            print(f"检查XGen状态失败: {str(e)}")
            return status_info

    def _get_description_info(self, palette, desc):
        """获取描述信息"""
        desc_name = desc.split(':')[-1]
        desc_info = {
            'name': desc_name,
            'full_name': desc,
            'use_cache': False,
            'live_mode': True,
            'cache_file': '',
            'cache_file_exists': False
        }

        try:
            use_cache = xgenm.getAttr('useCache', palette, desc, self.primitive_type)
            live_mode = xgenm.getAttr('liveMode', palette, desc, self.primitive_type)
            cache_file = xgenm.getAttr('cacheFileName', palette, desc, self.primitive_type)

            desc_info['use_cache'] = use_cache.lower() == 'true'
            desc_info['live_mode'] = live_mode.lower() == 'true'
            desc_info['cache_file'] = cache_file

            if cache_file and os.path.exists(cache_file):
                desc_info['cache_file_exists'] = True

        except Exception as e:
            print(f"    获取描述 {desc_name} 信息失败: {str(e)}")

        return desc_info

    def _print_description_info(self, desc_info):
        """打印描述信息"""
        print(f"  描述: {desc_info['name']}")
        print(f"    使用缓存: {desc_info['use_cache']}")
        print(f"    实时模式: {desc_info['live_mode']}")
        print(f"    缓存文件: {desc_info['cache_file']}")

        if desc_info['cache_file']:
            if desc_info['cache_file_exists']:
                print(f"    缓存文件状态: ✅ 存在")
            else:
                print(f"    缓存文件状态: ❌ 不存在")
        else:
            print(f"    缓存文件状态: ⚠️  未设置")

    def get_xgen_statistics(self):
        """
        获取XGen统计信息
        
        Returns:
            dict: 统计信息
        """
        stats = {
            'palette_count': 0,
            'description_count': 0,
            'cached_count': 0,
            'live_count': 0,
            'missing_cache_count': 0
        }

        try:
            if not self._ensure_xgen_loaded():
                return stats

            palettes = xgenm.palettes()
            stats['palette_count'] = len(palettes)

            for palette in palettes:
                descriptions = xgenm.descriptions(palette)
                stats['description_count'] += len(descriptions)

                for desc in descriptions:
                    try:
                        use_cache = xgenm.getAttr('useCache', palette, desc, self.primitive_type).lower() == 'true'
                        live_mode = xgenm.getAttr('liveMode', palette, desc, self.primitive_type).lower() == 'true'
                        cache_file = xgenm.getAttr('cacheFileName', palette, desc, self.primitive_type)

                        if use_cache:
                            stats['cached_count'] += 1

                        if live_mode:
                            stats['live_count'] += 1

                        if use_cache and cache_file and not os.path.exists(cache_file):
                            stats['missing_cache_count'] += 1

                    except:
                        pass

        except Exception as e:
            print(f"获取XGen统计信息失败: {str(e)}")

        return stats

    def update_cache_template(self, new_template):
        """
        更新缓存模板
        
        Args:
            new_template (str): 新的缓存模板
        """
        self.default_hair_cache_template = new_template
        print(f"缓存模板已更新: {new_template}")

    def enable_all_caches(self):
        """启用所有描述的缓存"""
        try:
            palettes = xgenm.palettes()
            updated_count = 0

            for palette in palettes:
                descriptions = xgenm.descriptions(palette)
                for desc in descriptions:
                    try:
                        xgenm.setAttr('useCache', 'true', palette, desc, self.primitive_type)
                        xgenm.setAttr('liveMode', 'false', palette, desc, self.primitive_type)
                        updated_count += 1
                    except:
                        pass

            print(f"已启用 {updated_count} 个描述的缓存")
            return updated_count

        except Exception as e:
            print(f"启用缓存失败: {str(e)}")
            return 0

    def disable_all_caches(self):
        """禁用所有描述的缓存"""
        try:
            palettes = xgenm.palettes()
            updated_count = 0

            for palette in palettes:
                descriptions = xgenm.descriptions(palette)
                for desc in descriptions:
                    try:
                        xgenm.setAttr('useCache', 'false', palette, desc, self.primitive_type)
                        xgenm.setAttr('liveMode', 'true', palette, desc, self.primitive_type)
                        updated_count += 1
                    except:
                        pass

            print(f"已禁用 {updated_count} 个描述的缓存")
            return updated_count

        except Exception as e:
            print(f"禁用缓存失败: {str(e)}")
            return 0
