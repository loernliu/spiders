from selenium import webdriver
import time
import re
import requests
from urllib import parse
import qq_init as qq


class Spider(object):
    def __init__(self):
        self.ids = ''
        self.uins = ''
        self.driver = webdriver.Chrome()
        self.driver.get('https://i.qq.com/')
        self.__username = qq.USERNAME
        self.__password = qq.PASSWORD
        self.__receive_qq = qq.RECEIVE_MESSAGE_QQ
        self.headers = {
            'origin': 'https://user.qzone.qq.com',
            'referer': 'https://user.qzone.qq.com',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
        }
        self.req = requests.Session()
        self.cookies = {}

    def login(self):
        self.driver.switch_to.frame('login_frame')
        self.driver.find_element_by_id('switcher_plogin').click()
        self.driver.find_element_by_id('u').clear()
        self.driver.find_element_by_id('u').send_keys(self.__username)
        self.driver.find_element_by_id('p').clear()
        self.driver.find_element_by_id('p').send_keys(self.__password)
        self.driver.find_element_by_id('login_button').click()
        time.sleep(5)
        self.driver.implicitly_wait(2)
        cookie = ''
        for item in self.driver.get_cookies():
            cookie += item["name"] + '=' + item['value'] + ';'
        self.cookies = cookie
        self.get_qzonetoken(self.driver.page_source)
        self.get_g_tk()
        self.headers['Cookie'] = self.cookies
        self.driver.quit()

    def get_qzonetoken(self, page_source):
        '''
        window.g_qzonetoken = (function(){ try{return "fa5a1e1dc0673528864b564d6221f2342b97ef23b018372dcb36dfb49c49087efb8cd7652da9fe";} catch(e)
        '''
        self.qzonetoken = re.search(r'try{return\s"(\S+?)";', page_source).group(1)
        print('qzonetoken:{}'.format(self.qzonetoken))

    def get_g_tk(self):
        p_skey = self.cookies[self.cookies.find('p_skey=') + 7: self.cookies.find(';', self.cookies.find('p_skey='))]
        h = 5381
        for i in p_skey:
            h += (h << 5) + ord(i)
        print('g_tk', h & 2147483647)
        self.g_tk = h & 2147483647


    def add_board(self,num,content='haha'):
        url = 'https://h5.qzone.qq.com/proxy/domain/m.qzone.qq.com/cgi-bin/new/add_msgb?' + 'qzonetoken=' + str(self.qzonetoken) + '&g_tk=' + str(self.g_tk)
        data = {
            'content': str(content),
            'hostUin': self.__receive_qq,
            'uin': self.__username,
            'format': 'fs',
            'inCharset': 'utf-8',
            'outCharset': 'utf-8',
            'iNotice': '1',
            'ref': 'qzone',
            'json': '1',
            'g_tk': self.g_tk,
            'qzreferrer': 'https://user.qzone.qq.com/proxy/domain/qzs.qq.com/qzone/msgboard/msgbcanvas.html'
        }
        response = self.req.post(url, data=data, headers=self.headers)
        
        print(response.status_code)
        if '"message":"留言成功"' in response.text:
            print('第{}:{}留言成功'.format(num+1,content))
        else:
            with open('message', 'a+') as f:
                f.write(response.text + '\n\n')
            print('第{}:{}出错'.format(num+1,content))

if __name__ == '__main__':
    sp = Spider()
    sp.login()
    num = 0
    content = 'test'
    t = time.perf_counter()
    while num < 100:
        sp.add_board(num,content)
        time.sleep(4)
        num += 1
    End = time.perf_counter() - t
    print('{}条留言插入完成,共同用时{}'.format(num+1,End))
