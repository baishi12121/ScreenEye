; ScreenEye 安装包脚本（Inno Setup 6）
; 编译：在已安装 Inno Setup 的机器上执行
;     ISCC.exe installer\CareUEyes.iss
; 产物：installer\ScreenEye_Setup.exe
;
; 设计要点：
; - 单文件 exe（dist\ScreenEye.exe）整体拷入 {app}
; - 每用户安装到 LocalAppData\Programs，无需管理员权限（与“开机自启写 HKCU”一致）
; - 仅 64 位（程序依赖 Windows API / ctypes，且用 64 位 Python 打包）
; - SetupIconFile 复用应用图标 resources\app.ico
; - 中文 + 英文安装界面（随系统区域自动切换）

#define MyAppName "屏间护目 ScreenEye"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ScreenEye"
#define MyAppURL ""
#define MyAppExeName "ScreenEye.exe"

[Setup]
; 应用唯一标识（用于升级/卸载登记）
AppId={{A1B2C3D4-0001-4E59-8F00-CAREUEYES0001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

; 安装位置：每用户 Program Files 替代目录，免管理员
DefaultDirName={localappdata}\Programs\ScreenEye
DefaultGroupName=ScreenEye
; 单文件 exe 直接放 {app}
OutputDir=.
OutputBaseFilename=ScreenEye_Setup
SetupIconFile=..\resources\app.ico

; 权限：无需管理员（写 LocalAppData / HKCU）
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
UsedUserAreasWarning=no

; 架构：仅 64 位
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os

; 行为/外观
WizardStyle=modern
SetupLogging=yes
Compression=lzma2
SolidCompression=yes
; 关闭“以管理员身份运行此安装程序”的 UAC 提示带来的程序兼容模式干扰
ChangesEnvironment=no
; 卸载时显示程序图标
UninstallDisplayIcon={app}\{#MyAppExeName}
; 允许不创建开始菜单文件夹
AllowNoIcons=yes
; 防止重复运行安装向导
SetupMutex=ScreenEyeSetupMutex

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式设置:"; Flags: unchecked

[Files]
; 单文件 exe 整体安装（无外部依赖）
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; 紧急复位脚本（进程被强杀后屏幕色彩未恢复时，双击即可恢复默认）
Source: "reset_gamma.bat"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\恢复屏幕默认色彩"; Filename: "{app}\reset_gamma.bat"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
