@echo off
setlocal

rem Set the console's code page to UTF-8 for this session
chcp 65001 > nul
echo Active code page set to UTF-8 for this console session.

rem Set PostgreSQL client encoding for this session
set PGCLIENTENCODING=UTF8

rem --- SECURITY WARNING ---
rem Storing your password directly in a script is INSECURE.
rem For convenience in a local development environment, you can set it here.
rem For production or shared environments, consider more secure methods
rem like a .pgpass file or environment variables set outside the script.
set PGPASSWORD=testpassword

echo.
echo Attempting to connect to PostgreSQL as user "testuser" on database "grantmatcher_db"...
echo.

rem Launch psql
psql -h localhost -p 5432 -U testuser -d grantmatcher_db

rem Clear the temporary password variable from the environment for security
set PGPASSWORD=

echo.
echo You are now logged out of psql (if you exited it).
echo Press any key to close this console window...
pause > nul