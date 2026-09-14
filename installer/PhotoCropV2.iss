#define AppName "PhotoCropV2"
#define AppPublisher "PhotoCrop"
#define AppExeName "PhotoCropV2.exe"

#ifndef AppVersion
  #error AppVersion must be supplied by build.ps1 using /DAppVersion=x.y.z
#endif

[Setup]
AppId={{76F69A08-DC5C-43EE-A5CD-3130BBF7EF5C}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=PhotoCrop_Setup
SetupIconFile=..\assets\photocrop.ico
UninstallDisplayIcon={app}\{#AppExeName}
LicenseFile=..\LICENSE
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl,JapaneseOverrides.isl"

[CustomMessages]
english.DesktopShortcut=Create a desktop shortcut
english.AdditionalShortcuts=Additional shortcuts:
english.LaunchApp=Launch {#AppName}
french.DesktopShortcut=Créer un raccourci sur le Bureau
french.AdditionalShortcuts=Raccourcis supplémentaires :
french.LaunchApp=Lancer {#AppName}
japanese.DesktopShortcut=デスクトップにショートカットを作成する
japanese.AdditionalShortcuts=追加のショートカット：
japanese.LaunchApp={#AppName} を起動する

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopShortcut}"; GroupDescription: "{cm:AdditionalShortcuts}"; Flags: unchecked

[Files]
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\PhotoCrop\PhotoCropV2"; ValueType: string; ValueName: "language"; ValueData: "{code:InitialLanguage}"; Flags: createvalueifdoesntexist uninsdeletevalue

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent

[Code]
function PreferredJapaneseFont: String;
begin
  if FontExists('Yu Gothic UI') then
    Result := 'Yu Gothic UI'
  else if FontExists('Meiryo UI') then
    Result := 'Meiryo UI'
  else if FontExists('MS UI Gothic') then
    Result := 'MS UI Gothic'
  else
    Result := 'Segoe UI';
end;

procedure InitializeWizard;
var
  JapaneseFont: String;
begin
  if ActiveLanguage = 'japanese' then
  begin
    JapaneseFont := PreferredJapaneseFont;
    WizardForm.Font.Name := JapaneseFont;
    WizardForm.WelcomeLabel1.Font.Name := JapaneseFont;
    WizardForm.WelcomeLabel2.Font.Name := JapaneseFont;
    WizardForm.PageNameLabel.Font.Name := JapaneseFont;
    WizardForm.PageDescriptionLabel.Font.Name := JapaneseFont;
  end;
end;

function InitialLanguage(Param: String): String;
begin
  if ActiveLanguage = 'japanese' then
    Result := 'ja'
  else if ActiveLanguage = 'french' then
    Result := 'fr'
  else
    Result := 'en';
end;
