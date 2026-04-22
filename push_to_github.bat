@echo off
REM ====================================================================
REM  One-click push of this folder to GitHub
REM  Repo: https://github.com/cyrilhenson/D-NMDA-Complex-Spine
REM
REM  - Logs everything to push_log.txt
REM  - Auto-handles the case where the GitHub repo already has a README
REM    or license file (does pull --rebase --allow-unrelated-histories
REM    then re-pushes).
REM ====================================================================

setlocal EnableDelayedExpansion
cd /d "%~dp0"

if exist push_log.txt del push_log.txt

call :log "============================================================"
call :log "  Push NMDA-Analysis-App to GitHub"
call :log "  %DATE% %TIME%"
call :log "============================================================"
call :blank

REM --- Step 1. Verify git ---
where git >nul 2>nul
if errorlevel 1 (
    call :log "[ERROR] Git is not installed. Download from https://git-scm.com/download/win"
    goto :end_dump
)
for /f "delims=" %%v in ('git --version') do call :log "Git found: %%v"

REM --- Step 2. Clean leftover .git ---
if exist ".git" (
    call :log "[SETUP] Removing leftover .git folder..."
    rmdir /s /q ".git" 2>nul
    REM In case rmdir failed for some reason
    if exist ".git\*" (
        call :log "[WARN] Could not fully delete .git folder. Continuing anyway."
    )
)

REM --- Step 3. Init ---
call :blank
call :log "[STEP 1/6] Initializing repository..."
git init -b main >> push_log.txt 2>&1
if errorlevel 1 ( call :log "[ERROR] git init failed" & goto :end_dump )

call :log "[STEP 2/6] Setting commit identity (this repo only)..."
git config user.name "Laurence Henson" >> push_log.txt 2>&1
git config user.email "laurence.cyril.henson@gmail.com" >> push_log.txt 2>&1
git config core.autocrlf true >> push_log.txt 2>&1

REM --- Step 4. Stage ---
call :log "[STEP 3/6] Staging files..."
git add . >> push_log.txt 2>&1
if errorlevel 1 ( call :log "[ERROR] git add failed - see log dump below" & goto :end_dump )

REM --- Step 5. Commit ---
call :log "[STEP 4/6] Creating commit..."
git commit -m "Initial commit: NMDA Antagonist study analysis app" >> push_log.txt 2>&1
if errorlevel 1 ( call :log "[ERROR] git commit failed - see log dump below" & goto :end_dump )

REM --- Step 6. Remote ---
call :log "[STEP 5/6] Linking to GitHub repo..."
git remote remove origin >nul 2>&1
git remote add origin https://github.com/cyrilhenson/D-NMDA-Complex-Spine.git >> push_log.txt 2>&1

REM --- Step 7. Push (with auto-fallback if remote is non-empty) ---
call :log "[STEP 6/6] Pushing to GitHub..."
call :blank
call :log "(If a browser pops up asking you to sign in to GitHub, do that now.)"
call :blank

git push -u origin main >> push_log.txt 2>&1
if errorlevel 1 (
    call :log "[INFO] Push rejected (likely the GitHub repo is not empty)."
    call :log "       Trying to merge remote contents and push again..."
    call :blank

    git pull origin main --allow-unrelated-histories --no-edit >> push_log.txt 2>&1
    if errorlevel 1 (
        call :log "[ERROR] Auto-merge failed. See log dump below for details."
        goto :end_dump
    )

    git push -u origin main >> push_log.txt 2>&1
    if errorlevel 1 (
        call :log "[ERROR] Push still failed after merge. See log dump below."
        goto :end_dump
    )
)

call :blank
call :log "============================================================"
call :log "  SUCCESS! View your repo at:"
call :log "  https://github.com/cyrilhenson/D-NMDA-Complex-Spine"
call :log "============================================================"
goto :end

:end_dump
call :blank
call :log "================ FULL LOG (push_log.txt) ==================="
type push_log.txt
call :blank
call :log "============================================================"
call :log "  Above is the full log. It is also saved to push_log.txt"
call :log "  Copy the most relevant lines and share them for help."
call :log "============================================================"

:end
echo.
echo Press any key to close...
pause >nul
exit /b

:log
echo %~1
echo %~1 >> push_log.txt
exit /b 0

:blank
echo.
echo. >> push_log.txt
exit /b 0
