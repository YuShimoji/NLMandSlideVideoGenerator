param([string]$FilePath, [string]$SearchTerm, [int]$ContextBytes = 400)

# Register Shift-JIS encoding
[System.Text.Encoding]::RegisterProvider([System.Text.CodePagesEncodingProvider]::Instance)
$sjis = [System.Text.Encoding]::GetEncoding(932)

$searchBytesUTF8 = [System.Text.Encoding]::UTF8.GetBytes($SearchTerm)
$fileBytes = [System.IO.File]::ReadAllBytes($FilePath)

Write-Output "=== Searching $FilePath for '$SearchTerm' (decoding as Shift-JIS) ==="

$found = 0
for ($i = 0; $i -lt $fileBytes.Length - $searchBytesUTF8.Length; $i++) {
    $match = $true
    for ($j = 0; $j -lt $searchBytesUTF8.Length; $j++) {
        if ($fileBytes[$i + $j] -ne $searchBytesUTF8[$j]) { $match = $false; break }
    }
    if ($match) {
        $found++
        $start = [Math]::Max(0, $i - $ContextBytes)
        $end = [Math]::Min($fileBytes.Length, $i + $searchBytesUTF8.Length + $ContextBytes)
        $chunk = New-Object byte[] ($end - $start)
        [Array]::Copy($fileBytes, $start, $chunk, 0, $end - $start)
        $decoded = $sjis.GetString($chunk)
        $cleaned = $decoded -replace '[\x00-\x08\x0B\x0C\x0E-\x1F]', '.'
        Write-Output ""
        Write-Output "--- Match #$found at offset $i ---"
        Write-Output $cleaned
        Write-Output ""
    }
}

Write-Output "Total matches: $found"
