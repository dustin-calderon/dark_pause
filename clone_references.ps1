$base = "D:\Code Projects\dark_pause\.references"

$repos = @(
    # --- Blockers ---
    @{ dir="blockers\selfcontrol";          url="https://github.com/SelfControlApp/selfcontrol.git" },
    @{ dir="blockers\selfrestraint";        url="https://github.com/ParkerK/selfrestraint.git" },
    @{ dir="blockers\focus-cli";            url="https://github.com/ChetanXpro/Focus.git" },
    @{ dir="blockers\website-blocker-desktop"; url="https://github.com/aymendn/website-blocker-desktop.git" },
    @{ dir="blockers\site-blocker";         url="https://github.com/mahmud-r-farhan/Site-Blocker.git" },
    @{ dir="blockers\webblockerscript";     url="https://github.com/karthik558/WebBlockerScript.git" },
    @{ dir="blockers\website-app-blocker";  url="https://github.com/MohammedTsmu/WebsiteAndAppBlocker.git" },
    @{ dir="blockers\hosts-file-editor";    url="https://github.com/scottlerch/HostsFileEditor.git" },

    # --- Trackers ---
    @{ dir="trackers\activitywatch";        url="https://github.com/ActivityWatch/activitywatch.git" },
    @{ dir="trackers\screeny";              url="https://github.com/ArnoGevorkyan/Screeny.git" },
    @{ dir="trackers\screentime";           url="https://github.com/mazarskov/ScreenTime.git" },
    @{ dir="trackers\desktop-time-limiter"; url="https://github.com/AspireOne/desktop-time-limiter.git" },
    @{ dir="trackers\super-productivity";   url="https://github.com/johannesjo/super-productivity.git" },

    # --- Domain Lists ---
    @{ dir="lists\steven-black-hosts";      url="https://github.com/StevenBlack/hosts.git" }
)

foreach ($r in $repos) {
    $dest = Join-Path $base $r.dir
    if (Test-Path $dest) {
        Write-Host "[SKIP] $($r.dir) (already exists)" -ForegroundColor Yellow
        continue
    }
    Write-Host "[CLONE] $($r.dir)..." -ForegroundColor Cyan
    git clone --depth 1 --single-branch $r.url $dest 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK]    $($r.dir)" -ForegroundColor Green
    } else {
        Write-Host "[FAIL]  $($r.dir)" -ForegroundColor Red
    }
}

Write-Host "`nDone! $($repos.Count) repos processed." -ForegroundColor White
