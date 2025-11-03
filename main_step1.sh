#!/bin/bash

# prepare A股数据

cd ./data
# 使用get_astock_data.py下载A股数据
python get_astock_data.py
cd ../
