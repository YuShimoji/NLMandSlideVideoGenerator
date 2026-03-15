param([string]$FilePath, [string]$SearchTerm, [int]$ContextBytes = 200)

$searchBytesUTF8 = [System.Text.Encoding]::UTF8.GetBytes($SearchTerm)
$searchBytesU16 = [System.Text.Encoding]::Unicode.GetBytes($SearchTerm)
$fileBytes = [System.IO.File]::ReadAllBytes($FilePath)

Write-Output "=== Searching $FilePath for '$SearchTerm' ==="
Write-Output "File size: $($fileBytes.Length) bytes"

# Search UTF-8
for ($i = 0; $i -lt $fileBytes.Length - $searchBytesUTF8.Length; $i++) {
    $match = $true
    for ($j = 0; $j -lt $searchBytesUTF8.Length; $j++) {
        if ($fileBytes[$i + $j] -ne $searchBytesUTF8[$j]) { $match = $false; break }
    }
    if ($match) {
        $start = [Math]::Max(0, $i - $ContextBytes)
        $end = [Math]::Min($fileBytes.Length, $i + $searchBytesUTF8.Length + $ContextBytes)
        $chunk = New-Object byte[] ($end - $start)
        [Array]::Copy($fileBytes, $start, $chunk, 0, $end - $start)
        $decoded = [System.Text.Encoding]::UTF8.GetString($chunk)
        $cleaned = $decoded -replace '[\x00-\x1F]', '.'
        Write-Output ""
        Write-Output "UTF8 MATCH at offset $i :"
        Write-Output $cleaned
    }
}

# Search UTF-16LE
for ($i = 0; $i -lt $fileBytes.Length - $searchBytesU16.Length; $i++) {
    $match = $true
    for ($j = 0; $j -lt $searchBytesU16.Length; $j++) {
        if ($fileBytes[$i + $j] -ne $searchBytesU16[$j]) { $match = $false; break }
    }
    if ($match) {
        # Align to 2-byte boundary
        $alignedStart = [Math]::Max(0, $i - $ContextBytes)
        if ($alignedStart % 2 -ne 0) { $alignedStart-- }
        $alignedEnd = [Math]::Min($fileBytes.Length, $i + $searchBytesU16.Length + $ContextBytes)
        if ($alignedEnd % 2 -ne 0) { $alignedEnd-- }
        $chunk = New-Object byte[] ($alignedEnd - $alignedStart)
        [Array]::Copy($fileBytes, $alignedStart, $chunk, 0, $alignedEnd - $alignedStart)
        $decoded = [System.Text.Encoding]::Unicode.GetString($chunk)
        $cleaned = $decoded -replace '[\x00-\x1F]', '.'
        Write-Output ""
        Write-Output "U16 MATCH at offset $i :"
        Write-Output $cleaned
    }
}
