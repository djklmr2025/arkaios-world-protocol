' Runs the Educación Libre -> task board bridge once, in the background (no window).
' Meant for a Windows scheduled task. Log: <repo>\.local-world\edu-sync.log (appended).
Set fso = CreateObject("Scripting.FileSystemObject")
repo = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
py = repo & "\.venv-pilot\Scripts\python.exe"
If Not fso.FileExists(py) Then WScript.Quit 1
If Not fso.FolderExists(repo & "\.local-world") Then WScript.Quit 1
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = repo
sh.Environment("PROCESS")("PYTHONUTF8") = "1"
sh.Run "cmd /c ""echo [%date% %time%] >> .local-world\edu-sync.log & """ & py & """ world\edu_inbox_bridge.py >> .local-world\edu-sync.log 2>&1""", 0, True
