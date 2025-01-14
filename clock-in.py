# -*- coding: utf-8 -*-

# 打卡脚修改自ZJU-nCov-Hitcarder的开源代码，感谢这位同学开源的代码

from traceback import print_tb
import requests
import json
import re
import datetime
import time
import sys
import random
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
import base64


# 保证兼容python2以及python3
IS_PY3 = sys.version_info.major == 3
if IS_PY3:
    from urllib.request import urlopen
    from urllib.request import Request
    from urllib.error import URLError
    from urllib.parse import urlencode
    from urllib.parse import quote_plus
else:
    import urllib2
    from urllib import quote_plus
    from urllib2 import urlopen
    from urllib2 import Request
    from urllib2 import URLError
    from urllib import urlencode

# 防止https证书校验不正确
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

API_KEY = 'mrxonS6pcI5LCn7NrtMRy0iu'

SECRET_KEY = 'BOezi8kqOSQFesxVCPoMBZQQ3EK4MT8s'


OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"


"""  TOKEN start """
TOKEN_URL = 'https://aip.baidubce.com/oauth/2.0/token'


my_sender='zbh11808@126.com'    # 发件人邮箱账号
my_user='921263166@qq.com'      # 收件人邮箱账号

class ClockIn(object):
    """Hit card class
    Attributes:
        username: (str) 浙大统一认证平台用户名（一般为学号）
        password: (str) 浙大统一认证平台密码
        login_url: (str) 登录url
        base_url: (str) 打卡首页url
        save_url: (str) 提交打卡url
        self.headers: (dir) 请求头
        sess: (requests.Session) 统一的session
    """

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.login_url = "https://zjuam.zju.edu.cn/cas/login?service=https%3A%2F%2Fhealthreport.zju.edu.cn%2Fa_zju%2Fapi%2Fsso%2Findex%3Fredirect%3Dhttps%253A%252F%252Fhealthreport.zju.edu.cn%252Fncov%252Fwap%252Fdefault%252Findex"
        self.base_url = "https://healthreport.zju.edu.cn/ncov/wap/default/index"
        self.save_url = "https://healthreport.zju.edu.cn/ncov/wap/default/save"
        self.code_url = "https://healthreport.zju.edu.cn/ncov/wap/default/code"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36"
        }
        self.sess = requests.Session()
        self.sess.keep_alive = False
    
    """
        获取token
    """
    def fetch_token(self):
        params = {'grant_type': 'client_credentials',
                'client_id': API_KEY,
                'client_secret': SECRET_KEY}
        post_data = urlencode(params)
        if (IS_PY3):
            post_data = post_data.encode('utf-8')
        req = Request(TOKEN_URL, post_data)
        try:
            f = urlopen(req, timeout=5)
            result_str = f.read()
        except URLError as err:
            print(err)
        if (IS_PY3):
            result_str = result_str.decode()


        result = json.loads(result_str)

        if ('access_token' in result.keys() and 'scope' in result.keys()):
            if not 'brain_all_scope' in result['scope'].split(' '):
                print ('please ensure has check the  ability')
                exit()
            return result['access_token']
        else:
            print ('please overwrite the correct API_KEY and SECRET_KEY')
            exit()

    """
        读取文件
    """
    def read_file(self, image_path):
        f = None
        try:
            f = open(image_path, 'rb')
            return f.read()
        except:
            print('read image file fail')
            return None
        finally:
            if f:
                f.close()


    """
        调用远程服务
    """
    def request(self, url, data):
        req = Request(url, data.encode('utf-8'))
        has_error = False
        try:
            f = urlopen(req)
            result_str = f.read()
            if (IS_PY3):
                result_str = result_str.decode()
            return result_str
        except  URLError as err:
            print(err)

    def login(self):
        """Login to ZJU platform"""
        res = self.sess.get(self.login_url, headers=self.headers)
        execution = re.search(
            'name="execution" value="(.*?)"', res.text).group(1)
        res = self.sess.get(
            url='https://zjuam.zju.edu.cn/cas/v2/getPubKey', headers=self.headers).json()
        n, e = res['modulus'], res['exponent']
        encrypt_password = self._rsa_encrypt(self.password, e, n)

        data = {
            'username': self.username,
            'password': encrypt_password,
            'execution': execution,
            '_eventId': 'submit'
        }
        res = self.sess.post(url=self.login_url, data=data, headers=self.headers)
        # print(res.content.decode())
        # check if login successfully
        if '统一身份认证' in res.content.decode():
            raise LoginError('登录失败，请核实账号密码重新登录')
        return self.sess

    def post(self):
        """Post the hitcard info"""
        res = self.sess.post(self.save_url, data=self.info, headers=self.headers)
        return json.loads(res.text)

    def get_date(self):
        """Get current date"""
        today = datetime.date.today()
        return "%4d%02d%02d" % (today.year, today.month, today.day)

    def get_info(self, html=None):
        """Get hitcard info, which is the old info with updated new time."""
        if not html:
            time.sleep(5)
            res = self.sess.get(self.base_url, headers=self.headers)
            html = res.content.decode()
#             res = self.sess.get(self.code_url, headers=self.headers)
#             with open('code.jpg', 'wb') as file:
#                 file.write(res.content)
#                 file.close
#             # codenum = input("请输入验证码：")

#             # 获取access token
#             token = self.fetch_token()
#             # 拼接通用文字识别高精度url
#             image_url = OCR_URL + "?access_token=" + token
#             text = ""
#             # 读取测试图片
#             file_content = self.read_file('./code.jpg')
#             # 调用文字识别服务
#             result = self.request(image_url, urlencode({'image': base64.b64encode(file_content)}))
#             result_json = json.loads(result)
#             for words_result in result_json["words_result"]:
#                 text = text + words_result["words"]
#                 print(text)
            



        try:
            old_infos = re.findall(r'oldInfo: ({[^\n]+})', html)
            if len(old_infos) != 0:
                old_info = json.loads(old_infos[0])
            else:
                raise RegexMatchError("未发现缓存信息，请先至少手动成功打卡一次再运行脚本")

            new_info_tmp = json.loads(re.findall(r'def = ({[^\n]+})', html)[0])
            new_id = new_info_tmp['id']
            name = re.findall(r'realname: "([^\"]+)",', html)[0]
            number = re.findall(r"number: '([^\']+)',", html)[0]
        except IndexError:
            raise RegexMatchError('Relative info not found in html with regex')
        except json.decoder.JSONDecodeError:
            raise DecodeError('JSON decode error')

        new_info = old_info.copy()
        new_info['id'] = new_id
        new_info['name'] = name
        new_info['number'] = number
        new_info["date"] = self.get_date()
        new_info["created"] = round(time.time())
        new_info["address"] = "浙江省杭州市西湖区"
        new_info["area"] = "浙江省 杭州市 西湖区"
        new_info["province"] = new_info["area"].split(' ')[0]
        new_info["city"] = new_info["area"].split(' ')[1]
        # form change
        new_info['jrdqtlqk[]'] = 0
        new_info['jrdqjcqk[]'] = 0
        new_info['sfsqhzjkk'] = 1   # 是否申领杭州健康码
        new_info['sqhzjkkys'] = 1   # 杭州健康吗颜色，1:绿色 2:红色 3:黄色
        new_info['sfqrxxss'] = 1    # 是否确认信息属实
        new_info['jcqzrq'] = ""
        new_info['gwszdd'] = ""
        new_info['szgjcs'] = ""
#         new_info['verifyCode'] = text

        # 2021.08.05 Fix 2
        magics = re.findall(r'"([0-9a-f]{32})":\s*"([^\"]+)"', html)
        for item in magics:
            new_info[item[0]] = item[1]

        self.info = new_info
        return new_info

    def _rsa_encrypt(self, password_str, e_str, M_str):
        password_bytes = bytes(password_str, 'ascii')
        password_int = int.from_bytes(password_bytes, 'big')
        e_int = int(e_str, 16)
        M_int = int(M_str, 16)
        result_int = pow(password_int, e_int, M_int)
        return hex(result_int)[2:].rjust(128, '0')


# Exceptions
class LoginError(Exception):
    """Login Exception"""
    pass


class RegexMatchError(Exception):
    """Regex Matching Exception"""
    pass


class DecodeError(Exception):
    """JSON Decode Exception"""
    pass

def mail():
    ret=True
    try:
        msg=MIMEText('今日打卡失败','plain','utf-8')
        msg['From']=formataddr(["zbh11808",my_sender])  # 括号里的对应发件人邮箱昵称、发件人邮箱账号
        msg['To']=formataddr(["921263166",my_user])              # 括号里的对应收件人邮箱昵称、收件人邮箱账号
        msg['Subject']="今日打卡失败"                # 邮件的主题，也可以说是标题
 
        server=smtplib.SMTP_SSL("smtp.126.com", 465)  # 发件人邮箱中的SMTP服务器，SSL端口是465
        server.login(my_sender, my_pass)  # 括号中对应的是发件人邮箱账号、邮箱密码
        server.sendmail(my_sender,[my_user,],msg.as_string())  # 括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
        server.quit()  # 关闭连接
    except Exception:  # 如果 try 中的语句没有执行，则会执行下面的 ret=False
        ret=False
    return ret

def main(username, password):
    """Hit card process
    Arguments:
        username: (str) 浙大统一认证平台用户名（一般为学号）
        password: (str) 浙大统一认证平台密码
    """
    delay_time = random.randint(0,3000)
    print("任务将在%d秒后执行" % delay_time)
    #time.sleep(delay_time)
    
    print("\n[Time] %s" %
          datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("🚌 打卡任务启动")

    dk = ClockIn(username, password)

    print("登录到浙大统一身份认证平台...")
    try:
        dk.login()
        print("已登录到浙大统一身份认证平台")
    except Exception as err:
        print(str(err))
        raise Exception

    print('正在获取个人信息...')
    try:
        dk.get_info()
        print('已成功获取个人信息')
    except Exception as err:
        print('获取信息失败，请手动打卡，更多信息: ' + str(err))
        raise Exception

    print('正在为您打卡')
    try:
        res = dk.post()
        if str(res['e']) == '0':
            print('已为您打卡成功！')
        else:
            print(res['m'])
            if res['m'].find("已经") != -1: # 已经填报过了 不报错
                pass
            else:
                raise Exception
    except Exception:
        print('数据提交失败')
        raise Exception


if __name__ == "__main__":
    username = sys.argv[1]
    password = sys.argv[2]
    my_pass = str(sys.argv[3])
    try:
        main(username, password)
    except Exception:
        ret=mail()
        if ret:
            print("邮件发送成功")
        else:
            print("邮件发送失败")
        exit(1)
