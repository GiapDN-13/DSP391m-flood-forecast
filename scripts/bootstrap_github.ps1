<#
    Thiết lập GitHub cho dự án DSP391m — Giáp chạy 1 lần ở W01.

    Yêu cầu: GitHub CLI đã cài và đăng nhập
        winget install GitHub.cli
        gh auth login

    Cách chạy:
        cd E:\FPT_University\2026\FALL_26\DSP391m
        .\scripts\bootstrap_github.ps1 -Repo "<user>/DSP391m-flood-forecast"
#>

param(
    [Parameter(Mandatory = $true)][string]$Repo
)

$ErrorActionPreference = "Stop"
Write-Host "==> Thiết lập $Repo" -ForegroundColor Cyan

# ---------- 1. Labels ----------
$labels = @(
    @{ name = "p0-critical";     color = "b60205"; desc = "Tren duong gang, tre la chet" },
    @{ name = "p1";              color = "d93f0b"; desc = "Uu tien thuong" },
    @{ name = "p2";              color = "fbca04"; desc = "Uu tien thap" },
    @{ name = "data";            color = "0e8a16"; desc = "Crawl / ETL / lam sach" },
    @{ name = "model";           color = "1d76db"; desc = "Feature + mo hinh" },
    @{ name = "eda";             color = "5319e7"; desc = "Phan tich kham pha" },
    @{ name = "dashboard";       color = "006b75"; desc = "Streamlit / truc quan hoa" },
    @{ name = "docs";            color = "c5def5"; desc = "Bao cao / tai lieu / slide" },
    @{ name = "infra";           color = "444444"; desc = "Repo, CI, moi truong" },
    @{ name = "good-first-task"; color = "7057ff"; desc = "Viec de, co huong dan - uu tien giao Duc" },
    @{ name = "light-task";      color = "bfdadc"; desc = "Viec nhe, async, khong deadline gap - danh cho Huyen" },
    @{ name = "blocked";         color = "e11d21"; desc = "Dang ket, can nguoi go" },
    @{ name = "needs-review";    color = "0075ca"; desc = "Cho nguoi khac xem" }
)

foreach ($l in $labels) {
    gh label create $l.name --repo $Repo --color $l.color --description $l.desc --force | Out-Null
    Write-Host "  label: $($l.name)"
}

# ---------- 2. Milestones ----------
$milestones = @(
    @{ title = "Report 1"; due = "2026-10-01"; desc = "10% - Proposal. Han that 04/10, noi bo 01/10" },
    @{ title = "Report 2"; due = "2026-10-29"; desc = "20% - Data + EDA. Han that 01/11, noi bo 29/10" },
    @{ title = "Report 3"; due = "2026-12-10"; desc = "40% - Model + Evaluation. Han that 13/12, noi bo 10/12" },
    @{ title = "Final + Exam"; due = "2026-12-18"; desc = "10% + 20% - Final report va thi van dap" }
)

foreach ($m in $milestones) {
    gh api -X POST "repos/$Repo/milestones" `
        -f title="$($m.title)" `
        -f due_on="$($m.due)T17:00:00Z" `
        -f description="$($m.desc)" 2>$null | Out-Null
    Write-Host "  milestone: $($m.title)"
}

# ---------- 3. Bảo vệ nhánh main ----------
Write-Host "==> Bat branch protection cho main" -ForegroundColor Cyan
$protection = @{
    required_status_checks        = @{ strict = $true; contexts = @("ci") }
    enforce_admins                = $false
    required_pull_request_reviews = @{ required_approving_review_count = 1 }
    restrictions                  = $null
} | ConvertTo-Json -Depth 5

$protection | Out-File -FilePath "$env:TEMP\prot.json" -Encoding utf8
gh api -X PUT "repos/$Repo/branches/main/protection" --input "$env:TEMP\prot.json" | Out-Null
Remove-Item "$env:TEMP\prot.json"

# ---------- 4. Issue khởi động cho W01 ----------
Write-Host "==> Tao issue tuan 1" -ForegroundColor Cyan
$w01 = @(
    @{ t = "[W01] Bao giang vien team doi tu 2 sang 3 nguoi"; l = "p0-critical,docs";      a = "Giap" },
    @{ t = "[W01] Goi thu Flood API 1 diem song Huong (16.46, 107.59)"; l = "p0-critical,data"; a = "Giap" },
    @{ t = "[W01] Setup moi truong + chay lai notebook cua Giap"; l = "good-first-task,infra"; a = "Duc" },
    @{ t = "[W01] Doc doc Open-Meteo, viet API_NOTES.md";      l = "good-first-task,docs";  a = "Duc" },
    @{ t = "[W01] Lap Zotero group + tim 6 bai bao";           l = "light-task,docs";       a = "Huyen" },
    @{ t = "[W01] Tom tat paper 01 va 02";                     l = "light-task,docs";       a = "Huyen" },
    @{ t = "[W01] Dien muc 6 TEAM.md - thoa thuan ho tro";     l = "light-task,docs";       a = "Ca team" }
)

foreach ($i in $w01) {
    gh issue create --repo $Repo --title $i.t --label $i.l --milestone "Report 1" `
        --body "Nguoi lam: $($i.a)`n`nXem chi tiet trong docs/PLAN.md muc W01." | Out-Null
    Write-Host "  issue: $($i.t)"
}

Write-Host ""
Write-Host "XONG." -ForegroundColor Green
Write-Host "Viec con lai lam bang tay tren web (gh CLI chua ho tro tot Projects v2):" -ForegroundColor Yellow
Write-Host "  1. Tao Project 'DSP391m Flood Forecast' (kieu Table)"
Write-Host "  2. Them truong: Status, Owner, Week, Effort, Due  (xem docs/TRACKING.md)"
Write-Host "  3. Tao 3 view: Board theo Status / Table theo Owner / Board theo Week"
Write-Host "  4. Moi Duc va Huyen lam collaborator quyen 'push'"
