# -*- coding: UTF-8 -*-
# 2022年4月20日 21:14:18 由DertahSama编写的，作为第一个python作品还算不错吧？
# 2022年4月21日 19:30:35 ver1.1 加入了不良页面的诊断&重下载功能
# 2022年4月22日 16:10:35 ver1.2 加入了压缩为纯黑白PDF的功能，可大大减小体积
# 2022年4月22日 18:30:23 ver1.3 优化了下不良页面的诊断&重下载功能，但实在下不了我也没办法了
# 2022年4月24日 15:28:26 ver1.4 优化了一点细节
# 2022年4月28日 21:07:23 ver1.5 调整架构，原来img2pdf是可以一次转换一整个目录的图片的，可提高一点效率
# 2022年4月29日 18:35:56 ver1.6 我终于知道怎么怎么压到ccitt tiff了，tmd一句话我找了一个礼拜
# 2022年5月13日 12:58:40 ver1.6.1 @v1nh1shungry 指出glob得到的列表不一定是排好序的，于是加了个sorted()保证排序
# 2022年5月29日 14:49:29 ver1.6.2 更新了关于新式阅读器的报错说明
# 2022年5月31日 20:45:54 ver1.7 输出的pdf页面宽度统一为18 cm，整齐点。另外为exe用户提供了更改参数的功能。
# 2022年10月06日 17:31:46 ver1.8 添加了选页下载的功能，并给requests加了个伪装头，但好像超星的反爬机制升级了，成功率并不高


import requests,time,os,shutil,img2pdf,sys,re,cv2,glob
from PyPDF2 import PdfFileReader,PdfFileWriter
from PIL import Image
from io import BytesIO

## =======================CONFIGs===========================

# global Zoom,interval,max_retry,max_reretry
# 【下载清晰度】最高清晰度Zoom='3'将总是去色的，
# 如果你要下的书是彩色的并且愿意牺牲一些清晰度来保留彩色的话，这里可改为Zoom='2'
Zoom='3'
# 【下载间隔】为了避免访问太快被ban，应当设置一个下载间隔时间，单位秒
interval=1

# 【下载重试次数】
max_retry=3
# 【集中重新下载重试次数】其中最后一次会以zoom=2下载
max_reretry=3

# 【伪装头】
my_headers = {
    'Upgrade-Insecure-Requests': 1,
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.9'
}
#更多请阅读：https://www.yiibai.com/python/python3-webbug-series3.html
## ============================================================

def ProgressBar(now,alls):
    progress=int(now/alls*50)
    print("\r进度: %d/%d: "%(now,alls), "▋"*progress + "-"*(50-progress), end="")
    if now==alls:
        print("done！")   #100%了换个行
    sys.stdout.flush()
    time.sleep(0.01)

def anError(msg):
    print('\n'+msg)
    input("按回车键退出。")
    raise Exception(msg)

def GetData():
    url=input("输入阅读页面网址（页面不要关）：")
    if "ssj.sslibrary.com" in url:
        anError("本脚不能处理ssj.sslibrary.com打头的新式阅读器！请参考使用说明中给出的解决办法。")
        
    print("开始获取信息……")

    respond=requests.get(url,my_headers)
    resp=respond.text
    
    
    if respond.status_code!=200:
        anError("获取信息失败，网址可能已超时。错误代码：%d"%respond.status_code)

    # 举例，需要的关键信息都在网页源代码的以下这几段。我不会用高级的办法，就只会正则匹配：
    #         <div id="b_title">目录</div>
    #         <div id="dir_div" style="height: 95%;">
    #             <ul id="ztree" param="/cat/cat2xml.dll?kid=6363678E6463648E6A643639303138333432&a=A0157469D3A82CBBCF4BBFC3362D869C" class="ztree"></ul>
    #         </div>
    #
    # <div id="bookinfo" style="display:none">卓宁编,俄语,华中师范大学出版社,1985.12,</div>
    #
    # <script type="text/javascript">
    #     require(['reader', 'pagetypeutil', 'readerExcerpt', 'readerExtract', 'print', 'highlight', 'pagerTool', 'screenshot', 'loadJS','directoryTree', 'readlogger', 'jqueryCookie'],
    #       function (_reader, _ptu, _readerExcerpt, _readerExtract, _print, _highlight, _pagerTool, _screenshot, _loadJS, _directoryTree, _readlogger) {
    #         var pages = [[1, 0], [1, 1], [1, 1], [1, 1], [1, 0], [1, 121], [1, 0], [2, 0]];
    #         var page = 1;
    #         var pageType = 5 ||5;
    #         var ssid = '11521282';

    #         var opts = {
    #             renderId: 'reader',
    #             pages: pages,
    #             cpage: _ptu.getValibPageType(page, pageType, pages),
    #             jpgPath: "/n/91e270fea51bac64a26c15e69956eae7MC341177856311/img0/242B008FE7092F4467F9E74D14B059EB0CE163309E8F5B076D07802703808C00DC70365155796349EBE68CC246360AA0C02FF602BCFC7CC784E4D72A70E4A6D7160ED6BBD2BBEDC31E4BEA12492357E5F8751271E15236B5FE2BED7358E8471233D106B3AEA1969E1309B076FBBD97EFB8CC/bf1/qw/11521282/F936C684B59A43BDA0C3F1035AE38BB6/",

    try:
        jpgpath=re.search(r'jpgPath: "(.*)",',resp).group(1) # 图片存放的地方，是动态变化的。
        img_url_head="http://img.sslibrary.com"+jpgpath
        DownloadCore(img_url_head+"000001?zoom=%s"%Zoom,'test') # 感觉不在这里赶紧下载一下，就会下载不了，推测是加入了自动刷新防爬虫@221005
        os.remove('./RAW/test.png')
    except:
        anError("出问题，好像被反爬虫干了")
    

    bookname=re.search(r'"bookinfo".*>(.*)<',resp).group(1)

    xmlpath=re.search(r'id="ztree" param="(.*)" ',resp).group(1)
    xmlurl=xmlpath.replace('/cat/cat2xml.dll?','http://path.sslibrary.com/cat/cat2xml.dll?') # 目录xml所在的地方
    xml_r=requests.get(xmlurl,my_headers)
    contents_xml=xml_r.content.decode('utf-8')
    with open('[目录]'+bookname+'.xml','w') as f:
        f.write(contents_xml)

    page_info=re.search(r'var pages = \[(.*)\]',resp).group(1) #页数信息
    page_info2find=re.finditer(r'\[\d+, \d+\]',page_info)
    page_mins=[]
    page_maxes=[]
    page_amount=[]
    for match in page_info2find:
        #print(match.group())
        min_num=re.search(r'(\d+),',match.group()).group(1)
        page_mins.append(int(min_num))
        max_num=re.search(r', (\d+)',match.group()).group(1)
        page_maxes.append(int(max_num))
        page_amount.append(int(max_num)-int(min_num)+1)
    type_dict={'cov':(min(page_mins[7],1),max(page_maxes[7],1),max(page_amount[7],page_maxes[7],1)),  #封面
                'bok':(page_mins[1],page_maxes[1],page_amount[1]),        #书名页
                'leg':(page_mins[2],page_maxes[2],page_amount[2]),        #版权页
                'fow':(page_mins[3],page_maxes[3],page_amount[3]),        #前言
                "!00":(page_mins[4],page_maxes[4],page_amount[4]),        #目录
                '000':(page_mins[5],page_maxes[5],page_amount[5])}        #正文
    print("获取信息成功，书名：["+bookname+"]，即将开始下载……")
    return [bookname, img_url_head, type_dict, contents_xml]

def DownloadCore(img_url,name):
    img=requests.get(img_url,my_headers)
    if img.status_code!=200:
        anError("下载页%s图片被拒！错误代码：%d。请确保在网页上点「放大」能出页面，并稍候再试。要是老不行，您可能被ban了。"%(name,img.status_code))
    img_pic=Image.open(BytesIO(img.content))
    resol_bad=img_pic.width<800 #尺寸太小了说明有问题

    #固定页面宽度为18cm（7.09inch）的话，dpi应该就是img_pic.width/7.09
    dpi_set=img_pic.width/7.09
    img_pic.save("./RAW/%s.png"%name,dpi=(dpi_set,dpi_set))
    size=os.path.getsize("./RAW/%s.png"%name)
    page_bad= size==18628 or size==18649 #「数据加载失败」页面的大小为18628 B

    result_bad=resol_bad or page_bad
    return result_bad

def Redownload(PageToRedownload,interval):
    success=[]
    retry=1
    while len(PageToRedownload)>len(success):
        print("\n第 %d/%d 轮重新下载……"%(retry,max_reretry)+"（待下载：%d 页）"%(len(PageToRedownload)-len(success)))
        for name in PageToRedownload:
            if name in success:
                continue
            img_url=PageToRedownload[name]
            if retry>max_retry-1:
                img_url=img_url.replace("zoom=3","zoom=2")
                print("尝试以zoom=2下载……",end="")
            result_bad=DownloadCore(img_url,name)
            if result_bad:
                print("第%s页还是失败，待会儿再试……"%name)
            else:
                print("第%s页重新下载成功……"%name)
                success.append(name)
            time.sleep(interval) #慢一点免得被ban
        if retry>max_retry:
            print("多次重新下载失败！请检查网络或考虑改小zoom！\n总之接下来把已下下来的文件合并输出了……")
            break
        retry+=1
        print("冷却 %d 秒……"%(5*retry))
        time.sleep(5*retry)
    return 0

def Download(img_url_head,type_dict,Zoom,interval):
    all_pages=0
    for type in type_dict:
        all_pages+=type_dict[type][2]
    index=1
    retry=0
    PageToRedownload={}
    
    for type in type_dict:  #开干！
        page_min=type_dict[type][0]
        page_max=type_dict[type][1]
        page=page_min
        while page<=page_max:
            page_str=type+"%03d"%page   #当前页地址
            if type=='cov':  #封面还是保留彩色吧   
                img_url=img_url_head+page_str+"?zoom=2"                 
            elif type=='000':   #万一正文超过1000页
                img_url=img_url_head+"%06d"%page+"?zoom="+Zoom
            else:
                img_url=img_url_head+page_str+"?zoom="+Zoom
            
            name="%04d(%s)"%(index,page_str)
            result_bad=DownloadCore(img_url,name)
            time.sleep(interval) #慢一点免得被ban

            if result_bad: #出问题，尝试重新下载
                retry=retry+1
                if retry<=max_retry:
                    if retry==1:
                        print("\n", end="")
                    print("\r页%s访问受阻，%d秒后尝试第 %d/%d 次重新下载……"%(name,3,retry,max_retry), end="")
                    time.sleep(3)
                else:
                    # raise Exception("第%06d页("%index+page_str+")访问失败，下载终止，请检查网络或考虑降低zoom。")
                    print("页%s访问失败，待会儿再下（或请考虑降低zoom）……"%name)
                    PageToRedownload[name]=img_url
                    page=page+1
                    index=index+1
                    retry=0           
            else:   #没问题就收入并下一页
                # pdf_out=AddAPage(pdf_out,"./RAW/%06d.pdf"%index)
                if retry!=0:
                    print("重新下载成功……")
                    retry=0  
                ProgressBar(index,all_pages)
                page=page+1
                index=index+1
                           
    Redownload(PageToRedownload, interval) #集中重新下载之前下载失败的页
    return 0

def SelectDownload(img_url_head,type_dict,Zoom,interval):
    print("\n获取到的书籍页数信息如下：")
    print("类型\t起页码\t止页码\t总页数")
    print("-------------------------------------------")
    print("封面\t%d\t%d\t%d"%(type_dict['cov'][0],type_dict['cov'][1],type_dict['cov'][2]))
    print("书名页\t%d\t%d\t%d"%(type_dict['bok'][0],type_dict['bok'][1],type_dict['bok'][2]))
    print("版权页\t%d\t%d\t%d"%(type_dict['leg'][0],type_dict['leg'][1],type_dict['leg'][2]))
    print("前言\t%d\t%d\t%d"%(type_dict['fow'][0],type_dict['fow'][1],type_dict['fow'][2]))
    print("目录\t%d\t%d\t%d"%(type_dict['!00'][0],type_dict['!00'][1],type_dict['!00'][2]))
    print("正文\t%d\t%d\t%d"%(type_dict['000'][0],type_dict['000'][1],type_dict['000'][2]))
    print("")

    type_pages_selected=dict(type_dict)
    choose=input("要下载非正文部分(封面、书名页、版权页、前言、目录)吗？（y/n）:")
    if choose=='n': # 如果不下载其它部分，那么它们的page_selected置空，即不下载。
        for type in type_pages_selected:
            type_pages_selected[type]=[]
        print("不下载非正文部分，确认。\n")
    else: # 要下载的话，就把页码罗列出来
        for type in type_pages_selected:
            type_pages_selected[type]=list(range(type_dict[type][0],type_dict[type][1]+1))
        print("要下载非正文部分，确认。\n")
    
    print("下面选择要下载的正文页...")
    print("正文页码以网页上显示的为准，范围：%d-%d"%(type_dict['000'][0],type_dict['000'][1]))
    print("输入格式：举例，「1-3,15,20-22」表示要下载[1,2,3,15,20,21,22]这些页")
    the_pages_raw=input("输入要下载的正文的页码：")
    pages_cache=the_pages_raw.split(',')
    the_pages=[]
    for item in pages_cache:
        item_cache=item.split('-')
        if len(item_cache)==2: # 此时item_cache形如['20','22']
            the_pages.extend(range(int(item_cache[0]),int(item_cache[1])+1))
        else: # 此时item_cache形如['15']
            the_pages.append(int(item_cache[0]))
    print("已选定的要下载的正文页码为："+str(the_pages))
    print("即将开始下载……")
    type_pages_selected['000']=the_pages

    all_pages=0 # 总页数
    for type in type_pages_selected:
        all_pages+=len(type_pages_selected[type])

    # 开始下载
    index=1
    retry=0
    PageToRedownload={}
    for type in type_pages_selected:
        for page in type_pages_selected[type]:
            page_str=type+"%03d"%page   #当前页地址
            if type=='cov':  #封面还是保留彩色吧   
                img_url=img_url_head+page_str+"?zoom=2"                 
            elif type=='000':   #万一正文超过1000页
                img_url=img_url_head+"%06d"%page+"?zoom="+Zoom
            else:
                img_url=img_url_head+page_str+"?zoom="+Zoom
        
            name=page_str
            result_bad=DownloadCore(img_url,name)
            time.sleep(interval) #慢一点免得被ban

            if result_bad: #出问题，尝试重新下载
                retry=retry+1
                if retry<=max_retry:
                    if retry==1:
                        print("\n", end="")
                    print("\r页%s访问受阻，%d秒后尝试第 %d/%d 次重新下载……"%(name,3,retry,max_retry), end="")
                    time.sleep(3)
                else:
                    print("页%s访问失败，待会儿再下（或请考虑降低zoom）……"%name)
                    PageToRedownload[name]=img_url
                    # page=page+1
                    index=index+1
                    retry=0           
            else:   #没问题就收入并下一页
                if retry!=0:
                    print("重新下载成功……")
                    retry=0  
                ProgressBar(index,all_pages)
                # page=page+1
                print(name,index)
                index=index+1
                

    Redownload(PageToRedownload, interval) #集中重新下载之前下载失败的页
    return 0


def AddContents(pdf_file,type_dict,contents_xml):
    #加目录
    print("添加目录……")
    sys.stdout.flush()
    time.sleep(0.01)
    pdf_in=PdfFileReader(pdf_file)
    pdf_out=PdfFileWriter()
    for page in range(pdf_in.numPages):
        pdf_out.addPage(pdf_in.getPage(page))
    
    parent_id=[0, 0, 0, 0]
    parent_id[0]=pdf_out.addBookmark("封面",0,parent=None)
    parent_id[0]=pdf_out.addBookmark("版权页",0+type_dict['bok'][2]+type_dict['cov'][2],parent=None)
    parent_id[0]=pdf_out.addBookmark("前言",0+type_dict['bok'][2]+type_dict['cov'][2]+type_dict['leg'][2],parent=None)
    parent_id[0]=pdf_out.addBookmark("目录",0+type_dict['bok'][2]+type_dict['cov'][2]+type_dict['leg'][2]+type_dict['fow'][2],parent=None)
    
    mainbody_start=0+type_dict['bok'][2]+type_dict['cov'][2]+type_dict['leg'][2]+type_dict['fow'][2]+type_dict['!00'][2]
    #offset=sum(type_dict.values())-type_dict['000']   #xml里的页码是从正文开始的，所以与pdf页码有个偏移
    for match in re.finditer(r'id=.*?InsertPageNumber',contents_xml):   #提取一条目录数据
        index=re.search(r'id="(.*?)"',match.group()).group(1)
        caption=re.search(r'Caption="(.*?)"',match.group()).group(1)
        pagenumber=re.search(r'PageNumber="(.*?)"',match.group()).group(1)
        pagenumber=int(pagenumber)-type_dict['000'][0]+mainbody_start #python里页码是从0开始的

        for level in list(range(4)):
            if index.count('-')==level: #数index字符串里的横杠来判断层级，不太优雅但works
                # print('\t'*level+caption+'\t'+pagenumber)
                if level==0 or parent_id[level-1]==0:
                    parent_id[level]=pdf_out.addBookmark(caption,pagenumber,parent=None)
                else:
                    parent_id[level]=pdf_out.addBookmark(caption,pagenumber,parent=parent_id[level-1])
    
    return pdf_out

def Compress(cover_pages,files_to_cmprs,cmpresd_dir):

    list_of_pages=sorted(glob.glob(files_to_cmprs))

    all_pages=len(list_of_pages)

    for index in range(all_pages):
        if index<=cover_pages-1: #封面保持彩色
            # cv2.imwrite("./RAW/cmpresd/%06d.jpeg"%index,img_cv,[int(cv2.IMWRITE_JPEG_QUALITY),85])
            imgdata=Image.open(list_of_pages[index])
            dpi_set=imgdata.width/7.09  #固定页面宽度为18cm（7.09inch）的话，dpi应该就是img.width/7.09
            imgdata.save(cmpresd_dir+"%04d.jpg"%index, optimize=True, quality=85, dpi=(dpi_set,dpi_set))
        else:
            img_cv=cv2.imread(list_of_pages[index])
            height, width, channels = img_cv.shape
            if width<3000:
                img_cv=cv2.resize(img_cv,(3000,round(height*3000/width)),interpolation=cv2.INTER_LANCZOS4)
            # 二值化
            # blurred = cv2.GaussianBlur(img_cv, (1, 1), 0) #涂抹降噪，不想涂抹的话改成(1,1)
            gray=cv2.cvtColor(img_cv ,cv2.COLOR_BGR2GRAY)
            binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 81, 20)
            # cv2.imwrite("./RAW/cmpresd/%06d.png"%index,binary,[cv2.IMWRITE_PNG_BILEVEL, 1, int(cv2.IMWRITE_PNG_COMPRESSION),9])
            img_pil=Image.fromarray(binary)
            imgdata=img_pil.convert('1')
            dpi_set=imgdata.width/7.09  #固定页面宽度为18cm（7.09inch）的话，dpi应该就是img.width/7.09
            imgdata.save(cmpresd_dir+"%04d.tiff"%index, format="TIFF", compression="group4",dpi=(dpi_set,dpi_set))

        ProgressBar(index,all_pages)

def WritePDF(pdf_name,files_to_save,type_dict, contents_xml):
    print("合成……",end="")
    sys.stdout.flush()
    time.sleep(0.01)
    with open("temp.pdf", "wb+") as pdf_temp:
        pdf_temp.write(img2pdf.convert(sorted(glob.glob(files_to_save))))   #合成pdf，用sorted保证排序
        with open(pdf_name, "wb+") as pdf_file:
            pdf_out=AddContents(pdf_temp, type_dict, contents_xml)    #加目录
            pdf_out.write(pdf_file)                                     #输出 
    os.remove("temp.pdf")
    base_path=os.getcwd().replace('\\','/')
    print("已保存到： "+base_path+ '/'+pdf_name)


def main():
    global Zoom,interval,max_retry,max_reretry
    print("Download_SS_PDF-ver1.8, by DertahSama, 2022.10.5")
    print("这是一个从超星图书馆（http://www.sslibrary.com ）下载PDF并且自动添加目录和压缩、并且支持选页下载的python脚本，然后打包成了exe。")
    print("本项目地址：https://github.com/DertahSama/Download_SS_PDF \n")
    #一点准备工作
    if os.path.exists('./RAW'):    #清空存下载数据的RAW文件夹
        shutil.rmtree('./RAW')
    os.mkdir('./RAW')
    os.mkdir("./RAW/cmpresd")

    # 获取信息
    [bookname, img_url_head, type_dict, contents_xml]=GetData()
    
    choose=input("（当前清晰度：zoom="+Zoom+"，当前下载间隔：%.1f s）"%interval+"要额外修改吗？(y修改，回车不改)：")
    if choose=="y":
        Zoom=input(">> 清晰度zoom（可保留彩色的2，或最清晰的3）=")
        interval=float(input(">> 下载间隔interval(秒，默认为1.0)="))
        print("（当前清晰度：zoom="+Zoom+"，当前下载间隔：%.1f s）"%interval)

    
    choose1=input("全书下载(回车) or 选页下载(s)？：")
    if choose1=='':
        #下载每页图片
        Download(img_url_head, type_dict, Zoom, interval)
        #合成、加目录
        WritePDF(bookname+".pdf","./RAW/*.*", type_dict, contents_xml)

        choose=input("\n要压缩PDF到纯黑白吗？可大大减小文件体积(回车确定，n取消)：")
        if choose=="":
            Compress(type_dict['cov'][2],"./RAW/*.*","./RAW/cmpresd/")
            WritePDF("[黑白]"+bookname+".pdf","./RAW/cmpresd/*.*", type_dict, contents_xml)

        input("完成，按任意键退出。")

    else:
        SelectDownload(img_url_head,type_dict,Zoom,interval)
        input("完成，请自行按需合成PDF，按任意键退出。")

    

if __name__ == '__main__':
    main()
