:: For double-clicking convenience: uncomment the --chat line to also open chat for streams
@echo off
set /p input=Enter Twitch channel name(s) (space-separated): 
call streamledge --live %input%
:: call streamledge --chat %input%
exit
