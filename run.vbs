Set oShell = CreateObject ("Wscript.Shell")
Dim strArgs
strArgs = "cmd /c runbat.bat"
oShell.run strArgs, 0, false