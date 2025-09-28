

# 使用 
## 纯 HEX
python hex_merge.py  -o total.bin  boot.hex  app.hex
## 纯 BIN 拼接（必须给地址）
python hex_merge.py  -o total.bin  boot.bin@0x08000000  app.bin@0x08004000
## HEX + BIN 混合
python hex_merge.py  -o fw.bin  bootloader.hex  app.bin@0x08004000  cfg.bin@0x0801FC00
## 指定基地址与填充字节
python hex_merge.py  -o fw.bin  -b 0x08000000  -p 0x00  *.hex  *.bin@0x08100000


# 编译
## 使用 虚拟环境编译成 exe
 Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
 python -m venv venv
 .\venv\Scripts\Activate.ps1

## 升级 pip 本身
python -m pip install -U pip

## 装打包工具
pip install pyinstaller

## 如有 requirements.txt
pip install -r requirements.txt

## 打包成 exe
pyinstaller -F -w hex_merge.py

## 退出当前虚拟环境
deactivate