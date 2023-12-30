import sqlite3
import os
import xml.etree.ElementTree as ET
import io
import re
import copy
from util import *
from tqdm import tqdm


type_2_message = {
    1: {"name":"文字信息", "content":[]},# "content":["时间", "发送id", "内容"]
    822083633:{"name":"引用消息",},
    3: {"name":"图片", 'content': []}, # content":["时间", "发送id","imgPath","msgId"]
    1048625: {"name":"图片"},
    34: {"name":"语音",'content': []}, # content":["时间", "发送id","语音时长(ms)","imgPath","msgId"]
    43: {"name":"视频",'content': []}, # content":["时间", "发送id","视频时长(s)","imgPath","msgId"]
    486539313: {"name":"视频"},
    47: {"name":"表情包",'content': []}, # content":["时间", "发送id","imgPath","msgId"]
    48: {"name":"定位",'content': []}, # content":["时间", "发送id","位置"]
    50: {"name":"微信通话",'content': []}, # content":["时间", "发送id","语言类型", "是否接通", "通话时间(s)"]
    64: {"name":"群语音通话",'content': []}, #content":["发起时间","结束时间"]
    10000: {"name":"撤回消息",'content': []}, #content":["时间", "发送id"]
    268445456: {"name":"撤回消息"}, #content":["时间", "发送id"]
    419430449: {"name":"转账",'content': []}, #content":["时间", "接收转账id", 钱数]
    436207665: {"name":"红包",'content': []}, #content":["时间", "发送id"]
    922746929: {"name":"拍一拍",'content': []}, #content":["时间", "拍人者", "被拍者"]
    1090519089: {"name":"文件",'content': []}, # content: ["时间", "发送id", file_name, file_len(KB)]
    -1879048186: {"name":"位置共享",'content': []}, #content":["时间", "发送id"]
    # 自己加的
    10086: {"name":"收款", 'content': []} #content":["时间", "发送id", 钱数]
}

# 获取所有联系人
def get_person_list():
    cursor = conn.cursor()
    cursor.execute("SELECT username,conRemark,nickname FROM rcontact \
                WHERE type NOT IN (4, 33, 0, 2, 8, 9, 10, 11, 33) and username NOT LIKE '%@chatroom%' and username NOT LIKE '%@app%' and verifyFlag=0;")
    # 不包含企业微信号的人可以添加username NOT LIKE '%@openim%'
    table_data = cursor.fetchall()
    res = []
    for row in table_data:
        res.append(row[0])
    cursor.close()
    return res

# 获取所有群聊
def get_room_list():
    cursor = conn.cursor()
    cursor.execute("SELECT chatroomname FROM chatroom where memberlist <> ''")
    # 不包含企业微信号的人可以添加username NOT LIKE '%@openim%'
    table_data = cursor.fetchall()
    res = []
    for row in table_data:
        res.append(row[0])
    cursor.close()
    return res

# 获取所有联系人
def get_wxid_to_info():
    cursor = conn.cursor()
    cursor.execute("SELECT username,conRemark,nickname,lvbuff FROM rcontact")
    # 不包含企业微信号的人可以添加username NOT LIKE '%@openim%'
    table_data = cursor.fetchall()
    res = {}
    for row in table_data:
        username,conRemark,nickname,lvbuff = row
        gender = int(lvbuff[8]) # 1男人 2女 0未知
        if conRemark == "":
            conRemark = nickname #None
        res[username] = {
            "conRemark": conRemark,
            "nickname": nickname,
            "gender": gender,
            "avator": get_avator(username, avator_path)
        }
    return res



from roomdata_pb2 import RoomData
def get_wxid_to_room_name(room_wxid):
    cursor = conn.cursor()
    cursor.execute(f"SELECT roomdata from chatroom WHERE chatroomname='{room_wxid}'")
    room_data = cursor.fetchall()
    room_data = room_data[0][0]
    cursor.close()
    person = RoomData()
    person.ParseFromString(room_data)
    wxid_to_room_name = {} # ["微信id", "群昵称"]
    for menber in person.members:
        wxid = menber.wxid
        room_name = menber.name
        if room_name == "":
            room_name = None
        wxid_to_room_name[wxid] = room_name
    return wxid_to_room_name

# 查询某人的wxid
def get_wxid(name):
    cursor = conn.cursor()
    # 先通过备注找人
    cursor.execute(f"SELECT username from rcontact WHERE conRemark like '%{name}%'")
    table_data = cursor.fetchall()
    if len(table_data) == 0: #如果备注没有
        cursor.execute(f"SELECT username from rcontact WHERE nickname like '%{name}%'")
        table_data = cursor.fetchall()
    
    cursor.close()
    if len(table_data) == 0:
        return None
    return table_data[0][0]

# 获取本人微信信息
def get_user_info(conn):
    cursor = conn.cursor()
    cursor.execute(f"SELECT value from userinfo WHERE id=2")
    table_data = cursor.fetchall()
    wxid = table_data[0][0]
    cursor.execute(f"SELECT value from userinfo WHERE id=4")
    table_data = cursor.fetchall()
    wx_name = table_data[0][0]
    wx_avator = get_avator(wxid, avator_path)
    cursor.close()
    return wxid, wx_name, wx_avator


# 查询所有聊天记录
def get_message_by_wxid(wxid, start_time=None, end_time=None):
    cursor = conn.cursor()
    if start_time is None:
        cursor.execute(f"SELECT type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId from message WHERE talker='{wxid}' ORDER by createTime")
    else:
        start_time = get_timestamp(start_time)
        end_time = get_timestamp(end_time)+999
        cursor.execute(f"SELECT type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId from message WHERE talker='{wxid}' AND createTime BETWEEN {start_time} AND {end_time} ORDER by createTime")
    table_data = cursor.fetchall()
    cursor.close()
    return table_data

# 处理文本
def handle_text(msgs):
    res = []
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row
        if msg_type == 1:
            res.append(
                [createTime, talker, content]
            )
        elif msg_type == 822083633:
            try:
                xml_tree = ET.parse(io.StringIO(content))
            except:
                content = content.replace("&#","")
                xml_tree = ET.parse(io.StringIO(content))
            root = xml_tree.getroot()
            ctx = root.find('.//title').text
            res.append(
                [createTime, talker, ctx]
            )
    return res

# 处理图片
def handle_pic(msgs):
    res = []
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row
        
        res.append([createTime, talker, imgPath, msgId])
    return res

# 处理语音
def handle_voice(msgs):
    res = []
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row
        
        tmp = content.split(":")
        voice_len = int(tmp[1])
        talker = tmp[0]
        res.append([createTime, talker, voice_len, imgPath, msgId])
    return res

# 处理视频
def handle_video(msgs):
    res = []
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row
        tmp = content.split(":")
        talker = tmp[0]
        video_len = int(tmp[1])
        res.append([createTime, talker, video_len, imgPath, msgId])
    return res

# 处理表情包
def handle_bimg(msgs):
    res = []
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row
        tmp = content.split(":")
        talker = tmp[0]
        res.append([createTime, talker, imgPath, msgId])
    return res

# 处理定位
def handle_pos(msgs):
    res = []
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row
        try:
            xml_tree = ET.parse(io.StringIO(content))
        except: #出现了群昵称
            ct_s = content.split("\n",1)
            talker = ct_s[0][:-1]
            content = ct_s[1]
            xml_tree = ET.parse(io.StringIO(content))

        root = xml_tree.getroot()
        pos = root.find('.//location').get('label')
        res.append([createTime, talker, pos])
    return res

# 处理通话
def handle_voip(msgs):
    res = []
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row

        text_data = lvbuffer.decode('utf-8')
        pattern = r'([\u4e00-\u9fff]+)(\s(?P<min>\d+)\:(?P<sec>\d+))?'
        cos_time = 0
        if content == "voip_content_voice":
            voip_type = 1 #0 视频通话 1语音通话
        else:
            voip_type = 0
        success_type = 0 #0挂断 1接听 2在其他设备接听
        matches = re.search(pattern, text_data)
        if matches is not None:
            matches = matches.groups()
            voip_type_name = matches[0]
            
            if (matches[2] is not None):
                min = int(matches[2])
                sec = int(matches[3])
                cos_time = min*60 + sec
                success_type = 1
            elif voip_type_name == "已在其它设备接听":
                success_type = 2
        res.append([createTime, talker, voip_type, success_type, cos_time])
    return res

# 处理群通话
def handle_rooom_voip(msgs):
    res = []
    start_time = 10000000#(ms)
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row

        if "语音通话已经结束" in content:
            res.append([start_time, createTime])
        elif "发起了语音通话" in content:
            start_time = createTime
            
    return res

# 处理撤回
def handle_back(msgs):
    res = []
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row

        if "撤回" in content:
            res.append([createTime, talker])
    return res

# 处理转账
def handle_transfer(msgs):
    res = []
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row

        xml_tree = ET.parse(io.StringIO(content))
        root = xml_tree.getroot()
        money_type = int(root.find('.//paysubtype').text)
        if money_type == 3:
            pattern = r'收到转账(\d+\.\d+)元'
            matches = re.search(pattern, content)
            money_value = float(matches.group(1))
            res.append([createTime, talker, money_value])

    return res

# 处理红包
def handle_hongbao(msgs):
    res = []
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row
        if "红包" in content:
            res.append([createTime, talker])
    return res

# 处理收款
def handle_collection(msgs):
    res = []
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row
        if "收款" in content:
            pattern = r'每人需支付(\d+\.\d+)元'
            matches = re.search(pattern, content)
            if matches is None:
                continue
            money_value = float(matches.group(1))
            res.append([createTime, talker, money_value])
    return res


# 处理拍一拍
def handle_pat(msgs, wxid):
    res = []
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row
        # pattern = r'<template><\!\[CDATA\[(?P<pat_from>我|自己|"\$\{(?P<pat_from_wxid>.*?)\})(\$\{fromusername@textstatusicon\})?"?\s?拍了拍\s?(?P<pat_to>"(?P<pat_to_name_or_wxid>.*?)\$\{pattedusername@textstatusicon\}|我|自己).*?</template>'
        # matches = re.search(pattern, content)
        # re_res = matches.groups()
        # pat_from = matches.group("pat_from").strip()
        # pat_to = matches.group("pat_to").strip()
        # if pat_from == "我" or pat_from == "自己":
        #     pat_from = self_wxid
        # else:
        #     pat_from = matches.group("pat_from_wxid")
        
        # if pat_to == "我":
        #     pat_to = self_wxid
        # elif pat_to == "自己":
        #     pat_to = pat_from
        # else:
        #     pat_to = matches.group("pat_to_name_or_wxid")
        #     patt = r'\$\{(.*?)\}'
        #     matches = re.search(patt, pat_to)
        #     if matches is not None: #是wxid
        #         pat_to = matches.group(1)
        #     else:
        #         pat_to = pat_to #这里要从备注或者群信息中找出对应的wxid
        # res.append([createTime, pat_from, pat_to])
        pattern = r'<template>(?!.*<template>.*)<\!\[CDATA\[(?P<pat_from>我|"\$\{(?P<pat_from_wxid>.*?)\})(\$\{fromusername@textstatusicon\})?"?\s?拍了拍\s?(?P<pat_to>"(?P<pat_to_name_or_wxid>.*?)\$\{pattedusername@textstatusicon\}|我|自己).*?</template>'
        matches = re.search(pattern, content)
        flag = False
        if matches is None:
            flag = True
            pattern = r'<template>(?!.*<template>.*)<\!\[CDATA\[(?P<pat_from>我|"\$\{(?P<pat_from_wxid>.*?)\})(\$\{fromusername@textstatusicon\})?"?\s?拍了拍\s?(?P<pat_to>"(?P<pat_to_name_or_wxid>.*?")|我|自己).*?</template>'
            matches = re.search(pattern, content)
        pat_from = matches.group("pat_from").strip()
        pat_to = matches.group("pat_to").strip()
        if pat_from == "我":
            pat_from = self_wxid
        else:
            pat_from = matches.group("pat_from_wxid")
        
        if pat_to == "我":
            pat_to = self_wxid
        elif pat_to == "自己":
            pat_to = pat_from
        else:
            pat_to = matches.group("pat_to_name_or_wxid")
            patt = r'\$\{(.*?)\}'
            matches = re.search(patt, pat_to)
            if matches is not None: #是wxid
                pat_to = matches.group(1)
            else: #这里要从备注或者群信息中找出对应的wxid
                pat_to = wxid 
        res.append([createTime, pat_from, pat_to])
    return res


# 处理群聊中的拍一拍
def handle_pat_room(msgs, name_to_wxid):
    res = []
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row
        # content = r'<template><![CDATA["${wxid_0mlzpvih1nrb22}${fromusername@textstatusicon}" 拍了拍 "${wxid_n1sum0ae6n9q21}${pattedusername@textstatusicon}" 的三公分巴别塔]]></template>'
        # content = r'<template><![CDATA[我${fromusername@textstatusicon}拍了拍"何燐${pattedusername@textstatusicon}"再拍了拍你]]></template>'
        # content = r'<template><![CDATA["${wxid_j1q59wuhl04122}" 拍了拍我的头后变成了🐷]]></template>'
        # content = r'<template><![CDATA["${wxid_26ddznwrvoe012}${fromusername@textstatusicon}" 拍了拍 "${wxid_ymgi743bs1v622}${pattedusername@textstatusicon}" 的头，喊我一声爹]]></template>'
        
        pattern = r'<template>(?!.*<template>.*)<\!\[CDATA\[(?P<pat_from>我|"\$\{(?P<pat_from_wxid>.*?)\})(\$\{fromusername@textstatusicon\})?"?\s?拍了拍\s?(?P<pat_to>"(?P<pat_to_name_or_wxid>.*?)\$\{pattedusername@textstatusicon\}|我|自己).*?</template>'
        matches = re.search(pattern, content)
        flag = False
        if matches is None:
            flag = True
            pattern = r'<template>(?!.*<template>.*)<\!\[CDATA\[(?P<pat_from>我|"\$\{(?P<pat_from_wxid>.*?)\})(\$\{fromusername@textstatusicon\})?"?\s?拍了拍\s?(?P<pat_to>"(?P<pat_to_name_or_wxid>.*?")|我|自己).*?</template>'
            matches = re.search(pattern, content)
        pat_from = matches.group("pat_from").strip()
        pat_to = matches.group("pat_to").strip()
        if pat_from == "我":
            pat_from = self_wxid
        else:
            pat_from = matches.group("pat_from_wxid")
        
        if pat_to == "我":
            pat_to = self_wxid
        elif pat_to == "自己":
            pat_to = pat_from
        else:
            pat_to = matches.group("pat_to_name_or_wxid")
            patt = r'\$\{(.*?)\}'
            matches = re.search(patt, pat_to)
            if matches is not None: #是wxid
                pat_to = matches.group(1)
            else: #这里要从备注或者群信息中找出对应的wxid
                if flag:
                    pat_to = pat_to[:-1]
                if pat_to in name_to_wxid:
                    pat_to = name_to_wxid[pat_to]
                else:
                    assert(False)
                    pat_to = None 
        res.append([createTime, pat_from, pat_to])
    return res

# 处理文件
def handle_file(msgs):
    res = []
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row
        xml_tree = ET.parse(io.StringIO(content))
        root = xml_tree.getroot()
        file_name = root.find('.//title').text
        file_len = int(root.find('.//totallen').text) / 1024 
        res.append([createTime, talker, file_name, file_len])
    return res

# 处理位置共享
def handle_share_pos(msgs):
    res = []
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row
        if msg_type == -1879048186:
            res.append([createTime, talker])
    return res


def get_know_time(wxid):
    cursor = conn.cursor()
    cursor.execute(f"SELECT type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId from message WHERE talker='{wxid}' ORDER by createTime LIMIT 10")
    # 不包含企业微信号的人可以添加username NOT LIKE '%@openim%'
    table_data = cursor.fetchall()
    cursor.close()
    first_time = None
    know_time = None
    for row in table_data:
        mgs_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row
        if first_time is None:
            first_time = createTime 
        if mgs_type == 1 and content == "我通过了你的朋友验证请求，现在我们可以开始聊天了":
            know_time = createTime
        elif mgs_type != 1 and content == "以上是打招呼的内容":
            know_time = createTime
        elif mgs_type !=1 and "你加入了群聊" in content:
            know_time = createTime
    return know_time, first_time

 # 处理某人的聊天记录
def handle_person_message(msgs, wx_id):
    res = copy.deepcopy(type_2_message)
    res[1]["content"] = handle_text(filter_by_type(msgs, [1, 822083633], self_wxid))
    res[3]["content"] = handle_pic(filter_by_type(msgs, [3, 1048625], self_wxid))
    res[34]["content"] = handle_voice(filter_by_type(msgs, [34], self_wxid))
    res[43]["content"] = handle_video(filter_by_type(msgs, [43], self_wxid))
    res[47]["content"] = handle_bimg(filter_by_type(msgs, [47], self_wxid))
    res[48]["content"] = handle_pos(filter_by_type(msgs, [48], self_wxid))
    res[50]["content"] = handle_voip(filter_by_type(msgs, [50], self_wxid))
    res[64]["content"] = handle_rooom_voip(filter_by_type(msgs, [64], self_wxid))
    res[10000]["content"] = handle_back(filter_by_type(msgs, [10000, 268445456],self_wxid))
    res[419430449]["content"] = handle_transfer(filter_by_type(msgs, [419430449],self_wxid))
    res[436207665]["content"] = handle_hongbao(filter_by_type(msgs, [436207665],self_wxid))
    res[10086]["content"] = handle_collection(filter_by_type(msgs, [436207665],self_wxid))
    res[922746929]["content"] = handle_pat(filter_by_type(msgs, [922746929],self_wxid), wx_id)
    res[1090519089]["content"] = handle_file(filter_by_type(msgs, [1090519089],self_wxid))
    res[-1879048186]["content"] = handle_share_pos(filter_by_type(msgs, [-1879048186],self_wxid))
    return res

# 处理群聊的消息
def handle_room_message(msgs, wxid_to_room_name, wxid_to_name):
    name_to_wxid = {}
    for key in wxid_to_room_name:
        name_to_wxid[wxid_to_room_name[key]] = key
    for key in wxid_to_name:
        if key in wxid_to_room_name:
            name_to_wxid[wxid_to_name[key]["conRemark"]] = key
    
    res = copy.deepcopy(type_2_message)

    res[1]["content"] = handle_text(filter_by_type_room(msgs, [1, 822083633], self_wxid))
    res[3]["content"] = handle_pic(filter_by_type_room(msgs, [3, 1048625], self_wxid))
    res[34]["content"] = handle_voice(filter_by_type(msgs, [34], self_wxid))
    res[43]["content"] = handle_video(filter_by_type(msgs, [43], self_wxid))
    res[47]["content"] = handle_bimg(filter_by_type(msgs, [47], self_wxid))
    res[48]["content"] = handle_pos(filter_by_type_room(msgs, [48], self_wxid))
    res[50]["content"] = handle_voip(filter_by_type(msgs, [50], self_wxid))
    res[64]["content"] = handle_rooom_voip(filter_by_type(msgs, [64], self_wxid))
    res[10000]["content"] = handle_back(filter_by_type(msgs, [10000, 268445456],self_wxid))
    res[419430449]["content"] = handle_transfer(filter_by_type_room(msgs, [419430449],self_wxid))
    res[436207665]["content"] = handle_hongbao(filter_by_type_room(msgs, [436207665],self_wxid))
    res[10086]["content"] = handle_collection(filter_by_type_room(msgs, [436207665],self_wxid))
    res[922746929]["content"] = handle_pat_room(filter_by_type(msgs, [922746929],self_wxid), name_to_wxid)
    res[1090519089]["content"] = handle_file(filter_by_type_room(msgs, [1090519089],self_wxid))
    res[-1879048186]["content"] = handle_share_pos(filter_by_type_room(msgs, [-1879048186],self_wxid))
    return res

def get_res_by_wxid(wxid, wxid_to_name):
    msgs = get_message_by_wxid(wxid, sta_start_time, sta_end_time)
    if "@chatroom" in wxid:
        wxid_to_room_name = get_wxid_to_room_name(wxid)
        res = handle_room_message(msgs, wxid_to_room_name, wxid_to_name)
        return msgs, res
    else:
        return msgs, handle_person_message(msgs, wxid)

def get_y_mar(s, a,b,c,d):
    if "," in s:
        return a,b
    else:
        return c,d

def create_person_res(msgs, res, wxid, wxid_to_name, is_use_remark=True,name=None):
    # 获取年份
    year = sta_start_time.split(".")[0]
    # 获取显示的名字
    if name is None:
        if is_use_remark:
            name = wxid_to_name[wxid]["conRemark"]
        else:
            name = wxid_to_name[wxid]["nickname"]
    # 获取对方头像
    avatar = wxid_to_name[wxid]["avator"]
    # 获取自己的头像
    self_avatar = self_wx_avator
    self_name = self_wx_name

    # 第一页

    # 获取认识的时间
    know_time, first_time = get_know_time(wxid)
    if first_time is not None:
        historical_timestamp = know_time//1000 if know_time is not None else first_time//1000  # January 1, 2000 UTC
        historical_date = datetime.fromtimestamp(historical_timestamp)
        current_date = datetime.now()
        difference = current_date - historical_date
        days_passed = difference.days # 认识的天数
    if first_time is None:
        return
    
    def page_one():
        # 第一页
        total_msgs = get_message_by_wxid(wxid,"1971.1.1",sta_end_time)
        total_msg_len = len(total_msgs)

        background_image_path = 'pic\wechat.png'
        background_image = Image.open(background_image_path)

        #头像部分
        background_image = draw_avatar(background_image, Image.open(avatar),(90,112),(125,125),5)
        background_image = draw_avatar(background_image, Image.open(self_avatar),(430,112),(125,125),5)
        background_image = draw_text_emoji(background_image, name, 30, (150, 256), align="center", max_width=250)
        background_image = draw_text_emoji(background_image, self_name, 30, (500, 256), align="center", max_width=250)
        
        # 内容部分
        x = 60
        y = 450
        space = 30
        if know_time is not None:
            know_day = timestamp_to_day(know_time)
        else:
            know_day = timestamp_to_day(first_time)
        
        if know_time is not None:
            # 认识天数
            background_image, height = draw_multi_text(background_image, ["我们成为好友已经",str(days_passed),"天了"], [30,55,30],(x,y),
                                            color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                            space=[5,5,0])
        else:
            background_image, height = draw_multi_text(background_image, ["尽管相识已经超过聊天记录部分"], [30],(x,y),
                                        color_list=["white"],font_width_list=["normal"],
                                        space=[5])
            y+=height+space-20
            background_image, height = draw_multi_text(background_image, ["我们成为好友至少",str(days_passed),"天了"], [30,55,30],(x,y),
                                            color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                            space=[5,5,0])
        y+=height+space
        # 认识日期
        background_image, height = draw_multi_text(background_image, ["从",know_day,"开始"], [30,40,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0])
        total_msg_len_str = "{:,}".format(total_msg_len)
        if "," in total_msg_len_str:
            y+=height+space-20
            top_mar = 10
        else:
            y+=height+space-15
            top_mar = 0
        background_image, height = draw_multi_text(background_image, ["我们有",total_msg_len_str,"条聊天信息"], [30,55,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0],
                                        top_margin=[0,top_mar,0])
        
        y+=height+space
        background_image, height = draw_multi_text(background_image, ["每一条消息"], [30],(x,y),
                                        color_list=["white"],font_width_list=["normal"],
                                        space=[5])
        y+=height+space
        background_image, height = draw_multi_text(background_image, ["都是我们成长与生活的足迹"], [30],(x,y),
                                        color_list=["white"],font_width_list=["normal"],
                                        space=[5])
        return background_image
    
    def page_two_three():
        
        # 获取年内聊天记录
        year_msg_len = len(msgs)
        him_msg_len = 0
        for row in msgs:
            msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row
            if isSend == 0:
                him_msg_len += 1
        
        # 获取文本信息
        message_hub = []
        for createTime, talker, content in res[1]["content"]:
            message_hub.append(content)
        txt_time = len(message_hub)
        word_len = len("".join(message_hub))
        wordcloud_img, word= get_word_cloud("\n".join(message_hub))

        # # 第二页
        background_image_path = 'pic/txt.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度·文本』", 40, (320, 40), align="center", max_width=500)
        background_image = draw_avatar(background_image, Image.open(avatar),(90+175,112+30),(125,125),5)
        background_image = draw_text_emoji(background_image, "@"+name, 30, (150+175, 256+30), align="center", max_width=500)
        x = 60
        y = 450
        space = 35

        # 年度消息
        background_image, height = draw_multi_text(background_image, ["在这一年"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])

        year_msg_len_str = "{:,}".format(year_msg_len)
        y,top_mar = get_y_mar(year_msg_len_str, y+height+space-25, 10, y+height+space-20, 0)
        background_image, height = draw_multi_text(background_image, ["我们有",year_msg_len_str,"条聊天信息，其中"], [30,55,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0],
                                        top_margin=[0,top_mar,0])
        
        # 我发送的消息
        him_msg_len_str = "{:,}".format(him_msg_len)
        msg_rate = f"{int(him_msg_len / year_msg_len * 100)}%"
        y,top_mar = get_y_mar(him_msg_len_str, y+height+space-20, 10, y+height+space-15, 0)
        background_image, height = draw_multi_text(background_image, ["你发送了",him_msg_len_str,"条，占比",msg_rate], [30,55,30,55],(x,y),
                                        color_list=["white", "white", "white","white"],font_width_list=["normal", "bold", "normal","bold"],
                                        space=[5,5,5,0],
                                        top_margin=[0,top_mar,0,top_mar])
        
        # 文本信息
        # txt_time=19861
        txt_time = "{:,}".format(txt_time)
        y,top_mar = get_y_mar(txt_time, y+height+space-20, 10, y+height+space-20, 0)
        background_image, height = draw_multi_text(background_image, ["文本信息有",txt_time,"条"], [30,55,30],(x,y),
                                    color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                    space=[5,5,0],
                                    top_margin=[0,top_mar,0])
        
        word_len_str = "{:,}".format(word_len)
        y,top_mar = get_y_mar(word_len_str, y+height+space-20, 10, y+height+space-15, 0)
        background_image, height = draw_multi_text(background_image, ["共计",word_len_str,"个字"], [30,55,30],(x,y),
                                    color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                    space=[5,5,0],
                                    top_margin=[0,top_mar,0])
        paper_num = int(word_len / 800)
        y += height+space-10
        background_image, height = draw_multi_text(background_image, ["这些字连起来，可以写",str(paper_num),"篇高考作文"], [30,45,30],(x,y),
                                    color_list=["white", "#f4b9d1", "white"],font_width_list=["normal", "bold", "normal"],
                                    space=[5,5,0])
        page_two_img = background_image

        # 第三页
        x = 60
        y = 800
        space = 15
        background_image_path = 'pic/txt.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度·文本』", 40, (320, 40), align="center", max_width=500)
        background_image = insert_image(background_image, wordcloud_img, (50,150),(540,600))

        background_image, height = draw_multi_text(background_image, ["这片词云"], [30],(x,y),
                                        color_list=["white"],font_width_list=["normal"],
                                        space=[5])
        y+=height+space
        background_image, height = draw_multi_text(background_image, ["如同散落的时间碎片"], [30],(x,y),
                                        color_list=["white"],font_width_list=["normal"],
                                        space=[5])
        y+=height+space
        background_image, height = draw_multi_text(background_image, ["每一个词都是我们友谊故事的一行诗"], [30],(x,y),
                                        color_list=["white"],font_width_list=["normal"],
                                        space=[5])
        return page_two_img, background_image
    
    def page_pic():
        # 图片，视频，表情包
        pic_num = len(res[3]["content"])
        video_num =len(res[43]["content"]) #content":["时间", "发送id","视频时长(s)","imgPath","msgId"]
        video_time = 0
        for row in res[43]["content"]:
            video_time += row[2]
        video_minute = int(video_time / 60)
        video_sec = video_time % 60

        # 画图
        background_image_path = 'pic/wechat.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度·图片&视频』", 40, (320, 40), align="center", max_width=500)
        x = 60
        y = 300
        space = 35
        background_image, height = draw_multi_text(background_image, ["在这一年"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["我们互相发送了"], [30],(x,y),
                            color_list=["white"],font_width_list=["normal"],
                            space=[5])

        pic_num = "{:,}".format(pic_num)
        y,top_mar = get_y_mar(pic_num, y+height+space-25, 10, y+height+space-20, 0)
        background_image, height = draw_multi_text(background_image, ["图片",pic_num,"张"], [30,55,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0],
                                        top_margin=[0,top_mar,0])
        
        video_num = "{:,}".format(video_num)
        y,top_mar = get_y_mar(pic_num, y+height+space-25, 10, y+height+space-20, 0)
        background_image, height = draw_multi_text(background_image, ["视频",video_num,"个"], [30,55,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0],
                                        top_margin=[0,top_mar,0])
        
        video_minute = str(video_minute)
        video_sec = str(video_sec)
        y,top_mar = get_y_mar(pic_num, y+height+space-25, 10, y+height+space-20, 0)
        background_image, height = draw_multi_text(background_image, ["其中，视频长度至少",video_minute,"分",video_sec,"秒"], [30,55,30,55,30],(x,y),
                                        color_list=["white", "white", "white","white","white"],font_width_list=["normal", "bold", "normal","bold", "normal"],
                                        space=[5,5,5,5,0],
                                        top_margin=[0,top_mar,0,top_mar,0])
        
        y += height+space
        background_image, height = draw_multi_text(background_image, ["在这流动的视频和静止的照片中"], [30],(x,y),
                            color_list=["white"],font_width_list=["normal"],
                            space=[5])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["肯定定格了无数的瞬间"], [30],(x,y),
                            color_list=["white"],font_width_list=["normal"],
                            space=[5])

        return background_image

        
    def page_bimg():
        bimg_num = len(res[47]["content"])
        his_bimg_num = 0
        bimg_to_num = {}
        for row in res[47]["content"]:
            bimg_hash = row[2]
            if bimg_hash not in bimg_to_num:
                bimg_to_num[bimg_hash] = 0
            bimg_to_num[bimg_hash] += 1
            if row[1] != self_wxid:
                his_bimg_num += 1
        max_bimg_time = 0
        max_bimg_hash = None
        max_bimg =None
        for key in bimg_to_num:
            if bimg_to_num[key] > max_bimg_time:
                max_bimg_hash = key
                max_bimg_time = bimg_to_num[key]
        if max_bimg_hash is not None:
            max_bimg = get_bimg_from_hash(conn, max_bimg_hash) #下载表情包
        # 画图
        background_image_path = 'pic/wechat.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度·表情包』", 40, (320, 40), align="center", max_width=500)
        x = 60
        y = 300
        space = 10

        background_image, height = draw_multi_text(background_image, ["在这一年"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["我们相互发送了",str(bimg_num),"张表情包"], [30,55,30],(x,y),
                                        color_list=["white", "#fbb5cd", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0],
                                        top_margin=[0,0,0])
        
        y += height+space
        if bimg_num == 0:
            bimg_num = 1
        background_image, height = draw_multi_text(background_image, ["你发送了其中的",str(int(his_bimg_num / bimg_num * 100))+"%"], [30,55],(x,y),
                                        color_list=["white", "white"],font_width_list=["normal", "bold"],
                                        space=[5,5,0],
                                        top_margin=[0,0,0])
        y += height+space+20
        background_image, height = draw_multi_text(background_image, ["表情斗图，谁是王者"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        if max_bimg is not None:
            y += height+space+10
            
            background_image, height = draw_multi_text(background_image, ["聊天中出现最多的表情包如下，"], [30],(x,y),
                                        color_list=["white"],font_width_list=["normal"],
                                        space=[5])
            y += height+space
            background_image, height = draw_multi_text(background_image, ["共出现了",str(max_bimg_time),"次"], [30,55,30],(x,y),
                                            color_list=["white", "#fbb5cd", "white"],font_width_list=["normal", "bold", "normal"],
                                            space=[5,5,0],
                                            top_margin=[0,0,0])
            y += height+space+30
            img_width,img_height = max_bimg.size
            max_width = 300
            max_height = 300
            rate = img_width / img_height
            if rate > 1:
                img_width = max_width
                img_height = int(img_width / rate)
            else:
                img_height = max_height
                img_width = int(img_height * rate)
            background_image = insert_image(background_image, max_bimg, (320-img_width//2, y), (img_width, img_height))
        
        return background_image
    
    def page_voice():
        voice_num = len(res[34]["content"])
        voice_time = 0
        for row in res[34]["content"]:
            voice_time += row[2]
        voice_time = int(voice_time /1000)
        voice_time_min = int(voice_time / 60)
        voice_time_sec = voice_time % 60
        video_call_num = 0
        video_call_time = 0
        voice_call_num = 0
        voice_call_time = 0
        for row in res[50]["content"]:
            _,_,voip_type,success_type,voip_time=row
            if voip_type == 0:
                if success_type != 0:
                    video_call_num += 1
                video_call_time += voip_time
            else:
                if success_type != 0:
                    voice_call_num += 1
                voice_call_time += voip_time
        voice_call_time_min = int(voice_call_time / 60)
        voice_call_time_sec = voice_call_time % 60
        video_call_time_min = int(video_call_time / 60)
        video_call_time_sec = video_call_time % 60

        # 画图
        background_image_path = 'pic/txt.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度·语音&通话』", 40, (320, 40), align="center", max_width=500)
        x = 60
        y = 200
        space = 15

        background_image, height = draw_multi_text(background_image, ["在这一年"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["我们相互发送了",str(voice_num),"条","语音信息"], [30,55,30,30],(x,y),
                                        color_list=["white", "#fbb5cd", "white","#505f9a"],font_width_list=["normal", "bold", "normal","normal"],
                                        space=[5,5,0,0])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["其中，语音时长高达",str(voice_time_min),"分",str(voice_time_sec),"秒"], [30,55,30,55,30],(x,y),
                                color_list=["white", "white", "white","white","white"],font_width_list=["normal", "bold", "normal","bold", "normal"],
                                space=[5,5,5,5,0],
                                top_margin=[0,0,0,0,0])
        
        y += height+space+10
        background_image, height = draw_multi_text(background_image, ["语音通话","记录居然有",str(voice_call_num),"条"], [30,30,55,30],(x,y),
                                        color_list=["#505f9a","white", "#fbb5cd", "white"],font_width_list=["normal", "normal","bold", "normal"],
                                        space=[5,5,5,0])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["并且，语音时长高达",str(voice_call_time_min),"分",str(voice_call_time_sec),"秒"], [30,55,30,55,30],(x,y),
                                color_list=["white", "white", "white","white","white"],font_width_list=["normal", "bold", "normal","bold", "normal"],
                                space=[5,5,5,5,0],
                                top_margin=[0,0,0,0,0])
        y += height+space+10
        background_image, height = draw_multi_text(background_image, ["视频通话","记录居然有",str(video_call_num),"条"], [30,30,55,30],(x,y),
                                        color_list=["#505f9a","white", "#fbb5cd", "white"],font_width_list=["normal", "normal","bold", "normal"],
                                        space=[5,5,5,0])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["视频通话时长高达",str(video_call_time_min),"分",str(video_call_time_sec),"秒"], [30,55,30,55,30],(x,y),
                                color_list=["white", "white", "white","white","white"],font_width_list=["normal", "bold", "normal","bold", "normal"],
                                space=[5,5,5,5,0],
                                top_margin=[0,0,0,0,0])
        
        y += height+space+20
        background_image, height = draw_multi_text(background_image, ["语音，"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["能够文字所不能表达的信息"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        
        return background_image
    
    def page_money():
        my_hongbao_num = 0
        him_hongbao_num = 0
        for row in res[436207665]["content"]:
            if row[1] == self_wxid:
                my_hongbao_num += 1
            else:
                him_hongbao_num += 1
        money = 0
        max_money = 0
        for row in res[419430449]["content"]:
            money += row[2]
            max_money = max(max_money, row[2])
        # 画图
        background_image_path = 'pic/wechat.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度·红包&转账』", 40, (320, 40), align="center", max_width=500)
        x = 60
        y = 300
        space = 15

        background_image, height = draw_multi_text(background_image, ["红包，寄托了祝福"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y += height+space+10
        background_image, height = draw_multi_text(background_image, ["在这一年里"], [30],(x,y),
                            color_list=["white"],font_width_list=["normal"],
                            space=[5])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["你发了",str(him_hongbao_num),"个红包"], [30,55,30],(x,y),
                                        color_list=["white", "#fbb5cd", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["而我发了",str(my_hongbao_num),"个红包"], [30,55,30],(x,y),
                                        color_list=["white", "#fbb5cd", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0])
        # money = 12323
        money = round(money, 2)
        money = "{:,}".format(money)
        y,top_mar = get_y_mar(money, y+height+space-20, 15, y+height+space, 0)
        background_image, height = draw_multi_text(background_image, ["一共发生了","¥"+str(money),"的转账消息"], [30,55,30],(x,y),
                                        color_list=["white", "#fbb5cd", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0],
                                        top_margin=[0,top_mar,0])
        max_money = round(max_money, 2)
        max_money = "{:,}".format(max_money)
        y,top_mar = get_y_mar(max_money, y+height+space-20, 15, y+height+space, 0)
        background_image, height = draw_multi_text(background_image, ["最高的一笔转账是",str(max_money),"元"], [30,55,30],(x,y),
                                        color_list=["white", "#fbb5cd", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0],
                                        top_margin=[0,top_mar,0])
        
        y = 900
        background_image, height = draw_multi_text(background_image, ["祝老板"], [30],(x,y),
                            color_list=["white"],font_width_list=["normal"],
                            space=[5])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["财运亨通，财源滚滚"], [30],(x,y),
                            color_list=["white"],font_width_list=["normal"],
                            space=[5])
        return background_image
    
    def page_file():
        file_num = len(res[1090519089]["content"])
        file_size = 0
        for row in res[1090519089]["content"]:
            file_size += row[3]
        file_size = round(file_size/1024, 2)
        pos_len = len(res[48]["content"])
        share_len = len(res[-1879048186]["content"])
        
        # 画图
        background_image_path = 'pic/wechat.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度·文件&定位』", 40, (320, 40), align="center", max_width=500)
        x = 60
        y = 300
        space = 15

        background_image, height = draw_multi_text(background_image, ["为了方便"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y += height+space+20
        background_image, height = draw_multi_text(background_image, ["所以选择微信传文件"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["今年内共发送了",str(file_num),"个文件"], [30,55,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["所有文件大小高达",str(file_size),"MB"], [30,55,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0])
        y += height+space+25
        background_image, height = draw_multi_text(background_image, ["所以，微信什么时候能有文件管理呢"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        
        y += height+space
        background_image, height = draw_multi_text(background_image, ["今年一共发送了",str(pos_len),"次定位，"], [30,55,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0])
        y += height+space
        background_image, height = draw_multi_text(background_image, [str(share_len),"次共享定位"], [55,30],(x,y),
                                        color_list=["white", "white"],font_width_list=["bold", "normal"],
                                        space=[5,5,0])
        y += height+space+25
        background_image, height = draw_multi_text(background_image, ["是分享好玩地方的位置吗"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        return background_image
    
    def page_pat():
        my_pated = 0
        him_pated = 0
        for row in res[922746929]["content"]:
            if row[2] == self_wxid:
                my_pated += 1
            else:
                him_pated += 1
        back_num = len(res[10000]["content"])
        # 画图
        background_image_path = 'pic/txt.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度·拍一拍&撤回』", 40, (320, 40), align="center", max_width=700)
        x = 60
        y = 300
        space = 30

        background_image, height = draw_multi_text(background_image, ["拍一拍好玩吗"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y +=height+space+20
        background_image, height = draw_multi_text(background_image, ["今年内"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["你被拍了",str(him_pated),"次"], [30,55,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["我被拍了",str(my_pated),"次"], [30,55,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["还有，手滑","撤回","了",str(back_num),"条消息"], [30,30,30,55,30],(x,y),
                                        color_list=["white","#505f9a","white", "white", "white"],font_width_list=["normal","normal","normal", "bold", "normal"],
                                        space=[5,5,5,5,5,0])
        y +=height+space+20
        background_image, height = draw_multi_text(background_image, ["撤回那么快，我还没看呢"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        return background_image
    
    def page_end():
        background_image_path = 'pic/wechat.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度』", 40, (320, 40), align="center", max_width=500)
        background_image = draw_avatar(background_image, Image.open(avatar),(90+175,112+30),(125,125),5)
        background_image = draw_text_emoji(background_image, "@"+name, 30, (150+175, 256+30), align="center", max_width=500)
        background_image = draw_text(background_image, "感谢相遇，真的", 60, (150+175, 600), align="center", max_width=700)
        return background_image
    # img = page_pic()
    # img.show()
    # exit()
    
    page_list = [
        page_one,
        page_two_three,
        page_pic,
        page_file,
        page_bimg,
        page_voice,
        page_money,
        page_pat,
        page_end,
    ]
    
    img_list = []
    for fun in page_list:
        im = fun()
        if isinstance(im, tuple):
            for i in im:
                img_list.append(i)
        else:
            img_list.append(im)
    big_img = vertical_concat(img_list)
    return big_img
    big_img.save("test.png")
    pass

def get_rank_list(bg_image,pos,right,wxid_to_num, wxid_to_room_name, wxid_to_name, unit="条",limit=4,tag="文本信息排行"):
    res= []
    msg_sum = 0
    for key in wxid_to_num:
        # print(wxid_to_name[key]["conRemark"], wxid_to_num[key])
        msg_sum += wxid_to_num[key]
        if key not in wxid_to_room_name:
            continue
        insert_pos = len(res)
        for i in range(len(res)):
            if wxid_to_num[key] > wxid_to_num[res[i]]:
                insert_pos = i
                break
        res.insert(insert_pos, key)
    iter_len = min(limit, len(res))
    x = pos[0]
    y = pos[1]
    space = 20

    bg_image, width,height = draw_text_rank(bg_image, tag, 25, (320,y), font_width="bold",align="center",v_align="center",color="white")
    y += height+30
    for i in range(iter_len):
        wxid = res[i]
        avatar_path = wxid_to_name[wxid]["avator"]
        person_num = wxid_to_num[wxid]
        person_name = wxid_to_room_name[wxid]
        person_rate = int(person_num / msg_sum * 100)
        # print(wxid_to_name[wxid]["conRemark"], wxid_to_num[wxid])
        ava_img = Image.open(avatar_path)
        bg_image, width,height = draw_text_rank(bg_image, str(i+1)+".", 30, (x,y), align="leaf",v_align="center",color="white")
        bg_image = draw_avatar(bg_image,ava_img, (x+50,y), (60,60), 2, v_align="center")
        
        
        bg_image, width, height = draw_multi_text_rank(bg_image, [str(person_rate),"%，",str(person_num), unit], font_size_list=[30,20,30,20], pos=(right,y),
                            color_list=["white", "white","white", "white"],
                             font_width_list=["bold", "normal","bold", "normal"],
                             space=[0,10,0,0])
        right_width = width
        name_x = x+50+60+20
        bg_image, width,height = draw_text_rank(bg_image, person_name, 25, (name_x,y), align="leaf",v_align="center",color="white",max_width=right-name_x-right_width-10)
        # bg_image, width,height = draw_text_rank(bg_image, str(person_num), 30, (right-width,y), align="right",v_align="center",color="white")
        # right_margin = right_margin + width
        # bg_image, width,height = draw_text_rank(bg_image, "%", 20, (right-width-right_margin-20, y), align="right",v_align="center",color="white")
        # right_margin = right_margin + width +20
        # bg_image, width,height = draw_text_rank(bg_image, str(person_rate), 30, (right-right_margin, y), align="right",v_align="center",color="white")
        # bg_image = draw_avatar(bg_image, Image.open(avatar_path),(320-175//2,112),(175,175),5)
        y += space+60
    return bg_image




def create_room_res(msgs, res, wxid, wxid_to_name, room_name=None): #name_type 0群昵称 1微信名 2备注
    # 获取年份
    year = sta_start_time.split(".")[0]
    # 获取群名
    if room_name is None:
        room_name = wxid_to_name[wxid]["conRemark"]
    # 获取显示的名字
    wxid_to_room_name = get_wxid_to_room_name(wxid)
    wxid_to_want_name = {}
    for key in wxid_to_room_name:
        Remarks = wxid_to_room_name[key]
        if Remarks is None:
            Remarks = wxid_to_name[key]["nickname"]
        Remarks = Remarks.replace("\u2005", "")
        wxid_to_want_name[key] = Remarks

    # 获取对方头像
    avatar = wxid_to_name[wxid]["avator"]
    # 获取自己的头像
    self_avatar = self_wx_avator
    self_name = self_wx_name

    # 第一页

    # 获取认识的时间
    know_time, first_time = get_know_time(wxid)
    if first_time is not None:
        historical_timestamp = know_time//1000 if know_time is not None else first_time//1000  # January 1, 2000 UTC
        historical_date = datetime.fromtimestamp(historical_timestamp)
        current_date = datetime.now()
        difference = current_date - historical_date
        days_passed = difference.days # 认识的天数
    if first_time is None:
        return
    
    def page_one():
        # 第一页
        total_msgs = get_message_by_wxid(wxid,"1971.1.1",sta_end_time)
        total_msg_len = len(total_msgs)

        background_image_path = 'pic\wechat.png'
        background_image = Image.open(background_image_path)

        #头像部分
        background_image = draw_avatar(background_image, Image.open(avatar),(320-175//2,112),(175,175),5)
        background_image = draw_text_emoji(background_image, room_name, 40, (320, 300), align="center", max_width=600)
        # 内容部分
        x = 60
        y = 450
        space = 30
        if know_time is not None:
            know_day = timestamp_to_day(know_time)
        else:
            know_day = timestamp_to_day(first_time)
        

        # 认识天数
        background_image, height = draw_multi_text(background_image, ["本群已经建立至少",str(days_passed),"天了"], [30,55,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0])
        y+=height+space
        # 认识日期
        background_image, height = draw_multi_text(background_image, ["从",know_day,"开始"], [30,40,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0])
        total_msg_len_str = "{:,}".format(total_msg_len)
        if "," in total_msg_len_str:
            y+=height+space-20
            top_mar = 10
        else:
            y+=height+space-15
            top_mar = 0
        background_image, height = draw_multi_text(background_image, ["本群有",total_msg_len_str,"条聊天信息"], [30,55,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0],
                                        top_margin=[0,top_mar,0])
        
        y+=height+space
        background_image, height = draw_multi_text(background_image, ["每一条消息"], [30],(x,y),
                                        color_list=["white"],font_width_list=["normal"],
                                        space=[5])
        y+=height+space
        background_image, height = draw_multi_text(background_image, ["都是我们成长与生活的足迹"], [30],(x,y),
                                        color_list=["white"],font_width_list=["normal"],
                                        space=[5])
        return background_image
    
    def page_two_three():
        
        # 获取年内聊天记录
        year_msg_len = len(msgs)
        him_msg_len = 0
        for row in msgs:
            msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row
            if isSend == 0:
                him_msg_len += 1
        
        # 获取文本信息
        message_hub = []
        txt_rank = {}
        for createTime, talker, content in res[1]["content"]:
            message_hub.append(content)
            if talker not in txt_rank:
                txt_rank[talker] = 0
            txt_rank[talker] += 1
        txt_time = len(message_hub)
        word_len = len("".join(message_hub))
        wordcloud_img, word= get_word_cloud("\n".join(message_hub))

        # # 第二页
        background_image_path = 'pic/txt.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度·文本』", 40, (320, 40), align="center", max_width=500)
        # background_image = draw_avatar(background_image, Image.open(avatar),(90+175,112+30),(125,125),5)
        # background_image = draw_text_emoji(background_image, "@"+room_name, 30, (150+175, 256+30), align="center", max_width=500)
        x = 60
        y = 200
        space = 35

        # 年度消息
        background_image, height = draw_multi_text(background_image, ["在这一年"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])

        year_msg_len_str = "{:,}".format(year_msg_len)
        y,top_mar = get_y_mar(year_msg_len_str, y+height+space-25, 10, y+height+space-20, 0)
        background_image, height = draw_multi_text(background_image, ["本群有",year_msg_len_str,"条聊天信息"], [30,55,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0],
                                        top_margin=[0,top_mar,0])
        
        # 文本信息
        # txt_time=19861
        txt_time = "{:,}".format(txt_time)
        y,top_mar = get_y_mar(txt_time, y+height+space-20, 10, y+height+space-20, 0)
        background_image, height = draw_multi_text(background_image, ["其中，文本信息有",txt_time,"条"], [30,55,30],(x,y),
                                    color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                    space=[5,5,0],
                                    top_margin=[0,top_mar,0])
        
        word_len_str = "{:,}".format(word_len)
        y,top_mar = get_y_mar(word_len_str, y+height+space-20, 10, y+height+space-15, 0)
        background_image, height = draw_multi_text(background_image, ["共计",word_len_str,"个字"], [30,55,30],(x,y),
                                    color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                    space=[5,5,0],
                                    top_margin=[0,top_mar,0])
        paper_num = int(word_len / 800)
        y += height+space-10
        background_image, height = draw_multi_text(background_image, ["这些字连起来，可以写",str(paper_num),"篇高考作文"], [30,45,30],(x,y),
                                    color_list=["white", "#f4b9d1", "white"],font_width_list=["normal", "bold", "normal"],
                                    space=[5,5,0])
        
        background_image = get_rank_list(background_image, (50,650), 600, txt_rank, wxid_to_want_name, wxid_to_name)
        page_two_img = background_image
        
        # return page_two_img

        # 第三页
        x = 60
        y = 800
        space = 15
        background_image_path = 'pic/txt.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度·文本』", 40, (320, 40), align="center", max_width=500)
        background_image = insert_image(background_image, wordcloud_img, (50,150),(540,600))

        background_image, height = draw_multi_text(background_image, ["这片词云"], [30],(x,y),
                                        color_list=["white"],font_width_list=["normal"],
                                        space=[5])
        y+=height+space
        background_image, height = draw_multi_text(background_image, ["如同散落的时间碎片"], [30],(x,y),
                                        color_list=["white"],font_width_list=["normal"],
                                        space=[5])
        y+=height+space
        background_image, height = draw_multi_text(background_image, ["每一个词都是我们友谊故事的一行诗"], [30],(x,y),
                                        color_list=["white"],font_width_list=["normal"],
                                        space=[5])
        # return background_image
        return page_two_img, background_image
    
    def page_pic():
        # 图片，视频，表情包
        pic_num = len(res[3]["content"])
        video_num =len(res[43]["content"]) #content":["时间", "发送id","视频时长(s)","imgPath","msgId"]
        video_time = 0
        for row in res[43]["content"]:
            video_time += row[2]
        video_minute = int(video_time / 60)
        video_sec = video_time % 60

        # 画图
        background_image_path = 'pic/wechat.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度·图片&视频』", 40, (320, 40), align="center", max_width=500)
        x = 60
        y = 300
        space = 35
        background_image, height = draw_multi_text(background_image, ["在这一年"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["本群一共发送了"], [30],(x,y),
                            color_list=["white"],font_width_list=["normal"],
                            space=[5])

        pic_num = "{:,}".format(pic_num)
        y,top_mar = get_y_mar(pic_num, y+height+space-25, 10, y+height+space-20, 0)
        background_image, height = draw_multi_text(background_image, ["图片",pic_num,"张"], [30,55,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0],
                                        top_margin=[0,top_mar,0])
        
        video_num = "{:,}".format(video_num)
        y,top_mar = get_y_mar(pic_num, y+height+space-25, 10, y+height+space-20, 0)
        background_image, height = draw_multi_text(background_image, ["视频",video_num,"个"], [30,55,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0],
                                        top_margin=[0,top_mar,0])
        
        video_minute = str(video_minute)
        video_sec = str(video_sec)
        y,top_mar = get_y_mar(pic_num, y+height+space-25, 10, y+height+space-20, 0)
        background_image, height = draw_multi_text(background_image, ["其中，视频长度至少",video_minute,"分",video_sec,"秒"], [30,55,30,55,30],(x,y),
                                        color_list=["white", "white", "white","white","white"],font_width_list=["normal", "bold", "normal","bold", "normal"],
                                        space=[5,5,5,5,0],
                                        top_margin=[0,top_mar,0,top_mar,0])
        
        y += height+space
        background_image, height = draw_multi_text(background_image, ["在这流动的视频和静止的照片中"], [30],(x,y),
                            color_list=["white"],font_width_list=["normal"],
                            space=[5])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["肯定定格了无数的瞬间"], [30],(x,y),
                            color_list=["white"],font_width_list=["normal"],
                            space=[5])

        return  background_image

        
    def page_bimg():
        bimg_num = len(res[47]["content"])
        his_bimg_num = 0
        bimg_to_num = {}
        bimg_rank = {}
        for row in res[47]["content"]:
            if row[1] not in bimg_rank:
                bimg_rank[row[1]] = 0
            bimg_rank[row[1]] += 1
            bimg_hash = row[2]
            if bimg_hash not in bimg_to_num:
                bimg_to_num[bimg_hash] = 0
            bimg_to_num[bimg_hash] += 1
            if row[1] != self_wxid:
                his_bimg_num += 1
        max_bimg_time = 0
        max_bimg_hash = None
        max_bimg =None
        for key in bimg_to_num:
            if bimg_to_num[key] > max_bimg_time:
                max_bimg_hash = key
                max_bimg_time = bimg_to_num[key]
        if max_bimg_hash is not None:
            max_bimg = get_bimg_from_hash(conn, max_bimg_hash) #下载表情包
        # 画图
        background_image_path = 'pic/wechat.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度·表情包』", 40, (320, 40), align="center", max_width=500)
        x = 60
        y = 100
        space = 10

        background_image, height = draw_multi_text(background_image, ["在这一年"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["本群一共发送了",str(bimg_num),"张表情包"], [30,55,30],(x,y),
                                        color_list=["white", "#fbb5cd", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0],
                                        top_margin=[0,0,0])
        y += height+space+20
        background_image, height = draw_multi_text(background_image, ["表情斗图，谁是王者"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        background_image = get_rank_list(background_image, (50,780), 600, bimg_rank, wxid_to_want_name, wxid_to_name,unit="张",limit=3,tag="表情包排行")

        if max_bimg is not None:
            y += height+space+10
            
            background_image, height = draw_multi_text(background_image, ["聊天中出现最多的表情包如下，"], [30],(x,y),
                                        color_list=["white"],font_width_list=["normal"],
                                        space=[5])
            y += height+space
            background_image, height = draw_multi_text(background_image, ["共出现了",str(max_bimg_time),"次"], [30,55,30],(x,y),
                                            color_list=["white", "#fbb5cd", "white"],font_width_list=["normal", "bold", "normal"],
                                            space=[5,5,0],
                                            top_margin=[0,0,0])
            y += height+space+30
            img_width,img_height = max_bimg.size
            max_width = 300
            max_height = 300
            rate = img_width / img_height
            if rate > 1:
                img_width = max_width
                img_height = int(img_width / rate)
            else:
                img_height = max_height
                img_width = int(img_height * rate)
            background_image = insert_image(background_image, max_bimg, (320-img_width//2, y), (img_width, img_height))
        
        return background_image
    
    def page_voice():
        voice_num = len(res[34]["content"])
        voice_time = 0
        for row in res[34]["content"]:
            voice_time += row[2]
        voice_time = int(voice_time /1000)
        voice_time_min = int(voice_time / 60)
        voice_time_sec = voice_time % 60

        voip_num = len(res[64]["content"])
        voip_time = 0
        for row in res[64]["content"]:
            start_time, end_time  = row
            voip_time += end_time - start_time
        voip_time = int(voip_time / 1000)
        voip_time_min = int(voip_time / 60)
        voip_time_sec = voip_time % 60

        # 画图
        background_image_path = 'pic/txt.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度·语音&通话』", 40, (320, 40), align="center", max_width=500)
        x = 60
        y = 350
        space = 15

        background_image, height = draw_multi_text(background_image, ["在这一年"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["本群一共发送了",str(voice_num),"条","语音信息"], [30,55,30,30],(x,y),
                                        color_list=["white", "#fbb5cd", "white","#505f9a"],font_width_list=["normal", "bold", "normal","normal"],
                                        space=[5,5,0,0])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["其中，语音时长高达",str(voice_time_min),"分",str(voice_time_sec),"秒"], [30,55,30,55,30],(x,y),
                                color_list=["white", "white", "white","white","white"],font_width_list=["normal", "bold", "normal","bold", "normal"],
                                space=[5,5,5,5,0],
                                top_margin=[0,0,0,0,0])
        
        y += height+space+10
        background_image, height = draw_multi_text(background_image, ["群语音通话","记录居然有",str(voip_num),"条，并且"], [30,30,55,30],(x,y),
                                        color_list=["#505f9a","white", "#fbb5cd", "white"],font_width_list=["normal", "normal","bold", "normal"],
                                        space=[5,5,5,0])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["群语音时长高达",str(voip_time_min),"分",str(voip_time_sec),"秒"], [30,55,30,55,30],(x,y),
                                color_list=["white", "white", "white","white","white"],font_width_list=["normal", "bold", "normal","bold", "normal"],
                                space=[5,5,5,5,0],
                                top_margin=[0,0,0,0,0])
        
        y += height+space+20
        background_image, height = draw_multi_text(background_image, ["语音，"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["能够表达文字所不能表达的信息"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        
        return background_image
    
    def page_money():
        my_hongbao_num = 0
        him_hongbao_num = 0
        hongbao_rank = {}
        for row in res[436207665]["content"]:
            if row[1] not in hongbao_rank:
                hongbao_rank[row[1]] = 0
            hongbao_rank[row[1]] += 1
            if row[1] == self_wxid:
                my_hongbao_num += 1
            else:
                him_hongbao_num += 1
        money = 0
        max_money = 0
        for row in res[419430449]["content"]:
            money += row[2]
            max_money = max(max_money, row[2])
        
        collect_num = len(res[10086]["content"])
        collect_val = 0
        for row in res[10086]["content"]:
            collect_val += row[2]
        
        # 画图
        background_image_path = 'pic/wechat.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度·红包&转账』", 40, (320, 40), align="center", max_width=500)
        x = 60
        y = 200
        space = 15

        background_image, height = draw_multi_text(background_image, ["红包，寄托了祝福"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y += height+space+10
        background_image, height = draw_multi_text(background_image, ["在这一年里"], [30],(x,y),
                            color_list=["white"],font_width_list=["normal"],
                            space=[5])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["本群一共发了",str(him_hongbao_num+my_hongbao_num),"个红包"], [30,55,30],(x,y),
                                        color_list=["white", "#fbb5cd", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0])
        
        money = round(money, 2)
        money = "{:,}".format(money)
        y,top_mar = get_y_mar(money, y+height+space-20, 15, y+height+space, 0)
        background_image, height = draw_multi_text(background_image, ["一共发生了","¥"+str(money),"的转账消息"], [30,55,30],(x,y),
                                        color_list=["white", "#fbb5cd", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0],
                                        top_margin=[0,top_mar,0])
        collect_num = str(collect_num)
        y += height+space
        background_image, height = draw_multi_text(background_image, ["发起了",str(collect_num),"条群收款"], [30,55,30],(x,y),
                                        color_list=["white", "#fbb5cd", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0],
                                        top_margin=[0,top_mar,0])
        y += height+space+10
        background_image, height = draw_multi_text(background_image, ["如果每条群收款都参与了"], [30],(x,y),
                            color_list=["white"],font_width_list=["normal"],
                            space=[5])
        collect_val = round(collect_val, 2)
        collect_val = "{:,}".format(collect_val)
        y,top_mar = get_y_mar(collect_val, y+height+space-20, 15, y+height+space, 0)
        background_image, height = draw_multi_text(background_image, ["那么你要交",collect_val,"元"], [30,55,30],(x,y),
                                        color_list=["white", "#fbb5cd", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0],
                                        top_margin=[0,top_mar,0])
        
        if len(hongbao_rank)>0:
            background_image = get_rank_list(background_image, (50,700), 600, hongbao_rank, wxid_to_want_name, wxid_to_name,unit="个", tag="谁是发红包财神呢")
        return background_image
    
    def page_file():
        file_num = len(res[1090519089]["content"])
        file_size = 0
        for row in res[1090519089]["content"]:
            file_size += row[3]
        file_size = round(file_size/1024, 2)
        pos_len = len(res[48]["content"])
        share_len = len(res[-1879048186]["content"])
        
        # 画图
        background_image_path = 'pic/wechat.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度·文件&定位』", 40, (320, 40), align="center", max_width=500)
        x = 60
        y = 300
        space = 15

        background_image, height = draw_multi_text(background_image, ["为了方便"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y += height+space+20
        background_image, height = draw_multi_text(background_image, ["所以选择微信传文件"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["今年内本群共发送了",str(file_num),"个文件"], [30,55,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["所有文件大小高达",str(file_size),"MB"], [30,55,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0])
        y += height+space+25
        background_image, height = draw_multi_text(background_image, ["所以，微信什么时候能有文件管理呢"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        
        y += height+space
        background_image, height = draw_multi_text(background_image, ["本群今年一共发送了",str(pos_len),"次定位，"], [30,55,30],(x,y),
                                        color_list=["white", "white", "white"],font_width_list=["normal", "bold", "normal"],
                                        space=[5,5,0])
        y += height+space
        background_image, height = draw_multi_text(background_image, [str(share_len),"次共享定位"], [55,30],(x,y),
                                        color_list=["white", "white"],font_width_list=["bold", "normal"],
                                        space=[5,5,0])
        y += height+space+25
        background_image, height = draw_multi_text(background_image, ["是给群友分享好玩地方的位置吗"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        return background_image
    
    def page_pat():
        my_pated = 0
        him_pated = 0
        pat_rank = {}
        for row in res[922746929]["content"]:
            if row[2] not in pat_rank:
                pat_rank[row[2]] = 0
            pat_rank[row[2]] += 1
            if row[2] == self_wxid:
                my_pated += 1
            else:
                him_pated += 1
        back_num = len(res[10000]["content"])
        # 画图
        background_image_path = 'pic/txt.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度·拍一拍&撤回』", 40, (320, 40), align="center", max_width=700)
        x = 60
        y = 200
        space = 30

        background_image, height = draw_multi_text(background_image, ["拍一拍好玩吗"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y +=height+space+20
        background_image, height = draw_multi_text(background_image, ["今年内"], [30],(x,y),
                                    color_list=["white"],font_width_list=["normal"],
                                    space=[5])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["本群一共发生了",str(him_pated+my_pated),"次","拍一拍"], [30,55,30,30],(x,y),
                                        color_list=["white", "white", "white","#505f9a"],font_width_list=["normal", "bold", "normal","normal"],
                                        space=[5,5,5,0])
        y += height+space
        background_image, height = draw_multi_text(background_image, ["还有，手滑","撤回","了",str(back_num),"条消息"], [30,30,30,55,30],(x,y),
                                        color_list=["white","#505f9a","white", "white", "white"],font_width_list=["normal","normal","normal", "bold", "normal"],
                                        space=[5,5,5,5,5,0])
        # y +=height+space+20
        # background_image, height = draw_multi_text(background_image, ["撤回那么快，我还没看呢"], [30],(x,y),
        #                             color_list=["white"],font_width_list=["normal"],
        #                             space=[5])
        background_image = get_rank_list(background_image, (50,650), 600, pat_rank, wxid_to_want_name, wxid_to_name,unit="次", tag="谁被拍最多呢")
        return background_image
    
    def page_summary():
        wxid_to_num = {}
        cal_type = [1,3,34, 43,47, 48, 50,10000, 419430449,436207665,922746929,1090519089,-1879048186]
        for msg_type in cal_type:
            for row in res[msg_type]["content"]:
                talker = row[1]
                if "@chatroom" in talker:
                    continue
                if talker not in wxid_to_num:
                    wxid_to_num[talker] = 0
                wxid_to_num[talker] += 1
        # 画图
        background_image_path = 'pic/txt.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度·所有消息排行』", 40, (320, 40), align="center", max_width=700)
        background_image = get_rank_list(background_image, (50,150), 600, wxid_to_num, wxid_to_want_name, wxid_to_name,unit="条", tag="",limit=11)
        return background_image
    def page_end():
        background_image_path = 'pic/wechat.png'
        background_image = Image.open(background_image_path)
        background_image = draw_text(background_image, f"『{year}年度』", 40, (320, 40), align="center", max_width=500)
        background_image = draw_avatar(background_image, Image.open(avatar),(320-175//2,112),(175,175),5)
        background_image = draw_text_emoji(background_image, "@"+room_name, 40, (320, 300), align="center", max_width=600)
        background_image = draw_text_emoji(background_image, "干杯!", 60, (150+175, 600), align="center", max_width=700)
        return background_image
    # img = page_money()
    # img.show()
    # exit()

    # img = page_voice()
    # img.show()
    # exit()
    page_list = [
        page_one,
        page_two_three,
        page_pic,
        page_bimg,
        page_file,
        page_voice,
        page_money,
        page_pat,
        page_summary,
        page_end,
    ]
    
    img_list = []
    for fun in page_list:
        im = fun()
        if isinstance(im, tuple):
            for i in im:
                img_list.append(i)
        else:
            img_list.append(im)

    big_img = vertical_concat(img_list)
    return big_img

def create_res_img_by_wxid(wxid, name=None):
    msgs, res = get_res_by_wxid(wxid, wxid_to_name)
    if "@chatroom" in wxid:
        big_img = create_room_res(msgs, res, wxid, wxid_to_name,room_name=name)
    else:
        big_img = create_person_res(msgs, res, wxid, wxid_to_name,name=name)
    if name is None:
        if name_type == 0:
            name = wxid_to_name[wxid]["conRemark"]
        elif name_type == 1:
            name = wxid_to_name[wxid]["nickname"]
    big_img.save(f"生成结果/{name}.png")
    print("生成完成，路径在：", f"生成结果/{name}.png")

import argparse
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="微信年度报告生成")
    parser.add_argument("-d", "--dataset_path",default="E:/(com.tencent.mm)/apps/com.tencent.mm/r/MicroMsg/67fec1410543c5ff6ea9ab25bc770ac0",
                    help="数据库位置")
    parser.add_argument("-s", "--start_time",default="2023.1.1",
                    help="开始日期")
    parser.add_argument("-e", "--end_time",default="2023.12.31",
                    help="结束日期")
    parser.add_argument("-n", "--name_type", type=int,default=0,
                    help="使用备注还是微信名，0备注 1微信名 2自己输入")
    parser.add_argument("-m", "--mode",type=int,default=0,
                    help="范围，0单人或单群 1为所有群生成 2为所有人生成")
    args = parser.parse_args()

    sta_start_time = args.start_time #"2023.1.1"
    sta_end_time = args.end_time#"2023.12.31"
    name_type = args.name_type
    mode = args.mode

    dataset_path = args.dataset_path

    avator_path = os.path.join(os.path.join(dataset_path, "avatar/"))
    main_dataset_path = os.path.join(dataset_path, "EnMicroMsg_plain.db")
    conn = sqlite3.connect(main_dataset_path)
    self_wxid, self_wx_name, self_wx_avator = get_user_info(conn)

    # 先获取所有人和群的昵称和性别
    wxid_to_name = get_wxid_to_info()
    # 获取所有联系人的wxid
    all_friend = get_person_list()
    # 获取所有群聊的wxid
    all_room = get_room_list()

    if mode == 0:
        user_name = input("输入想要生成的人或群【备注或微信昵称】:")
        # user_name = "肥欣"
        wxid = get_wxid(user_name)
        print(wxid)
        if wxid is None:
            print("没找到这个人或群")
            exit()
        if name_type == 0:
            name = wxid_to_name[wxid]["conRemark"]
        elif name_type == 1:
            name = wxid_to_name[wxid]["nickname"]
        else:
            name = input("自定义他的名字：")
            if name == "":
                name = user_name
        create_res_img_by_wxid(wxid, name)
    elif mode == 1:
        for wxid in tqdm(all_room):
            create_res_img_by_wxid(wxid)
    elif mode == 2:
        for wxid in tqdm(all_friend):
            create_res_img_by_wxid(wxid)