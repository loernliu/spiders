import os
import re
import csv
import requests
from lxml import etree
from urllib import parse

class Tieba(object):
    '贴吧爬虫，负责爬取该吧中的相关信息'
    def __init__(self,name):
        self.name=name
        strName=parse.quote(name) # 对吧名进行url编码
        self.url='http://tieba.baidu.com/f?kw='+strName+'&ie=utf-8'

    def getBaseInfo(self):
        '爬取该吧的基础信息'
        r=requests.get(self.url)
        html=etree.HTML(r.content.decode('UTF-8'))
        pages=html.xpath('//*[@id="frs_list_pager"]/a[11]/@href')[0] # 获取该吧总共有多少页
        pn_r='&pn=[0-9]*'
        pn_c=re.compile(pn_r)
        pn=pn_c.findall(pages)[0][4:]
        members=html.xpath('//*[@class="card_num"]/span/span[2]/text()')[0]# 获取本吧的关注者数量
        baseInfo={
            'pn':pn,
            'nums':members
        }
        return baseInfo

    def getMembersInfo(self,pn):
        '获取本吧会员信息'
        gbkUrl=parse.quote(self.name,encoding='gbk') # 对吧名进行gbk编码
        url='http://tieba.baidu.com/bawu2/platform/listMemberInfo?word='+gbkUrl+'&pn='+str(pn)
        r=requests.get(url)
        html=etree.HTML(r.content.decode('gbk'))
        users=html.xpath('//*[@id="container"]/div[3]/span') # 用户相关信息在sapn中
        membersInfo=[]
        for e in users:
            href=e.xpath('./a/@href')[0]
            userUrl='http://tieba.baidu.com'+href # 构建用户主页链接
            res=requests.get(userUrl)

            try:
                root=etree.HTML(res.content.decode('utf-8'))
            except UnicodeDecodeError: # 已被删除的用户
                userInfo=['用户名:删除','吧龄：','发帖：','']
                sex=2
            else:
                userInfo=root.xpath('//*[@id="userinfo_wrap"]/div[2]/div[3]/div//text()') # 用户的相关信息
                try:
                    userSex=root.xpath('//*[@id="userinfo_wrap"]/div[2]/div[3]/div/span[1]/@class')[0] # 性别
                except IndexError: # 已经被屏蔽的用户
                    userInfo=['用户名:屏蔽','吧龄：','发帖：','']
                    sex=2
                else:
                    if userSex[26:]=='male':
                        sex=1
                    if userSex[26:]=='female':
                        sex=0
            userName=userInfo[0][4:] # 用户名
            years=userInfo[1][3:]    # 吧龄
            ties=userInfo[2][3:]     # 发帖数
            temp={
                'name':userName,
                'years':years,
                'ties':ties,
                'sex':sex
            }
            membersInfo.append(temp)
        return membersInfo

    def getTieInfo(self,pn):
        '爬取每一页帖子的回复数，标题，tid'
        url=self.url+'&pn='+str(pn)
        r=requests.get(url)
        html=etree.HTML(r.content.decode('UTF-8'))
        li=html.xpath('//*[@id="thread_list"]/li') # 一个li标签就是一个帖子
        if pn==0:
            index=1 # 第0页有置顶帖子，从li[1]开始才是普通帖子
        else:
            index=0 # 
        infoList=[]
        for i in range(index,len(li)):
            reply_num=li[i].xpath('./div/div[1]')[0].xpath('string(.)') # 某贴的回复数
            title=li[i].xpath('./div/div[2]/div[1]/div[1]/a[1]/@title')[0] # 某贴的标题
            tid=li[i].xpath('./div/div[2]/div[1]/div[1]/a[1]/@href')[0][3:] # 某贴的tid

            tempDir={
                'reply_num':int(reply_num),
                'title':title,
                'tid':tid
            }
            infoList.append(tempDir)
        return infoList


class Tiezi(object):
    '''帖子爬虫，负责爬每个贴子的数据'''

    def __init__(self,tid,pn):
        '''http://tieba.baidu.com/p/tid?pn=1 tid为帖子编号，pn为页码'''
        self.tid=tid
        self.pn=pn
    
    def getBaseInfo(self):
        '''获取该贴的基础信息'''
        url='http://tieba.baidu.com/p/'+str(self.tid)+'?pn='+str(self.pn) #构建帖子的url
        r=requests.get(url)
        html=etree.HTML(r.content.decode('UTF-8')) # 将请求得到的内容转化为xpath可处理的html格式

        # 处理帖子被删除情况
        try:
            title=html.xpath('//*[@id="j_core_title_wrap"]/div[2]/h1/text()')[0] # 某个贴子的标题
        except IndexError:
            print('该贴已被删除')
        else:
            responsNum=html.xpath('//*[@id="thread_theme_5"]/div[1]/ul/li[2]/span[1]/text()')[0] # 回复贴的个数
            pages=html.xpath('//*[@id="thread_theme_5"]/div[1]/ul/li[2]/span[2]/text()')[0] # 该贴的页数
            divs=html.xpath('//*[@id="j_p_postlist"]/div') # divs集合的元素是<Element div at 0x3316fa8>，每一个div都是一层楼，所有的信息都在里面
            baseInfo={
                "html":html,
                "title":title,
                "responseNum":responsNum,
                "pages":pages,
                "divs":divs
            }
            return baseInfo

    def getFloorBaseInfo(self,div):
        '''获取每层楼的基本数据'''
        userName=div.xpath('./div[2]/ul/li[@class="d_name"]/a//text()')[0] # 发帖人
        text=div.xpath('./div[3]/div[1]/cc/div[2]//text()') # 每层楼的内容
        data_field=div.xpath('./@data-field')[0] # 该楼层的相关信息都在div标签的data-field属性里面
        byte=data_field.encode('UTF-8') # 将lxml.etree._ElementUnicodeResult类型转为为bytes类型
        string=str(byte,'UTF-8') # 将 bytes类型转为string

        # 构建正则表达式
        post_id_r='"post_id":[0-9]*,'
        post_no_r='"post_no":[0-9]*'  # 楼层号
        date_r='"date":"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}"' # 发帖时间 
        comment_num_r='"comment_num":[0-9]*,' # 回复数量，后面确定楼中楼是否翻页大有帮助

        # 编译这段正则表达式
        date_c=re.compile(date_r)
        post_no_c=re.compile(post_no_r)
        post_id_c=re.compile(post_id_r)
        comment_num_c=re.compile(comment_num_r)
        
        # 得到目标字符串，并简单截取来清洗格式
        date=date_c.findall(string)[0][8:-1]
        post_no=post_no_c.findall(string)[0][10:]
        post_id=post_id_c.findall(string)[0][10:]
        comment_num=int(comment_num_c.findall(string)[0][14:-1])

        # 计算楼中楼被分为几页，每页显示10条数据,0页表示没有回复,即没有楼中楼
        if comment_num==0:
            lzlPage=0
        elif comment_num<=10:
            lzlPage=1
        elif comment_num % 10==0:
            lzlPage=int(comment_num/10)
        else:
            lzlPage=int(comment_num/10)+1

        FloorBaseInfo={
            "userName":userName,
            "text":text,
            "date":date,
            "post_no":post_no, # 以上全部是本楼的信息

            "post_id":post_id, # 它用来构建楼中楼的url
            "lzlPage":lzlPage  # 楼中楼有几页
        }
        return FloorBaseInfo

    def getLZLInfor(self,pid,page):
        '''获取楼中楼特定页的数据'''
        # 构建楼中楼消息的url地址，并爬取数据
        lzlUrl='http://tieba.baidu.com/p/comment?tid='+str(self.tid)+'&pid='+str(pid)+'&pn='+str(page)
        r_lzl=requests.get(lzlUrl)
        root=etree.HTML(r_lzl.content.decode('UTF-8'))

        infoList=[]

        lis=root.xpath('//li') # 每一个li都代表一条评论
        for i in range(0,len(lis)-1):
            r_text=lis[i].xpath('./div[@class="lzl_cnt"]')[0].xpath('string(.)').replace(' ','') # 回复的评论信息

            r_list=r_text.split(':',1)
            user1=r_list[0]
            
            # 提取时间
            time_r='[0-9]{4}-[0-9]*-[0-9]*:[0-9]*回复'
            time_c=re.compile(time_r)
            time=time_c.findall(r_list[1])[0] # 此时的格式位'2019-3-2319:04回复'
            time1=time[0:-2] # 切除'回复'
            date=time1[0:-5]+' '+time1[-5:] # 格式化发帖时间

            r_text1=r_list[1].replace(time,'') # 该串中只有评论内容或者是user2+评论内容

            if(r_text1[0:2]=='回复'):
                s=r_text1.split(':',1)
                try:
                    user2=s[0][2:]
                    context=s[1]
                except IndexError:
                    user2=''
                    context=r_text1
            else:
                user2=''
                context=r_text1
            
            tempDir={
                'user1':user1,
                'user2':user2,
                'context':context,
                'date':date
            }
            infoList.append(tempDir)
            
        return infoList

if __name__ == "__main__":
    # 用户输入要爬的吧名即可
    tieba=Tieba('河南理工大学') #注意不要输入'吧'字
    print('#---------------------------------------------------------#')
    baseInfo=tieba.getBaseInfo()
    print('吧名:',tieba.name)
    print('尾页id:',baseInfo['pn'])

    # 将整个吧的帖子信息写入csv文件
    infoDir={'回复数':'','标题':'','Tid':''}
    with open(tieba.name+'吧.csv','a',newline='',encoding='utf-8-sig') as csvfile:
        w=csv.DictWriter(csvfile,fieldnames=infoDir)
        w.writeheader()
        for i in range(0,int(baseInfo['pn'])+50,50): #获取整个吧的信息
            TieInfo=tieba.getTieInfo(i) #获取每一页的贴子信息
            for e in TieInfo:
                w.writerow({
                    '回复数':e['reply_num'],
                    '标题':e['title'],
                    'Tid':e['tid']
                })
            print('...')
            w.writerow({})
            print(i,' 成功写入文件')


    # 从csv文件中读取tid，爬取每个帖子的具体信息
    DstDir = os.getcwd()+"/tiezi/"
    with open(tieba.name+'.csv','r',encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        column2 = [row[2] for row in reader]
        #csv文件的第一行是属性名Tid,所以range从第二行开始
        for i in range(2964,3000): # 不要一次性遍历所有的tid,可以尝试每次爬几十个帖
            if(column2[i]!=''):
                tid=column2[i]
            pre = Tiezi(tid,1) # 初始化一个帖子
            preInfo=pre.getBaseInfo() # 帖子基本信息
            for pn in range(1,int(preInfo['pages'])+1):
                page=Tiezi(tid,pn)
                baseInfo=page.getBaseInfo()
                # print('标题：',baseInfo['title'])
                # print('回复数：',baseInfo['responseNum'])
                # print('页数：',baseInfo['pages'])
                # #print('楼层：',baseInfo['divs'],len(baseInfo['divs']),"个")
                # 写入csv文件   
                infoDir={'user1':'','user2':'','context':'','date':''}
                fileName=preInfo['title'].replace('.','').replace('/','')
                with open(DstDir+fileName+'.csv','a',newline='',encoding='utf-8-sig') as csvfile:
                    w=csv.DictWriter(csvfile,fieldnames=infoDir)
                    w.writeheader()

                    for e in baseInfo['divs']:
                        FloorBaseInfo=page.getFloorBaseInfo(e) # 每层楼的基本信息

                        #print('用户名：',FloorBaseInfo['userName'])
                        #print('内容：',FloorBaseInfo['text'])
                        #print('时间：',FloorBaseInfo['date'])
                        #print('楼层：',FloorBaseInfo['post_no'])
        
                        w.writerow({
                            'user1':FloorBaseInfo['userName'],
                            'user2':'',
                            'context':FloorBaseInfo['text'],
                            'date':FloorBaseInfo['date']
                        })

                        # 楼中楼
                        if FloorBaseInfo['lzlPage']!=0:
                            for i in range(1,FloorBaseInfo['lzlPage']+1):
                                lzlInfo=page.getLZLInfor(FloorBaseInfo['post_id'],i)
                                for j in lzlInfo:
                                    w.writerow({
                                        'user1':j['user1'],
                                        'user2':j['user2'],
                                        'context':j['context'],
                                        'date':j['date']
                                    })
                        w.writerow({})
                        print(FloorBaseInfo['post_no'],'楼成功写入文件') # 每层楼
                print(pn,'页成功写入文件') # 帖子的某页
            print(fileName,'成功写入文件') # 整个帖子