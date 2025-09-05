# Maya 使用说明

## 在Maya中使用此工具

### 方式1: 直接运行脚本文件
```python
# 在Maya Script Editor中运行
execfile("/path/to/raylight_maya_file_assembly/maya_assembler.py")
```

### 方式2: 添加到Python路径后导入
```python
import sys
sys.path.append("/path/to/raylight_maya_file_assembly")
import maya_assembler
maya_assembler.show_lookdev_animation_setup_ui()
```

### 方式3: 作为Maya插件加载
1. 将整个目录复制到Maya的scripts或plug-ins目录
2. 在Maya中运行：
```python
import maya_assembler
maya_assembler.show_lookdev_animation_setup_ui()
```

## 目录说明

- `maya_assembler.py` - Maya插件主入口文件
- `ui/` - UI界面相关模块  
- `core/` - 核心逻辑模块
- `managers/` - 各功能管理器模块
- `utils/` - 工具函数模块
- `config/` - 配置管理模块

## 注意事项

- 确保Maya能访问项目目录
- 所有依赖的模块都在子目录中，保持目录结构完整
- 只有`maya_assembler.py`是主入口文件，其他文件都是模块支持