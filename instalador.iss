; Script de instalación de Inno Setup para tu aplicación
[Setup]
AppName=Monitor de Recursos
AppVersion=1.0
DefaultDirName={pf}\MonitorRecursos
DefaultGroupName=Monitor de Recursos
UninstallDisplayIcon={app}\main.exe
OutputBaseFilename=MonitorRecursosInstaller
Compression=lzma
SolidCompression=yes
DisableProgramGroupPage=yes
OutputDir=dist

[Files]
; Copiar todo el contenido del ejecutable generado por PyInstaller
Source: "dist\MonitorRecursos\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Monitor de Recursos"; Filename: "{app}\main.exe"
Name: "{group}\Desinstalar Monitor de Recursos"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Monitor de Recursos"; Filename: "{app}\main.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Opciones adicionales"

[Run]
Filename: "{app}\main.exe"; Description: "Iniciar Monitor de Recursos"; Flags: nowait postinstall skipifsilent
