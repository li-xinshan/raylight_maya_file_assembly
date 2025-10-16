"""
Lookdev动画组装工具 Maya插件 - 精简版UI模块
版本：2.0 (重构版)
作者：Maya Pipeline Team

"""

import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMayaMPx as omm
import os
import sys

# 使用inspect模块获取脚本路径
import inspect

# 获取当前脚本路径
try:
    current_script = inspect.getfile(inspect.currentframe())
    SCRIPT_DIR = os.path.dirname(os.path.abspath(current_script))
except:
    # 如果inspect失败，尝试其他方法
    try:
        # 尝试从__file__获取
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    except:
        # 最后使用当前工作目录
        SCRIPT_DIR = os.getcwd()
        print(f"⚠️  使用当前工作目录: {SCRIPT_DIR}")

# 添加脚本目录到Python路径
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# 导入模块
try:
    from core.core_assembler import CoreAssembler
    from ui.ui_components import UIComponents  
    from ui.ui_event_handlers import UIEventHandlers
    from ui.ui_utils import UIUtils
    print(f"✅ 模块导入成功，脚本路径: {SCRIPT_DIR}")
except ImportError as e:
    import traceback
    print(traceback.format_exc())
    print(f"❌ 导入模块失败: {e}")
    print(f"当前脚本路径: {SCRIPT_DIR}")
    CoreAssembler = UIComponents = UIEventHandlers = UIUtils = None


class LookdevAnimationSetupUI:
    """
    Lookdev和动画组装工具 - 精简版UI界面
    """

    def __init__(self, config_file=None):
        # 窗口配置
        self.window_name = "LookdevAnimationSetup"
        self.window_title = "Lookdev动画组装工具 v3.0"
        
        # UI控件变量
        self.ui = {}
        
        # 初始化核心组装器
        self.core = CoreAssembler(config_file)
        
        # 当前资产状态
        self.current_asset = None
        self.available_assets = []
        
        # 项目扫描数据
        self.project_shots = {}
        self.current_shot_key = None
        
        # UI折叠状态记忆
        self.section_collapse_states = {
            'config': False,    # 配置设置 - 默认展开
            'settings': True,   # 参数设置 - 默认收缩
            'execution': True, # 执行操作 - 默认收缩
            'status': False,    # 状态信息 - 默认展开
            'tools': True       # 附加工具 - 默认收缩
        }

        # 初始化UI模块
        self.event_handler = UIEventHandlers(self)
        self.ui_components = UIComponents(self.ui, self.event_handler)
        self.ui_utils = UIUtils(self.ui)

    def show_ui(self):
        """显示UI界面"""
        # 创建主窗口
        self.ui_components.create_main_window(self.window_name, self.window_title)

        # 创建各个区域
        self.ui_components.create_config_section(self.section_collapse_states)
        self.ui_components.create_settings_section(self.section_collapse_states)
        self.ui_components.create_execution_section(self.section_collapse_states)
        self.ui_components.create_status_section(self.section_collapse_states)
        self.ui_components.create_tools_section(self.section_collapse_states)

        # 显示窗口
        cmds.showWindow(self.ui['window'])
        
        # 调整窗口大小限制
        cmds.window(self.ui['window'], edit=True, widthHeight=(520, 800))

        # 更新初始状态
        self.update_asset_list()
        
        # 异步启动项目扫描（避免阻塞UI）
        cmds.evalDeferred(self.event_handler.scan_project_shots)

    # ===== UI更新方法（委托给UI工具类） =====

    def update_asset_list(self):
        """更新资产列表"""
        assets_data = self.core.config_manager.get_assets_data()
        count = self.ui_utils.update_asset_list(assets_data)
        if count > 0:
            self.log_message(f"已加载 {count} 个资产配置")

    def update_asset_info(self):
        """更新资产信息显示"""
        self.ui_utils.update_asset_info(self.core)

    def update_namespace(self):
        """更新命名空间显示"""
        self.ui_utils.update_namespace(self.core)

    def update_shot_list(self):
        """更新场次镜头列表"""
        self.ui_utils.update_shot_list(self.project_shots)

    def update_progress(self, value):
        """更新进度条"""
        self.ui_utils.update_progress(value)

    def update_button_state(self, button_name, success):
        """更新按钮状态"""
        self.ui_utils.update_button_state(button_name, success)

    def reset_button_states(self):
        """重置所有按钮状态"""
        self.ui_utils.reset_button_states()

    def log_message(self, message):
        """添加日志消息"""
        self.ui_utils.log_message(message)

    # ===== 配置加载内部方法 =====

    def _load_shot_config_internal(self, shot_key, shot_data):
        """内部方法：加载场次镜头配置"""
        try:
            # 提取场次和镜头
            sequence, shot = shot_key.split('_')
            
            # 检查是否已经有从JSON配置文件加载的数据
            current_assets = self.core.config_manager.get_assets_data()
            has_preloaded_config = current_assets and len(current_assets) > 0
            
            if has_preloaded_config:
                # 如果已有配置数据，直接使用
                print(f"✅ 使用已有的预配置数据 ({len(current_assets)} 个资产)")
                success = True
            else:
                # 没有预配置数据时，才使用扫描数据创建配置
                print(f"⚠️  未找到预配置数据，从项目扫描数据创建配置")
                success = self.core.config_manager.create_config_from_shot_data(
                    sequence, shot, None, self.project_shots
                )
            
            if success:
                # 更新UI
                self.update_asset_list()
                
                # 更新状态指示器
                self.ui_utils.update_config_status(True)
                
                # 显示配置信息
                assets_data = self.core.config_manager.get_assets_data()
                info_text = self.ui_utils.format_asset_display_info(shot_key, assets_data)
                cmds.scrollField(self.ui['asset_info'], edit=True, text=info_text)
                
                self.log_message(f"✅ 已自动加载 {sequence}_{shot} 配置，包含 {len(assets_data)} 个资产")
                
            else:
                self.log_message(f"❌ 加载 {shot_key} 配置失败")
                self.ui_utils.update_config_status(False)
                
        except Exception as e:
            self.log_message(f"❌ 加载配置时出错: {str(e)}")
            self.ui_utils.update_config_status(False)


# ===== 插件功能函数 =====

def show_lookdev_animation_setup_ui(config_file=None, *args):
    """显示Lookdev动画组装工具UI"""
    ui = LookdevAnimationSetupUI(config_file)
    ui.show_ui()
    return ui


def quick_setup_lookdev_animation(*args):
    """快速设置Lookdev动画"""
    selected = cmds.ls(selection=True)
    if len(selected) >= 2:
        core = CoreAssembler()
        cmds.headsUpMessage("快速设置功能开发中...")
    else:
        cmds.warning("请选择Lookdev文件和ABC文件")


def get_time_from_selected_abc(*args):
    """从选择的ABC文件获取时间范围"""
    selected = cmds.ls(selection=True)
    if selected:
        abc_nodes = [node for node in selected if cmds.nodeType(node) == "AlembicNode"]
        if abc_nodes:
            abc_node = abc_nodes[0]
            start_frame = cmds.getAttr(f"{abc_node}.startFrame")
            end_frame = cmds.getAttr(f"{abc_node}.endFrame")

            cmds.playbackOptions(min=start_frame, max=end_frame)
            cmds.currentTime(start_frame)

            cmds.headsUpMessage(f"时间范围已设置: {start_frame} - {end_frame}")
        else:
            cmds.warning("请选择ABC节点")
    else:
        cmds.warning("请选择ABC节点")


# ===== 插件初始化和清理 =====

def initializePlugin(mobject):
    """Initialize the script plug-in"""
    mplugin = omm.MFnPlugin(mobject, "LookdevAnimationTools", "3.0", "any")

    # 删除已存在的菜单
    if cmds.menu("menuRaylight", exists=True):
        cmds.deleteUI("menuRaylight", menu=True)

    # 获取主窗口
    gMainWindow = mel.eval("global string $gMainWindow;$temp = $gMainWindow")

    # 创建主菜单 - Raylight
    raylight_menu = cmds.menu("menuRaylight",
                             label="Raylight",
                             parent=gMainWindow,
                             tearOff=True)

    # 创建Light子菜单
    light_submenu = cmds.menuItem(label="Light", subMenu=True, parent=raylight_menu)

    # 在Light子菜单中添加Lookdev动画工具
    cmds.menuItem(label="Lookdev动画组装工具",
                  command=show_lookdev_animation_setup_ui,
                  annotation="打开Lookdev动画组装工具主界面",
                  parent=light_submenu)

    cmds.menuItem(label="Lookdev工具 (带配置)",
                  command=lambda x: show_lookdev_animation_setup_ui("example_config.json"),
                  annotation="打开主界面并加载示例配置",
                  parent=light_submenu)

    cmds.menuItem(divider=True, parent=light_submenu)

    cmds.menuItem(label="快速设置",
                  command=quick_setup_lookdev_animation,
                  annotation="快速设置Lookdev和动画",
                  parent=light_submenu)

    cmds.menuItem(label="从ABC获取时间",
                  command=get_time_from_selected_abc,
                  annotation="从选择的ABC节点获取时间范围",
                  parent=light_submenu)

    cmds.menuItem(divider=True, parent=light_submenu)

    # Light工具子菜单
    light_tools_submenu = cmds.menuItem(label="工具", subMenu=True, parent=light_submenu)

    cmds.menuItem(label="播放动画",
                  command=lambda x: cmds.play(forward=True),
                  annotation="播放动画",
                  parent=light_tools_submenu)

    cmds.menuItem(label="停止动画",
                  command=lambda x: cmds.play(state=False),
                  annotation="停止动画",
                  parent=light_tools_submenu)

    cmds.menuItem(label="适配视图",
                  command=lambda x: (cmds.select(all=True), cmds.viewFit(), cmds.select(clear=True)),
                  annotation="适配视图到所有对象",
                  parent=light_tools_submenu)

    cmds.menuItem(divider=True, parent=light_tools_submenu)

    cmds.menuItem(label="选择ABC节点",
                  command=lambda x: cmds.select(cmds.ls(type="AlembicNode")) if cmds.ls(
                      type="AlembicNode") else cmds.warning("没有ABC节点"),
                  annotation="选择场景中的所有ABC节点",
                  parent=light_tools_submenu)

    # Light帮助子菜单
    light_help_submenu = cmds.menuItem(label="帮助", subMenu=True, parent=light_submenu)

    cmds.menuItem(label="关于",
                  command=lambda x: cmds.confirmDialog(
                      title="关于",
                      message="Raylight Lookdev动画组装工具 v3.0\n\n• 模块化重构版\n• 支持批量导入\n• 智能相机处理\n• 文件保存检查\n\nPowered by Raylight Pipeline",
                      button=["确定"]),
                  annotation="显示关于信息",
                  parent=light_help_submenu)

    cmds.menuItem(label="使用说明",
                  command=lambda x: cmds.confirmDialog(
                      title="使用说明",
                      message="Raylight Lookdev工具使用说明：\n\n✅ 支持批量资产导入\n✅ 智能相机处理避免重复\n✅ 执行前文件保存检查\n✅ 支持chr/prp资产分类\n\n详细说明请查看主界面的帮助菜单。",
                      button=["确定"]),
                  annotation="显示使用说明",
                  parent=light_help_submenu)

    print("Raylight Lookdev动画工具插件已加载 v3.0")


def uninitializePlugin(mobject):
    """Uninitialize the script plug-in"""
    if cmds.menu("menuRaylight", exists=True):
        cmds.deleteUI("menuRaylight", menu=True)

    print("Raylight Lookdev动画工具插件已卸载")


# 主函数
def main():
    """主函数 - 用于直接运行脚本"""
    return show_lookdev_animation_setup_ui()


# 如果直接运行此脚本
if __name__ == "__main__":
    show_lookdev_animation_setup_ui()