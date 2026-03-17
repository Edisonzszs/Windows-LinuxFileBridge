Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
scriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
pythonw = WshShell.ExpandEnvironmentStrings("%LocalAppData%") & "\\Programs\\Python\\Python313\\pythonw.exe"
pythonAlt = WshShell.ExpandEnvironmentStrings("%LocalAppData%") & "\\Programs\\Python\\Python312\\pythonw.exe"
pythonAlt2 = WshShell.ExpandEnvironmentStrings("%LocalAppData%") & "\\Programs\\Python\\Python311\\pythonw.exe"

If FSO.FileExists(pythonw) Then
  py = pythonw
ElseIf FSO.FileExists(pythonAlt) Then
  py = pythonAlt
ElseIf FSO.FileExists(pythonAlt2) Then
  py = pythonAlt2
Else
  py = "pythonw"
End If

cmd = Chr(34) & py & Chr(34) & " " & Chr(34) & scriptDir & "\\wsl_file_bridge_gui.py" & Chr(34)
WshShell.Run cmd, 0, False
