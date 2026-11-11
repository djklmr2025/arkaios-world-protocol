' Scheduled-task entry point (no window):
'   1. Watchdog: if the world does not answer on 127.0.0.1:4300, start it (start-hidden.vbs;
'      a second instance exits on the state-dir lock, so this is safe to repeat).
'   2. Runs the Educación Libre -> task board bridge once.
' Logs: <repo>\.local-world\edu-sync.log and server.log (appended).
Set fso = CreateObject("Scripting.FileSystemObject")
repo = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
py = repo & "\.venv-pilot\Scripts\python.exe"
If Not fso.FileExists(py) Then WScript.Quit 1
If Not fso.FolderExists(repo & "\.local-world") Then WScript.Quit 1
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = repo

Function WorldUp()
    WorldUp = False
    On Error Resume Next
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    http.setTimeouts 2000, 2000, 3000, 3000
    http.Open "GET", "http://127.0.0.1:4300/api/version", False
    http.Send
    If Err.Number = 0 Then WorldUp = (http.Status = 200)
    On Error GoTo 0
End Function

Sub Log(text)
    Set f = fso.OpenTextFile(repo & "\.local-world\edu-sync.log", 8, True)
    f.WriteLine "[" & Now & "] " & text
    f.Close
End Sub

If Not WorldUp() Then
    Log "ARKAIOS World no respondia en :4300; arrancandolo."
    sh.Run "wscript.exe //B """ & repo & "\world\start-hidden.vbs""", 0, False
    For i = 1 To 10
        WScript.Sleep 1000
        If WorldUp() Then Exit For
    Next
    If Not WorldUp() Then
        Log "ARKAIOS World sigue sin responder; ver .local-world\server.log"
        WScript.Quit 1
    End If
End If

sh.Environment("PROCESS")("PYTHONUTF8") = "1"
sh.Run "cmd /c ""echo [%date% %time%] >> .local-world\edu-sync.log & """ & py & """ world\edu_inbox_bridge.py >> .local-world\edu-sync.log 2>&1""", 0, True
