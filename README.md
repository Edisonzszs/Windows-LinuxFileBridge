# Windows-Linux File Bridge

一个面向 Windows 和 WSL Linux 之间高频传输场景的桌面小工具。

它的目标不是做一个复杂文件管理器，而是把最常见的跨系统资料传输做得更顺手、更安全、更像一个真正能日常使用的工具。

## Features

- Windows 和 Linux 双栏目录浏览
- 双向手动传输，支持文件和文件夹
- 同名冲突自动重命名，保留两份
- 传输时自动忽略快捷方式文件（`.lnk`、`.url`）
- 默认隐藏 Office 临时文件（`~$` 开头）和 `desktop.ini`
- 文件类型筛选：文件夹、文档、图片、压缩包、代码、媒体、数据、安装镜像
- 搜索、排序、右键菜单、新建文件夹
- 删除前二次确认
- 历史记录与失败重试
- 无控制台窗口启动

## Run

### Option 1

双击 `start_gui.vbs`

### Option 2

在项目目录执行：

```powershell
python wsl_file_bridge_gui.py
```

## Usage

1. 左侧选择 Windows 目录，右侧选择 Linux 目录。
2. 在任一侧选中文件或文件夹。
3. 点击 `发送到 Linux` 或 `发送到 Windows`。
4. 如需管理文件，可使用右键菜单执行重命名、查看属性、新建文件夹或删除。

## Filter Rules

- `全部文件`：显示正常文件和文件夹
- `文件夹`：只显示目录
- `媒体文件`、`数据文件` 等具体类型：只显示匹配文件，不混入文件夹
- `.lnk`、`.url`：默认隐藏且不会参与传输
- `~$` 开头文件、`desktop.ini`：默认隐藏

## WSL Path Notes

- Linux 路径通过 `\\wsl$\发行版` 访问
- 默认发行版是 `Ubuntu-24.04`
- 可在界面顶部修改发行版名称

## Build EXE

仓库提供了打包脚本 `build_exe.bat`。

安装 `PyInstaller` 后可执行：

```powershell
build_exe.bat
```

默认会输出到 `dist\WindowsLinuxFileBridge\`。

## Project Files

- `wsl_file_bridge_gui.py`: 主程序
- `start_gui.vbs`: 无黑窗启动器
- `DESIGN_PLAN.md`: 设计规划

## Limitations

- 当前拖拽功能依赖 `tkinterdnd2`，未安装时会自动降级
- 当前仍是 Tkinter 版本，界面偏轻量，不是完整资源管理器

## License

当前仓库尚未添加许可证文件；如果你愿意，下一步建议补一个 `MIT` License。
