@echo off
cd "D:\Programmazione\Fiverr\andychand400 v2"
call .\pycord-env\Scripts\activate.bat
call git clone https://github.com/Pycord-Development/pycord
cd "pycord"
call python -m pip install -U .[voice]
cd ..
rd /s /q ".\pycord"
call .\pycord-env\Scripts\deactivate.bat
echo DONE