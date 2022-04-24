# -*- coding: UTF-8 -*-
# 2022年4月20日 21:14:18 由DertahSama编写的，作为第一个python作品还算不错吧？
# 2022年4月21日 19:30:35 ver1.1 加入了不良页面的诊断&重下载功能
# 2022年4月22日 16:10:35 ver1.2 加入了压缩为纯黑白PDF的功能，可大大减小体积
# 2022年4月22日 18:30:23 ver1.3 优化了下不良页面的诊断&重下载功能，但实在下不了我也没办法了
# 2022年4月24日 15:28:26 ver1.4 优化了一点细节

import requests,time,os,shutil,img2pdf,sys,re,numpy,cv2
from PyPDF2 import PdfFileReader,PdfFileWriter
from PIL import Image
from io import BytesIO

def progress_bar(now,alls):
    print("\r", end="")
    progress=int(now/alls*50)
    print("进度: %d/%d: "%(now,alls), "▋"*progress + "-"*(50-progress), end="")
    sys.stdout.flush()
    time.sleep(0.01)

def AddAPage(pdf_w,file_name):
    if ".pdf" in file_name:
        pdf_pagein=PdfFileReader(file_name)
        pdf_w.addPage(pdf_pagein.getPage(0))
    else:
        img=Image.open(file_name)
        with open(file_name+".pdf","wb") as f:
            f.write(img2pdf.convert(img.filename))
        pdf_pagein=PdfFileReader(file_name+".pdf")
        pdf_w.addPage(pdf_pagein.getPage(0))
    return pdf_w

def GatherPDF(pdf_out,type_dict,folder):
    all_pages=sum(type_dict.values())
    index=1
    while index<=all_pages:
        pdf_out=AddAPage(pdf_out,folder+"/%06d.pdf"%index)
        index=index+1
    return pdf_out

def GetData():
    url=input("输入阅读页面网址（页面不要关）：")
    print("开始获取信息……")

    resp=requests.get(url).text
    #不会用高级的办法，就只会正则匹配
    try:
        jpgpath=re.search(r'jpgPath: "(.*)",',resp).group(1)
    except:
        raise Exception("获取信息失败，网址可能已超时。")
    img_url_head="http://img.sslibrary.com"+jpgpath

    bookname=re.search(r'"bookinfo".*>(.*)<',resp).group(1)

    xmlpath=re.search(r'id="ztree" param="(.*)" ',resp).group(1)
    xmlurl=xmlpath.replace('/cat/cat2xml.dll?','http://path.sslibrary.com/cat/cat2xml.dll?')
    xml_r=requests.get(xmlurl)
    contents_xml=xml_r.content.decode('utf-8')

    page_info=re.search(r'var pages = \[(.*)\]',resp).group(1)
    page_info2find=re.finditer(r'\[\d+, \d+\]',page_info)
    page_maxes=[]
    for match in page_info2find:
        #print(match.group())
        num=re.search(r', (\d+)',match.group()).group(1)
        page_maxes.append(int(num))
    type_dict={'cov':max(page_maxes[7],1),  #封面
                'bok':page_maxes[1],        #书名页
                'leg':page_maxes[2],        #版权页
                'fow':page_maxes[3],        #前言
                "!00":page_maxes[4],        #目录
                '000':page_maxes[5]}        #正文

    print("获取信息成功，书名：["+bookname+"]，即将开始下载……")
    return [bookname, img_url_head, type_dict, contents_xml]

def DownloadCore(img_url,index,type_dict):
    img=requests.get(img_url)
    img_pic=Image.open(BytesIO(img.content))
    resol_bad=img_pic.width<800 #太小了说明有问题

    with open("./RAW/%06d.pdf"%index,'wb+') as f: #写入/RAW
        f.write(img2pdf.convert(img.content))
    page_bad=os.path.getsize("./RAW/%06d.pdf"%index)==18269 #「数据加载失败」页面的大小为18269B

    # 转化为黑白图片备用，写入/RAW/tiff，也就是说管你想不想compress我在下载的时候就已compress好啦
    src=cv2.imdecode(numpy.frombuffer(img.content,numpy.uint8),cv2.IMREAD_COLOR) #用cv2模块处理
    if index<=type_dict['cov']: #封面不转黑白
        cv2.imwrite("./RAW/tiff/%06d.jpeg"%index,src,[int(cv2.IMWRITE_JPEG_QUALITY), 80])
    else: #剩下的页转黑白
        blurred = cv2.GaussianBlur(src, (1, 1), 0) #涂抹降噪，不想涂抹的话改成(1,1)
        gray=cv2.cvtColor(blurred ,cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 25, 20)
        cv2.imwrite("./RAW/tiff/%06d.tiff"%index,binary)

    result_bad=resol_bad or page_bad
    return result_bad

def Download(img_url_head,type_dict,Zoom,interval):
    print("（当前清晰度：zoom="+Zoom+"，当前下载间隔：%.1f s）"%interval)
    all_pages=sum(type_dict.values())
    index=1
    retry=0
    PageToRedownload={}
    
    for type in type_dict:  #开干！
        page_max=type_dict[type]
        page=1
        while page<=page_max:
            page_str=type+"%03d"%page   #当前页地址
            if type=='cov':  #封面还是保留彩色吧   
                img_url=img_url_head+page_str+"?zoom=2"                 
            elif type=='000':   #万一正文超过1000页
                img_url=img_url_head+"%06d"%page+"?zoom="+Zoom
            else:
                img_url=img_url_head+page_str+"?zoom="+Zoom

            result_bad=DownloadCore(img_url,index,type_dict)
            time.sleep(interval) #慢一点免得被ban

            if result_bad: #出问题，尝试重新下载
                retry=retry+1
                if retry>3:
                    # raise Exception("第%06d页("%index+page_str+")访问失败，下载终止，请检查网络或考虑降低zoom。")
                    print("第%06d页("%index+page_str+")访问失败，待会儿再下（或请考虑降低zoom）……")
                    PageToRedownload['%06d'%index]=img_url
                    page=page+1
                    index=index+1
                    retry=0
                else:
                    if retry==1:
                        print("\n", end="")
                    print("\r第%06d页("%index+page_str+")访问受阻，%d秒后尝试第 %d 次重新下载……"%(3,retry), end="")
                    time.sleep(3)
            else:   #没问题就收入并下一页
                # pdf_out=AddAPage(pdf_out,"./RAW/%06d.pdf"%index)
                progress_bar(index,all_pages)
                page=page+1
                index=index+1
                retry=0             
    # with open(base_path+ '/'+bookname+'.pdf','wb') as fout:
    #     pdf_out.write(fout)
    return PageToRedownload

def Redownload(PageToRedownload,interval, type_dict):
    success=[]
    retry=1
    while len(PageToRedownload)>len(success):
        print("第 %d 轮重新下载……"%retry)
        for key in PageToRedownload:
            if key in success:
                continue
            index=int(key)
            img_url=PageToRedownload[key]
            result_bad=DownloadCore(img_url,index,type_dict)
            if result_bad:
                print("第%06d页还是失败，待会儿再试……"%index)
            else:
                print("第%06d页重新下载成功……"%index)
                success.append(key)
            time.sleep(interval) #慢一点免得被ban
        if retry>=5:
            print("多次重新下载失败！请检查网络或考虑改小zoom！\n总之接下来把已下下来的文件合并输出了……")
            break
        retry+=1
        time.sleep(5)
    return 0
    
def AddContents(pdf_out,type_dict,contents_xml):
    #加目录
    print("\n添加目录……")
    parent_id=[0, 0, 0, 0]
    parent_id[0]=pdf_out.addBookmark("封面",0,parent=None)
    parent_id[0]=pdf_out.addBookmark("版权页",0+type_dict['bok']+type_dict['cov']-1,parent=None)
    parent_id[0]=pdf_out.addBookmark("前言",0+type_dict['bok']+type_dict['cov']+type_dict['leg']-1,parent=None)
    parent_id[0]=pdf_out.addBookmark("目录",0+type_dict['bok']+type_dict['cov']+type_dict['leg']+type_dict['fow']-1,parent=None)
    offset=sum(type_dict.values())-type_dict['000']   #xml里的页码是从正文开始的，所以与pdf页码有个偏移
    for match in re.finditer(r'id=.*?InsertPageNumber',contents_xml):   #提取一条目录数据
        index=re.search(r'id="(.*?)"',match.group()).group(1)
        caption=re.search(r'Caption="(.*?)"',match.group()).group(1)
        pagenumber=re.search(r'PageNumber="(.*?)"',match.group()).group(1)
        pagenumber=int(pagenumber)+offset-1 #python里页码是从0开始的

        for level in list(range(4)):
            if index.count('-')==level: #数index字符串里的横杠来判断层级，不太优雅但works
                # print('\t'*level+caption+'\t'+pagenumber)
                if level==0 or parent_id[level-1]==0:
                    parent_id[level]=pdf_out.addBookmark(caption,pagenumber,parent=None)
                else:
                    parent_id[level]=pdf_out.addBookmark(caption,pagenumber,parent=parent_id[level-1])
    
    return pdf_out

def Compress(type_dict):
    print("压缩处理中……")
    all_pages=sum(type_dict.values())
    index=1 
    pdf_compressed=PdfFileWriter()
    while index<=type_dict['cov']: 
        pdf_compressed=AddAPage(pdf_compressed,"./RAW/tiff/%06d.jpeg"%index)
        progress_bar(index,all_pages)
        index=index+1
    while index<=all_pages:
        pdf_compressed=AddAPage(pdf_compressed,"./RAW/tiff/%06d.tiff"%index)
        progress_bar(index,all_pages)
        index=index+1
    print(" ")
    return pdf_compressed


def main():
    # 获取信息
    [bookname, img_url_head, type_dict, contents_xml]=GetData()

    #一点准备工作
    base_path=os.getcwd().replace('\\','/')
    if os.path.exists(base_path+'/RAW'):    #清空存下载数据的RAW文件夹
        shutil.rmtree(base_path+'/RAW')
    os.mkdir('./RAW')
    os.mkdir("./RAW/tiff")
    pdf_out = PdfFileWriter()

    # 【注意！】最高清晰度Zoom='3'将总是去色的，
    # 如果你要下的书是彩色的并且愿意牺牲一些清晰度来保留彩色的话，这里可改为Zoom='2'
    Zoom='3'
    # 【注意！】为了避免访问太快被ban，应当设置一个下载间隔时间，单位秒
    interval=1

    #下载与合成
    PageToRedownload=Download(img_url_head, type_dict, Zoom, interval)
    Redownload(PageToRedownload, interval, type_dict)
    pdf_out=GatherPDF(pdf_out,type_dict,"./RAW")

    #加目录
    pdf_out=AddContents(pdf_out, type_dict, contents_xml)

    #保存
    with open(bookname+'.pdf','wb') as fout:
        pdf_out.write(fout)

    print("已保存到： "+base_path+ '/'+bookname+'.pdf')

    choose=input("要压缩PDF到纯黑白吗？若是灰度图像可大大减小体积（y/n）：")
    if choose=="y":
        pdf_compressed=Compress(type_dict)
        pdf_compressed=AddContents(pdf_compressed,type_dict,contents_xml)
        with open("[黑白]"+bookname+'.pdf','wb') as fout:
            pdf_compressed.write(fout)
        print("压缩后的已保存到： "+base_path+ '/[黑白]'+bookname+'.pdf')

if __name__ == '__main__':
    main()