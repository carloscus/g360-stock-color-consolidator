Set WshShell = WScript.CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
strDesktop = WshShell.SpecialFolders("Desktop")
strAppDir = FSO.GetParentFolderName(WScript.ScriptFullName)
strShortcut = strDesktop & "\G360 Stock Color Consolidator.lnk"

' Remove existing shortcut
If FSO.FileExists(strShortcut) Then FSO.DeleteFile(strShortcut)

Set oShortcut = WshShell.CreateShortcut(strShortcut)
oShortcut.TargetPath = strAppDir & "\run.bat"
oShortcut.WorkingDirectory = strAppDir
oShortcut.Description = "G360 - Stock Color Consolidator"
oShortcut.WindowStyle = 1 ' Normal

' Set icon from app assets
strIcon = strAppDir & "\assets\images\favicon.ico"
If FSO.FileExists(strIcon) Then
    oShortcut.IconLocation = strIcon & ", 0"
Else
    oShortcut.IconLocation = "shell32.dll, 1"
End If

oShortcut.Save
