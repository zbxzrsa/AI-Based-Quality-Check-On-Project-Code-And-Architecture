@echo off
REM Clean NPM Cache and Remove Chinese Path References
REM This script ensures your project is "Path-Clean" for CI/CD environments

echo.
echo Starting npm cache cleanup and Chinese path removal...
echo Current working directory: %CD%
echo.

REM Step 1: Clean project dependencies
echo Step 1: Cleaning project dependencies...
if exist node_modules (
    echo Removing node_modules...
    rmdir /s /q node_modules
    echo node_modules removed
) else (
    echo node_modules directory not found
)

if exist package-lock.json (
    echo Removing package-lock.json...
    del package-lock.json
    echo package-lock.json removed
) else (
    echo package-lock.json not found
)

REM Step 2: Clean npm cache
echo.
echo Step 2: Cleaning npm cache...
where npm >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Running npm cache clean --force...
    npm cache clean --force
    echo npm cache cleaned
) else (
    echo ERROR: npm command not found. Please install Node.js and npm first.
    pause
    exit /b 1
)

REM Step 3: Check npm configurations
echo.
echo Step 3: Checking npm configurations for Chinese paths...

REM Get current npm configurations
for /f "tokens=*" %%i in ('npm config get cache 2^>nul') do set NPM_CACHE=%%i
for /f "tokens=*" %%i in ('npm config get prefix 2^>nul') do set NPM_PREFIX=%%i
for /f "tokens=*" %%i in ('npm config get tmp 2^>nul') do set NPM_TMP=%%i

echo Current npm configurations:
echo   cache: %NPM_CACHE%
echo   prefix: %NPM_PREFIX%
echo   tmp: %NPM_TMP%

REM Check for Chinese characters in paths (basic check for common Chinese characters)
set CHINESE_FOUND=false

REM Function to check for Chinese characters
call :check_chinese "%NPM_CACHE%" cache_result
if "%cache_result%"=="true" set CHINESE_FOUND=true

call :check_chinese "%NPM_PREFIX%" prefix_result
if "%prefix_result%"=="true" set CHINESE_FOUND=true

call :check_chinese "%NPM_TMP%" tmp_result
if "%tmp_result%"=="true" set CHINESE_FOUND=true

if "%CHINESE_FOUND%"=="true" (
    echo.
    echo WARNING: Chinese characters found in npm configurations
) else (
    echo.
    echo No Chinese paths found in npm configurations
)

REM Step 4: Unset problematic configurations
if "%CHINESE_FOUND%"=="true" (
    echo.
    echo Step 4: Unsetting configurations with Chinese paths...
    
    call :check_chinese "%NPM_CACHE%" cache_result
    if "%cache_result%"=="true" (
        echo Unsetting npm cache configuration...
        npm config delete cache
        echo npm cache configuration unset
    )
    
    call :check_chinese "%NPM_PREFIX%" prefix_result
    if "%prefix_result%"=="true" (
        echo Unsetting npm prefix configuration...
        npm config delete prefix
        echo npm prefix configuration unset
    )
    
    call :check_chinese "%NPM_TMP%" tmp_result
    if "%tmp_result%"=="true" (
        echo Unsetting npm tmp configuration...
        npm config delete tmp
        echo npm tmp configuration unset
    )
)

REM Step 5: Configure npm_config_cache for current session
echo.
echo Step 5: Configuring npm_config_cache for current session...

set CURRENT_DIR=%CD%
set NEW_CACHE_PATH=%CURRENT_DIR%\.npm-cache

echo Setting npm_config_cache to: %NEW_CACHE_PATH%
set npm_config_cache=%NEW_CACHE_PATH%

REM Also set it in npm config for this project
npm config set cache "%NEW_CACHE_PATH%"

echo npm_config_cache configured for current session: %NEW_CACHE_PATH%

REM Step 6: Verify the project is now "Path-Clean"
echo.
echo Step 6: Verifying project is Path-Clean...

REM Check npm configurations again
for /f "tokens=*" %%i in ('npm config get cache 2^>nul') do set NPM_CACHE_NEW=%%i
for /f "tokens=*" %%i in ('npm config get prefix 2^>nul') do set NPM_PREFIX_NEW=%%i
for /f "tokens=*" %%i in ('npm config get tmp 2^>nul') do set NPM_TMP_NEW=%%i

echo Verifying npm configurations:
echo   cache: %NPM_CACHE_NEW%
echo   prefix: %NPM_PREFIX_NEW%
echo   tmp: %NPM_TMP_NEW%
echo   npm_config_cache (env): %npm_config_cache%

set VERIFICATION_PASSED=true

call :check_chinese "%NPM_CACHE_NEW%" cache_result_new
if "%cache_result_new%"=="true" (
    echo ERROR: Chinese characters still found in npm cache path: %NPM_CACHE_NEW%
    set VERIFICATION_PASSED=false
)

call :check_chinese "%NPM_PREFIX_NEW%" prefix_result_new
if "%prefix_result_new%"=="true" (
    echo ERROR: Chinese characters still found in npm prefix path: %NPM_PREFIX_NEW%
    set VERIFICATION_PASSED=false
)

call :check_chinese "%NPM_TMP_NEW%" tmp_result_new
if "%tmp_result_new%"=="true" (
    echo ERROR: Chinese characters still found in npm tmp path: %NPM_TMP_NEW%
    set VERIFICATION_PASSED=false
)

call :check_chinese "%npm_config_cache%" env_result
if "%env_result%"=="true" (
    echo ERROR: Chinese characters still found in npm_config_cache: %npm_config_cache%
    set VERIFICATION_PASSED=false
)

REM Step 7: Additional verification
echo.
echo Step 7: Additional verification...

if exist .npmrc (
    findstr /r "[一-龥]" .npmrc >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo WARNING: .npmrc file contains Chinese characters. Consider cleaning it.
        echo Current .npmrc content:
        type .npmrc
    ) else (
        echo .npmrc file is clean
    )
) else (
    echo .npmrc file not found
)

REM Step 8: Final verification and recommendations
echo.
echo Step 8: Final verification and recommendations...

if "%VERIFICATION_PASSED%"=="true" (
    echo ✅ Project is now Path-Clean!
    echo ✅ No Chinese characters found in npm configurations
    echo ✅ npm_config_cache is properly configured for current session
    echo.
    echo Project is ready for CI/CD environment. Key points:
    echo   • npm cache is isolated to: %NEW_CACHE_PATH%
    echo   • No Chinese paths detected in npm configurations
    echo   • Environment variable npm_config_cache is set for current session
    echo.
    echo To make this permanent for future sessions, add this to your system environment variables:
    echo   npm_config_cache=%NEW_CACHE_PATH%
    echo.
    echo To verify in future, run: npm config list
) else (
    echo ❌ Project still contains Chinese paths
    echo ❌ Verification failed
    echo Please review the errors above and clean up the problematic configurations
    pause
    exit /b 1
)

echo.
echo npm cache cleanup completed successfully!
pause
exit /b 0

REM Function to check for Chinese characters in a string
:check_chinese
set "input=%~1"
set "result=false"

REM Basic check for common Chinese characters (simplified check)
echo %input% | findstr /r "[一-龥]" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "%~2=true"
) else (
    set "%~2=false"
)
goto :eof
