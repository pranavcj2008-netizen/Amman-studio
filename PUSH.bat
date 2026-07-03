@echo off
cd "C:\Users\pranav cj\Desktop\jaravic\amman_studio"
"C:\Program Files\Git\bin\git.exe" add .
"C:\Program Files\Git\bin\git.exe" commit -m "update"
"C:\Program Files\Git\bin\git.exe" push origin main
echo.
echo Done! Now go to PythonAnywhere Bash and run:
echo cd /home/pranavcj5555/Amman-studio ^&^& git pull
echo.
pause
