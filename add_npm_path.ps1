$npmPath = "C:\Users\User\AppData\Roaming\npm"
$current = [Environment]::GetEnvironmentVariable("Path", "User")
$entries = $current -split ";"
if ($entries -contains $npmPath) {
    Write-Host "Already in PATH"
} else {
    [Environment]::SetEnvironmentVariable("Path", ($current + ";" + $npmPath), "User")
    Write-Host "Added to user PATH"
}
