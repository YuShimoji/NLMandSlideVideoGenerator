# PowerShell実行ポリシーを変更（初回のみ）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# その後、プロジェクトフォルダで実行
.\emergency_fix.ps1
