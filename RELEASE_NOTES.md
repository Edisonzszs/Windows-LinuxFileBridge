# GitHub Release 模板

这是一份可以直接粘贴到 GitHub Release 页面的说明稿，按当前项目状态整理。

## 建议版本标题

`v1.0.0 - First Public Release`

## 建议上传附件

- `WindowsLinuxFileBridge-OneFile.exe`：推荐大多数用户下载
- `WindowsLinuxFileBridge.zip`：可选，适合保留目录版完整结构

## 发布说明

Windows-Linux File Bridge 是一个面向 Windows 与 WSL Linux 文件交换场景的轻量桌面工具，提供双栏浏览和手动双向传输能力，适合日常文档、资料、项目文件在两个系统之间快速流转。

### 本版本包含

- Windows / Linux 双栏目录浏览
- 支持文件与文件夹双向传输
- 同名冲突自动重命名，保留两份
- 搜索、排序、文件类型筛选
- 删除、重命名、查看属性、新建文件夹
- 传输历史记录与失败重试
- 默认隐藏快捷方式、Office 临时文件和常见系统文件
- 提供可直接运行的 Windows EXE 打包版本

### 推荐下载

普通使用场景推荐优先下载 `WindowsLinuxFileBridge-OneFile.exe`。

### 说明

- 当前版本主要面向 Windows + WSL 使用场景
- 拖拽能力后续还可以继续增强
- 当前界面追求轻量和实用，不是完整文件管理器
