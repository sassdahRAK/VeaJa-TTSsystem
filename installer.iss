[Setup]
AppName=Veaja
AppVersion=1.1.0
AppPublisher=Veaja
AppPublisherURL=https://github.com/sassdahRAK/VeaJa-TTSsystem
AppSupportURL=https://github.com/sassdahRAK/VeaJa-TTSsystem/issues
AppUpdatesURL=https://github.com/sassdahRAK/VeaJa-TTSsystem/releases
DefaultDirName={autopf}\Veaja
DefaultGroupName=Veaja
OutputDir=installer_output
OutputBaseFilename=Veaja_Setup_1.1.0
SetupIconFile=assets\veaja.ico
UninstallDisplayIcon={app}\Veaja.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
DisableProgramGroupPage=yes

; Allow upgrading over an existing install without uninstalling first
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "dist\Veaja\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Veaja"; Filename: "{app}\Veaja.exe"; IconFilename: "{app}\Veaja.exe"
Name: "{group}\Uninstall Veaja"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Veaja"; Filename: "{app}\Veaja.exe"; IconFilename: "{app}\Veaja.exe"; Tasks: desktopicon

[Registry]
; Add to Windows "Apps & features" / "Add or Remove Programs"
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\Veaja.exe"; ValueType: string; ValueName: ""; ValueData: "{app}\Veaja.exe"; Flags: uninsdeletekey

[Run]
Filename: "{app}\Veaja.exe"; Description: "Launch Veaja"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
