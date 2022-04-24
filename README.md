# Download_SS_PDF
这是一个从超星图书馆（http://www.sslibrary.com ）下载PDF并且自动添加目录的python脚本。鉴于大概没有外国友人用，所以no English。

本脚本由本刚刚学会python的菜鸟一边google一边编写出来，当然不能突破超星图书馆的版权限制，原理只是网页爬虫，只能省去阁下按几百次右键保存图片的时间。

所以请使用者自重，若他人将该项目用于非法用途，本人概不负责。

# 环境与用法
环境为python 3.x，需要的模块如下：
```python
import requests,time,os,shutil,img2pdf,sys,re,numpy,cv2
from PyPDF2 import PdfFileReader,PdfFileWriter
from PIL import Image
from io import BytesIO
```

如果阁下是完全不会python的新人，要使用，只需下载一个Visual Studio Code，安装python扩展，然后打开python所在的目录（大概在\Program Files (x86)\Microsoft Visual Studio\Shared\Python39_64\之类的地方），在Script文件夹上按住Shift地右键→在此处打开Powershell窗口，然后运行以下命令：
```
pip3 install requests PyPDF2 Pillow img2pdf numpy opencv-python
```
然后用VS code打开本脚本运行即可。

用法非常简单：只需在超星网页打开一本书，复制阅读界面的网址进命令行，回车，然后等它下载就可以了。
![snipaste_20220420_205402](https://user-images.githubusercontent.com/74524914/164235308-4b62c5e9-475e-4400-b53b-69bb32fad3c6.png)

# 优点
1. 完整下载封面、版权页、前言页、目录页等，合成为完整的书籍PDF；
2. 与官方pdz下载同等的最高画质；
3. 顺带下载了目录，并妥当地嵌入到了PDF书签中；
![snipaste_20220420_212157](https://user-images.githubusercontent.com/74524914/164239989-9b3190d7-0233-45c5-9287-38d1c6be6b0f.jpg)
4. （ver1.2 new!）可以将下载的PDF压缩为纯黑白，可在保持清晰度情况下可大大减小体积。\
![snipaste_20220424_160835](https://user-images.githubusercontent.com/74524914/164966759-0ac8003f-34f3-4fef-98a5-6dec0b71f79f.jpg)

# 设置
主要能进行清晰度和下载间隔的设置：
1. 清晰度`zoom`：超星的最高分辨率图即为`zoom=3`，但是代价是总是去色的；如果想下载彩色书籍而保留颜色，可更改到`zoom=2`。
2. 下载间隔`interval`:下太快会被ban的！所以默认`interval=1`，即每下一页停1s，因此下载速度略慢。若阁下对自己的ip有信心可以改短一点。

# 更新历史
- 2022年4月21日 19:30:35 ver1.1 加入了不良页面的诊断&重下载功能
- 2022年4月22日 16:10:35 ver1.2 加入了压缩为纯黑白PDF的功能，可大大减小体积
- 2022年4月22日 18:30:23 ver1.3 优化了下不良页面的诊断&重下载功能，但实在下不了我也没办法了
- 2022年4月24日 15:28:26 ver1.4 优化了一点细节

# Credit
本脚本受到https://github.com/0NG/sslibrary-pdf-downloader 的启发而编写，补完了前辈计划做而没有做完的工作。
