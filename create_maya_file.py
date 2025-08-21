# coding=utf-8

import re
import sys
import os
import maya.cmds as cmds
import maya.mel as mel
from datetime import datetime

# 添加当前文件路径到系统路径
current_file_path = r'C:\CgTeamWork_v7\bin\lib'
cg_base_path = os.path.join(current_file_path, '../../bin/base')
cg_plugin_path = os.path.join(cg_base_path, 'cg_plugin')
cgtw_base = os.path.join(
    '/'.join(sys.executable.replace("\\", '/').split('/')[:-3]),
    'bin/base'
)

for path in [
    cg_base_path, cg_plugin_path, current_file_path, cgtw_base,
    '/Applications/CGTeamwork_v7.0/bin/base',
    r'C:\CgTeamWork_v7\bin\base'
]:
    if path not in sys.path:
        sys.path.append(path)

import cgtw2  # noqa


class CGTeamWorkApi:
    # 镜头任务字段列表
    task_field_sign_list = [
        'seq.entity',  # 场次
        'eps.entity',  # 集数
        'shot.entity',  # 镜头
        'task.entity',  # 任务
        'shot.fps',  # 镜头fps
        'shot.start_frame',  # 镜头开始帧
        'shot.end_frame',  # 镜头结束帧
        'task.res',  # 分辨率
        'task.artist',  # 制作者
        'task.status',  # 状态
        'pipeline.entity',  # 阶段
        'task.sup_review',  # 总监审核
        'seq.showdeadline',  # 场次截止日期
    ]

    # 资产任务字段列表
    asset_field_sign_list = [
        'asset.link_asset_type',
        'asset.entity',
        'asset.cn_name',
        'task.entity',
        'task.artist',
        'task.status',
        'task.sup_review',
    ]

    def __init__(self):
        try:
            self.client = cgtw2.tw()
        except Exception as e:
            raise Exception(f"Failed to connect to CGTeamWork: {e}")

    @staticmethod
    def _sort(data, key, reverse=True):
        """排序，支持自然排序（如shot0010, shot0020或sc001, sc002）"""

        def natural_sort_key(s):
            """自然排序的键函数"""
            if not s:
                return []
            return [int(text) if text.isdigit() else text.lower()
                    for text in re.split(r'(\d+)', str(s))]

        if not data:
            return []

        def get_key_value(item):
            value = item.get(key, '')
            if '.' in key and not value:
                parts = key.split('.')
                temp = item
                for part in parts:
                    if isinstance(temp, dict) and part in temp:
                        temp = temp[part]
                    else:
                        temp = ''
                        break
                value = temp
            return value

        return sorted(data, key=lambda x: natural_sort_key(get_key_value(x)), reverse=reverse)

    def get_task(self, project_db, id_list, limit="1000000"):
        """获取镜头任务信息"""
        module = 'shot'
        try:
            task_list = self.client.task.get(project_db, module, id_list, self.task_field_sign_list, limit=limit)
        except Exception as e:
            try:
                temp_fields = self.task_field_sign_list.copy()
                if 'eps.entity' in temp_fields:
                    temp_fields.remove('eps.entity')
                task_list = self.client.task.get(project_db, module, id_list, temp_fields, limit=limit)
            except Exception as e2:
                print(f"获取任务信息时出错: {e2}")
                try:
                    field_sign_list = self.client.task.fields(project_db, module)
                    task_list = self.client.task.get(project_db, module, id_list, field_sign_list, limit=limit)
                except Exception as e3:
                    print(f"使用所有字段获取任务时出错: {e3}")
                    return []
        return task_list

    def get_assets_task(self, project_db, id_list, limit='1000000'):
        """获取资产任务信息"""
        module = 'asset'
        try:
            task_list = self.client.task.get(project_db, module, id_list, self.asset_field_sign_list, limit=limit)
        except Exception as e:
            print(f"获取资产任务时出错: {e}")
            try:
                field_sign_list = self.client.task.fields(project_db, module)
                task_list = self.client.task.get(project_db, module, id_list, field_sign_list, limit=limit)
            except Exception as e2:
                print(f"使用所有字段获取资产任务时出错: {e2}")
                return []
        return task_list

    def get_drive_by_project(self, project_db_name):
        """获取项目对应的盘符路径"""
        field_sign_list = self.client.server.fields()
        data = self.client.server.get(project_db_name, field_sign_list)
        if os.name == 'nt':
            return data[0].get('win_path', '')
        elif os.name == 'darwin' or os.name == 'posix':
            return data[0].get('mac_path', '')
        else:
            return data[0].get('linux_path', '')

    def get_project(self, project_db_name):
        """获取项目列表"""
        field_sign_list = self.client.project.fields()
        filter_list = [
            ["project.status", "=", "Active"],
            ["project.database", "=", project_db_name]
        ]
        id_list = self.client.project.get_id(filter_list, limit="5000", start_num="")
        data = self.client.project.get(id_list, field_sign_list, limit="5000", order_sign_list=[])
        return self._sort(data, 'project.create_time')


# 添加缺失的函数
def get_current_selected_task():
    """获取当前选中的任务信息"""
    try:
        api = CGTeamWorkApi()

        # 获取当前选中信息
        t_database = api.client.client.get_database()
        t_module_type = api.client.client.get_module_type()
        t_id_list = api.client.client.get_id()

        print(t_database, t_module_type, t_id_list)
        if not all([t_database, t_module_type, t_id_list]):
            return {"error": "未选中任何项目或任务"}

        print(f"当前数据库: {t_database}")
        print(f"当前模块: {t_module_type}")
        print(f"选中任务ID: {t_id_list}")

        # 根据模块类型获取任务信息
        if t_module_type == 'task':
            tasks = api.get_task(t_database, t_id_list)
        else:
            return {"error": f"不支持的模块类型: {t_module_type}"}

        if not tasks:
            return {"error": "未找到任务信息"}

        # 获取项目相关信息
        project_drive = api.get_drive_by_project(t_database)
        project_info = api.get_project(t_database)
        project_name = project_info[0].get('project.entity', '') if project_info else t_database

        return {
            "database": t_database,
            "module_type": t_module_type,
            "task_ids": t_id_list,
            "tasks": tasks,
            "project_drive": project_drive,
            "project_name": project_name,
            "success": True
        }

    except Exception as e:
        print(f"获取任务信息时出错: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


def create_maya_project_structure(task_info):
    """根据任务信息创建Maya工程目录结构"""

    def safe_filename(name):
        """将名称转换为安全的文件名"""
        import re
        return re.sub(r'[<>:"/\\|?*]', '_', str(name))

    project_paths = {}

    try:
        tasks = task_info.get('tasks', [])
        if not tasks:
            return {"error": "没有任务信息"}

        task = tasks[0]  # 使用第一个任务
        module_type = task_info.get('module_type')
        project_drive = task_info.get('project_drive', '')
        project_name = task_info.get('project_name', '')

        # 构建基础路径 - 按照示例路径结构
        if module_type == 'task':
            # 镜头任务路径结构: P:\LHSN\shots\s310\c0990\lighting\scenes\
            seq_name = safe_filename(task.get('seq.entity', ''))
            shot_name = safe_filename(task.get('shot.entity', ''))
            task_name = safe_filename(task.get('task.entity', ''))
            pipeline = safe_filename(task.get('pipeline.entity', ''))

            # 根据示例路径修改结构
            base_path = os.path.join(
                project_drive,
                project_name,
                'shots',  # 使用 shots 而不是 scenes/dcc/shot
                seq_name,
                shot_name,
                pipeline
            ).replace('\\', '/')

            project_paths['type'] = 'shot'
            project_paths['seq'] = seq_name
            project_paths['shot'] = shot_name
            project_paths['task'] = task_name
            project_paths['pipeline'] = pipeline

            project_paths['base_path'] = base_path
            project_paths['maya_project_path'] = base_path
            project_paths['scenes_path'] = os.path.join(base_path, 'scenes').replace('\\', '/')
            # 如果不存在scenes_path 路径，则自动创建
            if not os.path.exists(project_paths['scenes_path']):
                os.makedirs(project_paths['scenes_path'])
            return project_paths

    except Exception as e:
        return {"error": f"创建工程目录失败: {e}"}


def create_first_version_maya_scene(task_info, project_paths):
    """创建第一版本的Maya场景文件"""

    try:
        # 生成场景文件名 - 按照示例格式
        module_type = task_info.get('module_type')
        tasks = task_info.get('tasks', [])
        task = tasks[0] if tasks else {}
        project_name = task_info.get('project_name', '')

        filename = f"{project_name}_{project_paths['seq']}_{project_paths['shot']}_{project_paths['pipeline']}_v001.ma"

        # 完整文件路径 - 直接在scenes目录下
        scene_path = os.path.join(project_paths['scenes_path'], filename).replace('\\', '/')

        if os.path.exists(scene_path):
            return {"error": f"场景文件已存在: {scene_path}"}

        # 创建新场景
        cmds.file(new=True, force=True)

        # 添加场景信息节点
        info_node = cmds.createNode('network', name='scene_info')
        cmds.addAttr(info_node, longName='project_name', dataType='string')
        cmds.addAttr(info_node, longName='task_type', dataType='string')
        cmds.addAttr(info_node, longName='created_by', dataType='string')
        cmds.addAttr(info_node, longName='created_date', dataType='string')
        cmds.addAttr(info_node, longName='version', dataType='string')
        cmds.addAttr(info_node, longName='full_path', dataType='string')

        # 设置属性值
        cmds.setAttr(f'{info_node}.project_name', project_name, type='string')
        cmds.setAttr(f'{info_node}.task_type', module_type, type='string')
        cmds.setAttr(f'{info_node}.created_by', os.getenv('USERNAME', 'unknown'), type='string')
        cmds.setAttr(f'{info_node}.created_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), type='string')
        cmds.setAttr(f'{info_node}.version', 'v001', type='string')
        cmds.setAttr(f'{info_node}.full_path', scene_path, type='string')

        # 保存场景
        print(scene_path)
        cmds.file(rename=scene_path)
        cmds.file(save=True)

        print(f"Maya场景创建成功: {scene_path}")

        return {
            "success": True,
            "scene_path": scene_path,
            "filename": filename,
            "project_path": project_paths["maya_project_path"]
        }

    except Exception as e:
        return {"error": f"创建Maya场景失败: {e}"}


def open_path(_path):
    os.startfile(_path)


def save_next_version():
    """保存当前场景的下一个版本"""
    try:
        current_file = cmds.file(query=True, sceneName=True)
        if not current_file:
            print("当前没有打开的场景文件")
            return False

        file_dir = os.path.dirname(current_file)
        file_name = os.path.basename(current_file)

        import re
        match = re.match(r'(.+)_v(\d+)\.mb$', file_name)
        if not match:
            print("文件命名格式不符合版本控制规范")
            return False

        base_name = match.group(1)
        current_version = int(match.group(2))
        next_version = current_version + 1

        new_filename = f"{base_name}_v{next_version:03d}.mb"
        new_filepath = os.path.join(file_dir, new_filename).replace('\\', '/')

        cmds.file(rename=new_filepath)
        cmds.file(save=True, type='mayaBinary')

        print(f"保存新版本成功: {new_filepath}")
        return True

    except Exception as e:
        print(f"保存新版本失败: {e}")
        return False


def create_maya_project_from_task():
    """主函数：从当前选中任务创建Maya工程"""

    print("开始创建Maya工程...")

    # 1. 获取当前选中任务
    task_info = get_current_selected_task()
    if "error" in task_info:
        print(f"错误: {task_info['error']}")
        return False

    print(f"获取到任务信息: {len(task_info.get('tasks', []))} 个任务")

    # 打印任务详细信息
    task = task_info.get('tasks', [{}])[0]
    if task_info.get('module_type') == 'shot':
        print(f"项目: {task_info.get('project_name')}")
        print(f"场次: {task.get('seq.entity')}")
        print(f"镜头: {task.get('shot.entity')}")
        print(f"流程: {task.get('pipeline.entity')}")
        print(f"帧率: {task.get('shot.fps')}")
        print(f"帧范围: {task.get('shot.start_frame')} - {task.get('shot.end_frame')}")

    # 2. 创建工程目录结构
    project_paths = create_maya_project_structure(task_info)
    if "error" in project_paths:
        print(f"错误: {project_paths['error']}")
        return False

    print(f"工程目录创建成功: {project_paths['base_path']}")

    # 3. 创建Maya场景文件
    scene_result = create_first_version_maya_scene(task_info, project_paths)
    if "error" in scene_result:
        print(f"错误: {scene_result['error']}")
        open_path(project_paths['scenes_path'])
        return False

    print(f"Maya场景创建成功: {scene_result['scene_path']}")
    open_path(project_paths['scenes_path'])

    # 4. 打印总结信息
    print("\n=== 工程创建完成 ===")
    print(f"工程路径: {project_paths['base_path']}")
    print(f"场景文件: {scene_result['scene_path']}")
    print(f"Maya工程: {project_paths['maya_project_path']}")
    print(f"文件命名格式: {scene_result['filename']}")

    return True


# 使用示例
if __name__ == '__main__':
    # 导入Maya独立模块
    import maya.standalone

    # 初始化Maya
    maya.standalone.initialize()
    print("Maya standalone 初始化成功")
    try:
        test_api = CGTeamWorkApi()
        print("CGTeamwork 连接成功")
    except Exception as e:
        print(f"CGTeamwork 连接失败: {e}")

    # 创建Maya工程
    success = create_maya_project_from_task()
    if success:
        print("Maya工程创建完成！")
        print("使用 save_next_version() 函数可以保存下一个版本")
    else:
        print("Maya工程创建失败！")
