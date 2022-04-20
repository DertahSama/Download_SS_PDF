# -*- coding: UTF-8 -*-
# 2022年4月20日 21:14:18 由DertahSama编写的，作为第一个python作品还算不错吧？

import requests,time,os,shutil,img2pdf,sys,re
from PyPDF2 import PdfFileReader,PdfFileWriter

def progress_bar(now,alls):
    print("\r", end="")
    progress=int(now/alls*50)
    print("下载进度: %d/%d: "%(now,alls), "▋"*progress + "-"*(50-progress), end="")
    sys.stdout.flush()
    time.sleep(0.05)

def GetData():
    url=input("输入阅读页面网址：")
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

def Download(img_url_head,type_dict,pdf_out,Zoom,interval,base_path):
    print("（当前清晰度：zoom="+Zoom+"，当前下载间隔：%.1f s）"%interval)
    all_pages=sum(type_dict.values())
    index=1
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

            img=requests.get(img_url)
            time.sleep(interval) #慢一点免得被ban
            with open(base_path+'/RAW/'+page_str+".pdf",'wb+') as f:
                f.write(img2pdf.convert(img.content))

            pdf_pagein=PdfFileReader(base_path+'/RAW/'+page_str+".pdf")
            pdf_out.addPage(pdf_pagein.getPage(0))
            
            progress_bar(index,all_pages)
            page=page+1
            index=index+1
    # with open(base_path+ '/'+bookname+'.pdf','wb') as fout:
    #     pdf_out.write(fout)
    return pdf_out
    
def AddContents(type_dict,pdf_out,contents_xml):
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

def main():
    # 获取信息
    [bookname, img_url_head, type_dict, contents_xml]=GetData()

    #一点准备工作
    base_path=os.getcwd().replace('\\','/')
    if os.path.exists(base_path+'/RAW'):    #清空存下载数据的RAW文件夹
        shutil.rmtree(base_path+'/RAW')
    os.mkdir(base_path+'/RAW')
    pdf_out = PdfFileWriter()

    # 【注意！】最高清晰度Zoom='3'将总是去色的，
    # 如果你要下的书是彩色的并且愿意牺牲一些清晰度来保留彩色的话，这里可改为Zoom='2'
    Zoom='3'
    # 【注意！】为了避免访问太快被ban，应当设置一个下载间隔时间，单位秒
    interval=1

    #下载与合成
    pdf_out=Download(img_url_head, type_dict,pdf_out,Zoom,interval,base_path)

    #加目录
    pdf_out=AddContents(type_dict,pdf_out,contents_xml)

    #保存
    with open(base_path+ '/'+bookname+'.pdf','wb') as fout:
        pdf_out.write(fout)

    print("已保存到： "+base_path+ '/'+bookname+'.pdf')

if __name__ == '__main__':
    main()