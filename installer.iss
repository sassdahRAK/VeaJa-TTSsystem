[Setup]
AppName=Veaja
AppVersion=1.0
AppPublisher=Veaja
AppPublisherURL=https://github.com/sassdahRAK/VeaJa-TTSsystem
DefaultDirName={autopf}\Veaja
DefaultGroupName=Veaja
OutputDir=installer_output
OutputBaseFilename=Veaja_Setup
SetupIconFile=assets\veaja.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Files]
Source: "dist\Veaja\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Veaja"; Filename: "{app}\Veaja.exe"; IconFilename: "{app}\Veaja.exe"
Name: "{commondesktop}\Veaja"; Filename: "{app}\Veaja.exe"; IconFilename: "{app}\Veaja.exe"

[Run]
Filename: "{app}\Veaja.exe"; Description: "Launch Veaja"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
