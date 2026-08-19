Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "run.bat" & Chr(34), 2, False
Set WshShell = Nothing
