<#
.SYNOPSIS
    Run the whole corpus through the real pipeline and score it.

.DESCRIPTION
    One command, start to finish:

        1. brings the stack up
        2. clears results from previous runs
        3. uploads all 300 corpus PDFs through POST /documents
        4. waits while the worker reads them, showing progress
        5. scores what landed against the sealed answer key
        6. writes a timestamped report and a JSON file

    This is the product path, not a shortcut through it. The same endpoint a
    doctor's browser calls, the same worker, the same database functions.

    Every document is sent to OpenParser, which is hosted in the United
    States. About 300 pages at roughly Rs 0.09 each, and two to three hours -
    OpenParser throttles hard under sustained load, so the first few documents
    take about six seconds and the average over a long run is nearer forty.

    Ctrl+C is safe at any point. The worker is a container and keeps reading;
    re-run with -KeepData to rejoin the run in progress rather than start it
    over and pay twice.

.PARAMETER KeepData
    Do not clear previous results. Use this to resume an interrupted run.

.PARAMETER Limit
    Only the first N documents, spread across patients. For a quick check
    before committing three hours to the full corpus.

.PARAMETER Workers
    How many worker containers to run. They cannot collide -
    fn_claim_document uses FOR UPDATE SKIP LOCKED - but OpenParser may
    throttle per account rather than per connection, in which case more
    workers give more retries and no more throughput. Start with 1.

.EXAMPLE
    .\bench\run.ps1
    .\bench\run.ps1 -Limit 10
    .\bench\run.ps1 -KeepData
#>
[CmdletBinding()]
param(
    [switch] $KeepData,
    [int]    $Limit = 0,
    [int]    $Workers = 1
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# results/ holds one pair per document and nothing else - the run's own
# reports go in reports/, so a glob over results/ is always just the corpus.
$resultsDir = Join-Path $PSScriptRoot "results"
$reportDir  = Join-Path $PSScriptRoot "reports"
foreach ($d in @($resultsDir, $reportDir)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null }
}

function Write-Rule { Write-Host ("-" * 74) -ForegroundColor DarkGray }

function Get-Scalar($sql) {
    # -t strips the header, and psql still pads; trim hard before comparing.
    $out = docker compose exec -T db psql -U labidp -d labidp -t -c $sql 2>$null
    if ($null -eq $out) { return "" }
    return ($out | Out-String).Trim()
}

function Get-Count($sql) {
    $v = Get-Scalar $sql
    $n = 0
    if ([int]::TryParse($v, [ref] $n)) { return $n }
    return 0
}

# ---------------------------------------------------------------- 1. the stack
Write-Rule
Write-Host "Contexta Lab IDP - corpus benchmark" -ForegroundColor Cyan
Write-Rule

Write-Host "starting the stack..."
docker compose up -d | Out-Null
if ($Workers -gt 1) {
    docker compose up -d --scale worker=$Workers | Out-Null
    Write-Host "  $Workers workers"
}

# The database takes a moment after the container reports started.
$ready = $false
foreach ($i in 1..30) {
    if ((Get-Scalar "SELECT 1;") -eq "1") { $ready = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $ready) {
    Write-Host "the database did not come up. docker compose logs db" -ForegroundColor Red
    exit 1
}

$practice = Get-Count "SELECT id FROM core.practices LIMIT 1;"
if ($practice -eq 0) {
    Write-Host "no practice found - apply the migrations first:" -ForegroundColor Red
    Write-Host "  docker compose exec api python /work/scripts/run_migrations.py"
    exit 1
}

# ------------------------------------------------------------ 2. previous runs
$existing = Get-Count "SELECT count(*) FROM lab.documents WHERE is_deleted = FALSE;"

if ($KeepData) {
    Write-Host "-KeepData: leaving $existing document(s) in place" -ForegroundColor Yellow
} elseif ($existing -gt 0) {
    $rows = Get-Count "SELECT count(*) FROM lab.results WHERE is_deleted = FALSE;"
    Write-Host ""
    Write-Host "About to delete $existing document(s) and $rows result(s) from the" -ForegroundColor Yellow
    Write-Host "previous run. A score computed over two runs mixed together is worse" -ForegroundColor Yellow
    Write-Host "than no score. The corpus is synthetic, so nothing real is lost." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Ctrl+C now to stop, or -KeepData to resume an interrupted run."
    foreach ($i in 5..1) {
        # The return goes at the START of the write, not after it. Ending a
        # line with a return leaves the cursor parked and the next write lands
        # on top of whatever is already there.
        Write-Host ("`r  clearing in $i... ") -NoNewline
        Start-Sleep -Seconds 1
    }
    Write-Host "`r  clearing...           "
    docker compose exec -T db psql -U labidp -d labidp -q `
        -c "UPDATE lab.documents SET is_synthetic = TRUE;" `
        -c "SELECT * FROM lab.fn_purge_synthetic($practice);" `
        -c "DELETE FROM core.visit_attachments;" | Out-Null
    Remove-Item (Join-Path $root "storage\*.pdf") -ErrorAction SilentlyContinue
    # The dumps too. One left over from a previous run sits under the same name
    # as the one this run would write, so a document that fails here would show
    # yesterday's extraction as if it were today's - the same hazard as a score
    # computed over two runs mixed together.
    Remove-Item (Join-Path $resultsDir "*.json") -ErrorAction SilentlyContinue
}

# ---------------------------------------------------------------- 3. the upload
$waiting = Get-Count "SELECT count(*) FROM lab.documents WHERE status IN ('received','parsing') AND is_deleted = FALSE;"

# -KeepData never uploads when documents are already here. Waiting ones mean
# an interrupted run to rejoin; none waiting means a finished run to re-score.
# Falling through to the upload in that second case pays for the corpus twice,
# which is the one thing this switch exists to prevent.
if ($KeepData -and $existing -gt 0) {
    Write-Host ""
    if ($waiting -gt 0) {
        Write-Host "$waiting of $existing still reading - rejoining that run, not uploading again."
    } else {
        Write-Host "$existing document(s) already read - scoring those, not uploading again."
    }
} else {
    Write-Host ""
    Write-Host "uploading..."
    if ($Limit -gt 0) {
        docker compose exec -T api python /work/scripts/upload_corpus.py --limit $Limit
    } else {
        docker compose exec -T api python /work/scripts/upload_corpus.py
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "upload failed" -ForegroundColor Red
        exit 1
    }
}

$total = Get-Count "SELECT count(*) FROM lab.documents WHERE is_deleted = FALSE;"

Write-Host ""
Write-Rule
Write-Host "$total document(s) queued. Every one is sent to api.openparser.dev," -ForegroundColor Yellow
Write-Host "in the United States. Roughly Rs $([math]::Round($total * 0.09, 2))." -ForegroundColor Yellow
Write-Rule

# --------------------------------------------------------------- 4. the waiting
Write-Host ""
Write-Host "reading. Ctrl+C is safe - the worker keeps going, and -KeepData rejoins."
Write-Host ""

$started = Get-Date
$lastDone = -1

while ($true) {
    $left = Get-Count "SELECT count(*) FROM lab.documents WHERE status IN ('received','parsing') AND is_deleted = FALSE;"
    $done = $total - $left
    $elapsed = (Get-Date) - $started

    $eta = "estimating"
    if ($done -gt 0 -and $left -gt 0) {
        $perDoc = $elapsed.TotalSeconds / $done
        $remain = [TimeSpan]::FromSeconds($perDoc * $left)
        $eta = "{0:hh\:mm\:ss} left  ({1:N0}s a document)" -f $remain, $perDoc
    }

    $line = "  {0,4} / {1,-4} done   {2:hh\:mm\:ss} elapsed   {3}" -f $done, $total, $elapsed, $eta
    Write-Host ("`r" + $line.PadRight(78)) -NoNewline

    if ($left -eq 0) { break }
    $lastDone = $done
    Start-Sleep -Seconds 5
}

$elapsed = (Get-Date) - $started
Write-Host ("`r" + ("  {0} / {0} done   {1:hh\:mm\:ss} elapsed" -f $total, $elapsed).PadRight(78))

$failed = Get-Count "SELECT count(*) FROM lab.documents WHERE status = 'failed' AND is_deleted = FALSE;"
if ($failed -gt 0) {
    Write-Host "  $failed document(s) gave up after their retries - see ocr_error" -ForegroundColor Yellow
}

# --------------------------------------------------------------- 5. the scoring
Write-Host ""
Write-Rule
Write-Host "scoring against the sealed answer key" -ForegroundColor Cyan
Write-Rule

$stamp = Get-Date -Format "yyyy-MM-dd-HHmm"
$txt = Join-Path $reportDir "$stamp.txt"
$json = Join-Path $reportDir "$stamp.json"

$commit = (git rev-parse --short HEAD 2>$null)
if ($null -eq $commit) { $commit = "not a git repo" }

# No 2>&1 on these. In PowerShell 5.1 redirecting a native command's stderr
# wraps every line in an ErrorRecord, and with $ErrorActionPreference = "Stop"
# that kills the script - which is what happened on the first full run, after
# forty minutes and the whole corpus, with the scores computed and thrown away.
#
# score_corpus.py also exits non-zero when it finds a wrong code, which is a
# finding and not a failure. Its exit code is recorded, not obeyed.
function Score($tail) {
    $out = & docker compose exec -T api python /work/scripts/score_corpus.py @tail | Out-String
    return $out
}

$overall  = Score @()
$byLayout = Score @("--by-layout")
$holdout  = Score @("--holdout", "4")
$missed   = Score @("--missed")
$metrics  = Score @("--json")
$scoreExit = $LASTEXITCODE

Write-Host $overall
Write-Host $byLayout

$report = @()
$report += "Contexta Lab IDP - corpus benchmark"
$report += "run      $stamp"
$report += "commit   $commit"
$report += "engine   openparser"
$report += "docs     $total  ($failed failed)"
if ($scoreExit -ne 0) {
    $report += "note     the scorer exited $scoreExit - it does that when it finds a"
    $report += "         wrong code. See 'wrong codes' below; the scores stand."
}
$report += "elapsed  {0:hh\:mm\:ss}" -f $elapsed
$report += ""
$report += "=== overall ==="
$report += $overall
$report += "=== by layout ==="
$report += $byLayout
$report += "=== dev vs held out (patients 1-4 were the ones looked at) ==="
$report += $holdout
$report += "=== rows never found ==="
$report += $missed

# UTF-8 without a BOM. Set-Content defaults to the system codepage, which
# mangles the box characters and micro signs in the tables; its -Encoding utf8
# fixes that but writes a BOM, and a BOM makes the JSON file unreadable to
# every JSON parser there is. So neither - write the bytes directly.
$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($txt,  ($report -join "`r`n"), $utf8)
[System.IO.File]::WriteAllText($json, $metrics.Trim(),         $utf8)

Write-Rule
Write-Host "report   $txt" -ForegroundColor Green
Write-Host "metrics  $json" -ForegroundColor Green
Write-Rule
Write-Host ""
Write-Host "Reading the numbers:"
Write-Host "  recall     of the rows printed on the page, how many we found"
Write-Host "  precision  of the rows we produced, how many are real. Expect this"
Write-Host "             to look low: rows printed with no readable value are kept"
Write-Host "             deliberately and the answer key does not contain them."
Write-Host "  code       given a row we found, the right canonical code"
Write-Host "  value      given a row we found, the right number. A wrong value is"
Write-Host "             worse than a wrong code - it puts a false reading on the"
Write-Host "             right chart."
Write-Host ""
Write-Host "--by-layout is the one worth reading. A single recall number hides"
Write-Host "which layouts actually fail."
