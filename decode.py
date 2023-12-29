
import os
import xml.etree.ElementTree as ET
import hashlib
import re
def md5_encrypt(text):
    md5 = hashlib.md5()
    md5.update(text.encode('utf-8'))
    return md5.hexdigest()

def contains_chinese(s):
    for char in s:
        if '\u4e00' <= char <= '\u9fff':
            return True
    return False


import argparse

parser = argparse.ArgumentParser(description="调用sqlcipher解码数据库")
parser.add_argument("-d", "--dataset_path",default="E:/(com.tencent.mm)/apps/com.tencent.mm/r/MicroMsg/67fec1410543c5ff6ea9ab25bc770ac0",
                help="数据库位置")
parser.add_argument("-u", "--uid_path",default="E:/(com.tencent.mm)/apps/com.tencent.mm/sp",
                help="uid位置")
args = parser.parse_args()

dataset_path = args.dataset_path #"2023.1.1"
decode_path = args.uid_path#"2023.12.31"
if contains_chinese(dataset_path):
    print("不支持路径存在中文")
    exit()
if contains_chinese(decode_path):
    print("不支持路径存在中文")
    exit()

uid_path = os.path.join(decode_path, "auth_info_key_prefs.xml")
dataset_file = os.path.join(dataset_path, "EnMicroMsg.db")
decode_file_path = os.path.join(dataset_path, "EnMicroMsg_plain.db")

tree = ET.parse(uid_path)
root = tree.getroot()
UID = root.find('.//int').get('value')
IMEI = "1234567890ABCDEF"
passwd = md5_encrypt(IMEI+UID)[:7]
print(passwd)

import wexpect
child = wexpect.spawn(f'./sqlcipher-shell64.exe {dataset_file}')
line = child.readline()
print(line)
line = child.readline()
print(line)
line = child.readline()
print(line)
print(dataset_file)
def input_to_progress(txt):
    child.sendline(txt)
    child.expect(re.compile(".+"), timeout=1200)
    line = child.readline()
    print(line)
    return line
input_to_progress(f"PRAGMA key = '{passwd}';\n") #PRAGMA key = '34d51b3';
input_to_progress(f"PRAGMA cipher_use_hmac = OFF;\n")
input_to_progress(f"PRAGMA cipher_page_size = 1024;\n")
input_to_progress(f"PRAGMA kdf_iter = 4000;\n")
input_to_progress(f"PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA1;\n")
input_to_progress(f"ATTACH DATABASE '{decode_file_path}' AS wechatdecrypted KEY '';\n")
input_to_progress(f"SELECT sqlcipher_export( 'wechatdecrypted' );\n")
print("正在解密数据库，可能需要5分钟")
input_to_progress(f"DETACH DATABASE wechatdecrypted;\n")
if not os.path.exists(decode_file_path) or os.path.getsize(decode_file_path) == 0:
    print("失败了，请手动解码数据库")
else:
    print("解码完成")
child.close()