' Starts the ARKAIOS reference world in the background (no window), loopback only.
' Log: <repo>\.local-world\server.log (appended).
' If another instance already owns the state dir, this one exits on the OS lock.
Set fso = CreateObject("Scripting.FileSystemObject")
repo = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
py = repo & "\.venv-pilot\Scripts\python.exe"
If Not fso.FileExists(py) Then WScript.Quit 1
If Not fso.FolderExists(repo & "\.local-world") Then WScript.Quit 1
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = repo
sh.Run "cmd /c """"" & py & """ world\server.py serve --state .local-world --port 4300 >> .local-world\server.log 2>&1""", 0, False
