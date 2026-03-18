# Windows-Linux File Bridge

一个面向 Windows 与 WSL Linux 高频文件交换场景的轻量桌面工具。它不是通用文件管理器，而是把跨系统传输、整理和常见管理动作做得更直接、更安全。

## 当前版本亮点

- 双栏工作区：左侧 Windows，右侧 Linux
- 传输中心：明确区分 `发送到 Linux` 和 `发送到 Windows`
- 顶部状态卡：显示当前发行版、两侧面板状态、最近结果
- 列表式文件视图：名称、类型、修改时间、大小一目了然
- 右键快捷操作：重命名、打开所在位置、查看属性、新建文件夹、删除
- 搜索、排序、类型筛选
- 传输历史记录与失败重试
- 独立“操作记录”二级窗口，避免主界面过于拥挤
- 更易拖拽的滚动条和更稳定的弹窗居中体验
- 无控制台窗口启动

## 适用场景

- 在 Windows 桌面目录和 WSL 项目目录之间来回搬运文件
- 传输文档、图片、代码、压缩包等常见资料
- 快速整理 Linux 侧目录，而不必手动切换命令行和资源管理器
- 处理临时文件交换，不希望引入更重的同步工具

## 功能说明

### 1. 双向传输

- 支持 Windows -> Linux
- 支持 Linux -> Windows
- 支持文件和文件夹
- 同名冲突自动重命名，保留两份
- `.lnk` 与 `.url` 快捷方式默认跳过，不参与传输

### 2. 双栏浏览

- 双击文件夹进入目录
- 顶部路径框可直接查看当前目录
- 支持“选择目录”和“上级”
- Linux 路径通过 `\\wsl$\发行版名\...` 访问

### 3. 文件管理

- 搜索文件名
- 按名称、修改时间排序
- 按文件类型筛选
- 新建文件夹
- 删除所选
- 重命名
- 打开所在位置
- 查看属性

### 4. 操作记录

- 所有传输、删除、重命名、新建文件夹操作都会写入历史
- 历史记录在“查看操作记录”二级窗口中展示
- 失败记录支持直接重试
- 最近一次结果会同步显示在主界面顶部状态卡

## 默认过滤规则

- `.lnk`、`.url` 快捷方式默认隐藏，也不会参与传输
- `~$` 开头的 Office 临时文件默认隐藏
- `desktop.ini` 默认隐藏
- “文件夹”筛选仅显示目录
- 其他类型筛选仅显示匹配文件，不混入文件夹

## 运行方式

直接双击：

- `start_gui.vbs`

或在命令行运行：

```powershell
python wsl_file_bridge_gui.py
```

## 打包 EXE

仓库已提供 `PyInstaller` 打包脚本：

```powershell
build_exe.bat
```

当前常用产物：

- 单文件版：`dist_pyinstaller_onefile\WindowsLinuxFileBridge-OneFile.exe`
- 目录版：`dist_pyinstaller\WindowsLinuxFileBridge\WindowsLinuxFileBridge.exe`

推荐优先分发单文件版。

## 项目结构

- `wsl_file_bridge_gui.py`：主程序
- `start_gui.vbs`：无控制台启动入口
- `build_exe.bat`：PyInstaller 打包脚本
- `DESIGN_PLAN.md`：设计规划与迭代记录
- `RELEASE_NOTES.md`：GitHub Release 文案模板
- `assets/app_icon.ico`：应用图标
- `assets/app_icon_preview.png`：图标预览

## 已知限制

- 拖拽能力依赖 `tkinterdnd2`，未安装时会自动降级
- 当前仍为 Tkinter 版本，目标是轻量高效，不是完整资源管理器
- 主要面向 Windows + WSL 的本地文件交换场景

## License

本项目采用 [MIT License](LICENSE)。
