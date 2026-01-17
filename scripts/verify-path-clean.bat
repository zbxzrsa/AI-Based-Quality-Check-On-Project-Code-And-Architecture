@echo off
REM Verify Path Clean Status
REM This script checks if your project is free from Chinese path references and ready for CI/CD

echo.
echo Verifying project Path-Clean status...
echo Current working directory: %CD%
echo.

REM Step 1: Check npm configurations
echo Step 1: Checking npm configurations...

REM Get current npm configurations
for /f "tokens=*" %%i in ('npm config get cache 2^>nul') do set NPM_CACHE=%%i
for /f "tokens=*" %%i in ('npm config get prefix 2^>nul') do set NPM_PREFIX=%%i
for /f "tokens=*" %%i in ('npm config get tmp 2^>nul') do set NPM_TMP=%%i

echo Current npm configurations:
echo   cache: %NPM_CACHE%
echo   prefix: %NPM_PREFIX%
echo   tmp: %NPM_TMP%
echo.

REM Check for Chinese characters in paths
set CHINESE_FOUND=false

REM Function to check for Chinese characters
call :check_chinese "%NPM_CACHE%" cache_result
if "%cache_result%"=="true" (
    echo ERROR: Chinese characters found in npm cache path: %NPM_CACHE%
    set CHINESE_FOUND=true
) else (
    echo SUCCESS: npm cache path is clean: %NPM_CACHE%
)

call :check_chinese "%NPM_PREFIX%" prefix_result
if "%prefix_result%"=="true" (
    echo ERROR: Chinese characters found in npm prefix path: %NPM_PREFIX%
    set CHINESE_FOUND=true
) else (
    echo SUCCESS: npm prefix path is clean: %NPM_PREFIX%
)

call :check_chinese "%NPM_TMP%" tmp_result
if "%tmp_result%"=="true" (
    echo ERROR: Chinese characters found in npm tmp path: %NPM_TMP%
    set CHINESE_FOUND=true
) else (
    echo SUCCESS: npm tmp path is clean: %NPM_TMP%
)

echo.

REM Step 2: Check environment variables
echo Step 2: Checking environment variables...

set ENV_VARS=NPM_CONFIG_CACHE NPM_CONFIG_PREFIX NPM_CONFIG_TMP NPM_CONFIG_REGISTRY

for %%v in (%ENV_VARS%) do (
    if defined %%v (
        call :check_chinese "!%%v!" env_result
        if "!env_result!"=="true" (
            echo ERROR: Environment variable %%v contains Chinese characters: !%%v!
            set CHINESE_FOUND=true
        ) else (
            echo SUCCESS: Environment variable %%v is clean: !%%v!
        )
    ) else (
        echo INFO: Environment variable %%v is not set
    )
)

echo.

REM Step 3: Check .npmrc file
echo Step 3: Checking .npmrc file...

if exist .npmrc (
    findstr /r "[一-龥]" .npmrc >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo ERROR: .npmrc file contains Chinese characters
        echo Current .npmrc content:
        type .npmrc
        set CHINESE_FOUND=true
    ) else (
        echo SUCCESS: .npmrc file is clean
        echo Current .npmrc content:
        type .npmrc
    )
) else (
    echo WARNING: .npmrc file not found
)

echo.

REM Step 4: Check npm cache directory
echo Step 4: Checking npm cache directory...

if not "%NPM_CACHE%"=="" (
    if not "%NPM_CACHE%"=="undefined" (
        if exist "%NPM_CACHE%" (
            echo SUCCESS: npm cache directory exists: %NPM_CACHE%
            REM Check if directory is writable (basic check)
            echo. > "%NPM_CACHE%\test_write.tmp" 2>nul
            if %ERRORLEVEL% EQU 0 (
                del "%NPM_CACHE%\test_write.tmp" >nul 2>&1
                echo SUCCESS: npm cache directory is writable
            ) else (
                echo ERROR: npm cache directory is not writable: %NPM_CACHE%
                set CHINESE_FOUND=true
            )
        ) else (
            echo WARNING: npm cache directory does not exist: %NPM_CACHE%
            echo This is normal if cache hasn't been used yet
        )
    ) else (
        echo WARNING: npm cache configuration not found
    )
) else (
    echo WARNING: npm cache configuration not found
)

echo.

REM Step 5: Check project dependencies
echo Step 5: Checking project dependencies...

if exist node_modules (
    echo INFO: node_modules directory exists
) else (
    echo INFO: node_modules directory not found (this is expected after cleanup)
)

if exist package-lock.json (
    echo INFO: package-lock.json exists
) else (
    echo INFO: package-lock.json not found (this is expected after cleanup)
)

echo.

REM Step 6: Test npm commands
echo Step 6: Testing npm commands...

where npm >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Testing npm config list...
    npm config list >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo SUCCESS: npm config commands work correctly
    ) else (
        echo ERROR: npm config commands failed
        set CHINESE_FOUND=true
    )
    
    echo Testing npm cache location...
    npm config get cache >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo SUCCESS: npm cache location accessible
    ) else (
        echo ERROR: npm cache location not accessible
        set CHINESE_FOUND=true
    )
) else (
    echo ERROR: npm command not found
    set CHINESE_FOUND=true
)

echo.

REM Step 7: Check for files with Chinese characters
echo Step 7: Scanning project files for Chinese characters...

set CHINESE_FILES_FOUND=false

REM Check common configuration files
for %%f in (.gitignore .env .env.local .env.development .env.production) do (
    if exist "%%f" (
        findstr /r "[一-龥]" "%%f" >nul 2>&1
        if %ERRORLEVEL% EQU 0 (
            echo WARNING: File %%f contains Chinese characters
            set CHINESE_FILES_FOUND=true
        )
    )
)

REM Check for files with Chinese characters in filenames (basic check)
for %%f in (*.*) do (
    echo %%f | findstr /r "[一-龥]" >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo WARNING: Found file with Chinese characters in filename: %%f
        set CHINESE_FILES_FOUND=true
    )
)

if "%CHINESE_FILES_FOUND%"=="false" (
    echo SUCCESS: No Chinese characters found in project files
)

echo.

REM Step 8: Final assessment
echo Step 8: Final assessment...
echo.

if "%CHINESE_FOUND%"=="false" (
    if "%CHINESE_FILES_FOUND%"=="false" (
        echo SUCCESS: PROJECT IS PATH-CLEAN!
        echo SUCCESS: No Chinese characters found in npm configurations
        echo SUCCESS: No Chinese characters found in environment variables
        echo SUCCESS: No Chinese characters found in project files
        echo SUCCESS: npm cache is properly configured
        echo SUCCESS: Project is ready for CI/CD environment
        echo.
        echo Summary:
        echo   npm cache location: %NPM_CACHE%
        echo   npm prefix: %NPM_PREFIX%
        echo   npm tmp: %NPM_TMP%
        echo.
        echo To maintain this clean state:
        echo   1. Keep npm_config_cache environment variable set
        echo   2. Avoid installing npm packages in directories with Chinese paths
        echo   3. Use the cleanup scripts if Chinese paths are detected again
        echo   4. Regularly run this verification script
    )
) else (
    echo ERROR: PROJECT STILL HAS PATH ISSUES
    echo ERROR: Chinese characters were found in configurations or files
    echo Please run the cleanup scripts to resolve these issues:
    echo   clean-npm-cache.bat (Windows)
    echo.
    echo After running cleanup, re-run this verification script
)

echo.
echo Verification completed.
pause
exit /b 0

REM Function to check for Chinese characters in a string
:check_chinese
set "input=%~1"
set "result=false"

REM Basic check for common Chinese characters
echo %input% | findstr /r "[一-龥]" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "%~2=true"
) else (
    set "%~2=false"
)
goto :eof
