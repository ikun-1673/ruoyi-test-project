@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

rem 优先使用 PATH 中的 jmeter；若未加入 PATH，则回退到本机安装路径（换机器时改这一行即可）
where jmeter.bat >nul 2>&1 && (set "JMETER=jmeter.bat") || (set "JMETER=C:\Tools\apache-jmeter-5.6.3\bin\jmeter.bat")
rem 脚本已移入 scripts\ 目录，以下路径基于脚本自身位置自动推导，换电脑也无需修改
set "HERE=%~dp0"
set "JMX=%HERE%ruoyi_login.jmx"
set "OUT=%~dp0.."

:menu
cls
echo ================================================================
echo    若依登录接口 - JMeter 阶梯压测
echo ================================================================
echo.
echo     [1]  预热         10 线程 /  30 秒   （正式压测前先跑这个）
echo     [2]  第 1 档      50 线程 / 120 秒
echo     [3]  第 2 档     100 线程 / 120 秒
echo     [4]  第 3 档     200 线程 / 120 秒
echo     [5]  第 4 档     300 线程 / 120 秒
echo.
echo     [6]  一键跑完：预热 + 全部 4 档（约 12 分钟，中途别关窗口）
echo     [0]  退出
echo.
echo ================================================================
set /p choice=请输入数字并回车: 

if "%choice%"=="1" goto warmup
if "%choice%"=="2" goto t50
if "%choice%"=="3" goto t100
if "%choice%"=="4" goto t200
if "%choice%"=="5" goto t300
if "%choice%"=="6" goto all
if "%choice%"=="0" exit /b
goto menu

:: ============ 各档位 ============
:warmup
call :run_tier warmup 10 5 30 "预热"
goto end

:t50
call :run_tier result_50 50 10 120 "第 1 档 50 线程"
goto end

:t100
call :run_tier result_100 100 10 120 "第 2 档 100 线程"
goto end

:t200
call :run_tier result_200 200 10 120 "第 3 档 200 线程"
goto end

:t300
call :run_tier result_300 300 10 120 "第 4 档 300 线程"
goto end

:all
echo.
echo 即将依次运行：预热 + 50 + 100 + 200 + 300
echo 总计约 12 分钟，请保持窗口开启。
pause
call :run_tier warmup 10 5 30 "预热"
call :run_tier result_50 50 10 120 "第 1 档 50 线程"
call :run_tier result_100 100 10 120 "第 2 档 100 线程"
call :run_tier result_200 200 10 120 "第 3 档 200 线程"
call :run_tier result_300 300 10 120 "第 4 档 300 线程"
echo.
echo ================================================================
echo   全部完成！数据在 results\ ，报告在 reports\
echo ================================================================
goto end

:: ============ 运行单档的子过程 ============
:: 参数: %1=文件名前缀  %2=线程数  %3=Ramp-Up  %4=持续秒数  %5=显示名称
:run_tier
set "TAG=%~1"
set "THREADS=%~2"
set "RAMPUP=%~3"
set "DURATION=%~4"
set "LABEL=%~5"

echo.
echo ----------------------------------------------------------------
echo   正在运行：%LABEL%
echo   线程=%THREADS%  Ramp-Up=%RAMPUP%s  持续=%DURATION%s
echo ----------------------------------------------------------------
echo.

rem 自动清理同档旧数据，避免 "Directory already exists" 报错
if exist "%OUT%\reports\%TAG%" rmdir /s /q "%OUT%\reports\%TAG%"
if exist "%OUT%\results\%TAG%.jtl" del /q "%OUT%\results\%TAG%.jtl"

call "%JMETER%" -n -t "%JMX%" -Jthreads=%THREADS% -Jrampup=%RAMPUP% -Jduration=%DURATION% -l "%OUT%\results\%TAG%.jtl" -e -o "%OUT%\reports\%TAG%"

echo.
echo   [完成] %LABEL%  报告: reports\%TAG%\index.html
echo.
exit /b

:end
echo.
echo 按任意键返回菜单...
pause >nul
goto menu
