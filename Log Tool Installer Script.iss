[Setup]
AppName=Hoverfly Tech Log Tool
AppVersion=1.0
WizardStyle=modern
DefaultDirName={autopf}\Hoverfly Log Tool
DefaultGroupName=HF Log Tool
UninstallDisplayIcon={app}\HF LogTool.exe
Compression=lzma2
SolidCompression=yes
OutputDir=C:\Users\18636\Desktop

[Files]
Source: "DFParser.exe"; DestDir: "{app}"
Source: "Loading.gif"; DestDir: "{app}"
Source: "LogMinion.jar"; DestDir: "{app}"
Source: "LogTool.exe"; DestDir: "{app}"
Source: "Hoverfly-Tech.ico"; DestDir: "{app}"
#define JavaInstaller "jdk-15.0.1_windows-x64_bin.exe"
Source: "{#JavaInstaller}"; DestDir: "{tmp}";

[Icons]
Name: "{group}\Hoverfly Log Tool"; Filename: "{app}\LogTool.exe"; IconFilename: "{app}\Hoverfly-Tech.ico"
Name: "{commondesktop}\Hoverfly Log Tool"; Filename: "{app}\LogTool.exe"; Tasks: desktopicon; IconFilename: "{app}\Hoverfly-Tech.ico"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Code]
const
  REQUIRED_JAVA_VERSION = '15.0.1';

function isJavaInstalled(): Boolean;
var
  JavaVer: String;
  tmpFileName,
  pathJavaExe: String;
  isGoodJavaVersion,
  isFoundJavaPath: Boolean;
  ResultCode: Integer;
  ExecStdout: AnsiString;
begin

  if RegQueryStringValue(HKLM, 'SOFTWARE\JavaSoft\JDK',
           'CurrentVersion', JavaVer) AND (JavaVer <> '') OR
     RegQueryStringValue(HKLM64, 'SOFTWARE\JavaSoft\JDK',
           'CurrentVersion', JavaVer) AND (JavaVer <> '') then begin
    Log('* Java Entry in Registry present. Version: ' + JavaVer);
    isGoodJavaVersion := CompareStr(JavaVer, REQUIRED_JAVA_VERSION) >= 0;
  end;

  Result := isGoodJavaVersion;
end;

[Run]
; Filename: "https://www.oracle.com/java/technologies/javase-downloads.html"; Flags: shellexec runasoriginaluser
Filename: "{tmp}\{#JavaInstaller}"; Parameters: "SPONSORS=0"; StatusMsg: "Java Runtime Enviroment not installed on your system. Installing..."; Check: not isJavaInstalled