import hashlib
import os
from datetime import datetime
import time

def get_timestamp(date="2023.1.1"):
    date_object = datetime.strptime(date, '%Y.%m.%d')
    timestamp = time.mktime(date_object.timetuple())*1000
    return timestamp

def timestamp_to_sec(timestamp):
    date_time = datetime.fromtimestamp(timestamp // 1000)
    # Format the datetime object to a string in the format "Year-Month-Day Hour:Minute:Second"
    formatted_date_time = date_time.strftime('%Y-%m-%d %H:%M:%S')
    return formatted_date_time

def timestamp_to_day(timestamp):
    date_time = datetime.fromtimestamp(timestamp // 1000)
    # Format the datetime object to a string in the format "Year-Month-Day Hour:Minute:Second"
    formatted_date_time = date_time.strftime('%Y-%m-%d')
    return formatted_date_time

def avatar_md5(wxid):
    m = hashlib.md5()
    # 参数必须是byte类型，否则报Unicode-objects must be encoded before hashing错误
    m.update(bytes(wxid.encode('utf-8')))
    return m.hexdigest()
'''
#! 获取头像文件完整路径
'''
def get_avator(wxid, avatar_path):
    avatar = avatar_md5(wxid)
    path = avatar_path + avatar[:2] + '/' + avatar[2:4]
    is_find = False
    for root, dirs, files in os.walk(path):
        for file in files:
            if avatar in file:
                avatar = file
                is_find = True
                break
    if is_find:
        return  path + '/'+ avatar
    else:
        return "pic/default_avatar.jpg"

def filter_by_type(msgs, type_list=[1], self_wxid=None):
    res = []
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row
        if msg_type in type_list:
            if self_wxid is not None and isSend == 1:
                talker = self_wxid
            res.append([msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId])
    return res

def filter_by_type_room(msgs, type_list=[1], self_wxid=None):
    res = []
    for row in msgs:
        msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId = row
        if msg_type in type_list:
            if isSend == 0:
                ct_s = content.split("\n",1)
                talker = ct_s[0][:-1]
                content = ct_s[1]
            elif self_wxid is not None and isSend == 1:
                talker = self_wxid
            res.append([msg_type,isSend,createTime,talker,content,imgPath,lvbuffer,msgId])
    return res


from PIL import Image, ImageDraw,ImageFont
def draw_avatar(background_image, insert_image, position, size, border_width, v_align="top"):
    if v_align == "center":
        position = (position[0], position[1] - size[1]//2)
    ant = 4
    background_image_size =background_image.size
    large_image = background_image.resize((background_image_size[0]*ant,
                                           background_image_size[1]*ant,), Image.LANCZOS)
    # Resize the insert image to the desired size
    insert_image = insert_image.resize((size[0]*ant,size[1]*ant), Image.LANCZOS)
    mask = Image.new('L', insert_image.size, 0)
    draw = ImageDraw.Draw(mask) 
    draw.ellipse((0, 0) + insert_image.size, fill=255)
    insert_image.putalpha(mask)
    large_image.paste(insert_image, (position[0]*ant,position[1]*ant), mask=insert_image)
    
    draw = ImageDraw.Draw(large_image)
    border_width = border_width*ant // 2
    draw.ellipse((position[0]*ant-border_width, position[1]*ant-border_width, 
                    position[0]*ant + size[0]*ant +border_width,
                    position[1]*ant + size[1]*ant +border_width), 
                    outline="white", width=border_width*2)
    background_image = large_image.resize(background_image.size,Image.LANCZOS)
    return background_image

def insert_image(background_image, insert_image, position, size):
    ant = 4
    background_image_size =background_image.size
    large_image = background_image.resize((background_image_size[0]*ant,
                                           background_image_size[1]*ant,), Image.LANCZOS)
    # Resize the insert image to the desired size
    insert_image = insert_image.resize((size[0]*ant,size[1]*ant), Image.LANCZOS)
    large_image.paste(insert_image, (position[0]*ant,position[1]*ant),mask=insert_image )
    background_image = large_image.resize(background_image.size,Image.LANCZOS)
    return background_image

def change_string_cahr(s, i, c):
    return s[:i] + c + s[i+1:]
import re
def get_emoji_pos(text):
    # Emoji 的 Unicode 编码范围通常包括以下几个区域
    # 但这个范围不是固定的，可能随着标准的更新而变化
    emoji_pattern = re.compile("["
                           u"\U0001F600-\U0001F64F"  # emoticons
                           u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                           u"\U0001F680-\U0001F6FF"  # transport & map symbols
                           u"\U0001F700-\U0001F77F"  # alchemical symbols
                           u"\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
                           u"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
                           u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
                           u"\U0001FA00-\U0001FA6F"  # Chess Symbols
                           u"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
                           "]+", flags=re.UNICODE)

    # 使用 finditer 方法找到所有 emoji 的位置
    positions = [match.start() for match in emoji_pattern.finditer(text)]
    emoji_list = []
    for i in positions:
        emoji_list.append(text[i])
        text = change_string_cahr(text, i, 'A')
    return text, positions, emoji_list



# from pilmoji import Pilmoji
# def draw_text_emoji(background_image, text, font_size, pos, color="white",font_width="normal",align="leaf",max_width=10000000):

#     draw = Pilmoji(background_image)
#     # 选择一个初始字体大小
#     font_size = font_size
#     if font_width == "normal":
#         font = ImageFont.truetype("./pic/MiSans-Semibold.ttf", font_size)
#     elif font_width == "":
#         font = ImageFont.truetype("./pic/MiSans-Bold.ttf", font_size)
    
#     text, emoji_pos, emoji_list = get_emoji_pos(text)
#     now_txt = ""
#     txt_res = []
#     #不超出长度
#     for t in text:
#         text_width, text_height = font.getsize(now_txt+t)
#         if text_width > max_width:
#             txt_res.append(now_txt)
#             now_txt = t
#         else:
#             now_txt += t
#     if now_txt != "":
#         txt_res.append(now_txt)
    

#     emoji_txt_res = []
#     start_pos = 0
#     k = 0
#     # 将emoji表情替换回去
#     for row in txt_res:
#         end_pos = start_pos + len(row)
#         for i in range(k, len(emoji_pos)):
#             want_pos = emoji_pos[i]
#             if want_pos <= end_pos: #在这一行上
#                 k += 1
#                 row = change_string_cahr(row, want_pos - start_pos, emoji_list[i])
#             elif want_pos > end_pos:
#                 break
#         start_pos = end_pos+1 
#         emoji_txt_res.append(row)

#     x = pos[0]
#     y = pos[1]
#     if align == "leaf":
#         text = "\n".join(emoji_txt_res)
#         draw.text((x, y), text, font=font, fill=color)
#     elif align == "center":
#         now_height = y
#         for i in range(len(txt_res)):
#             width, height = font.getsize(txt_res[i])
            
#             _x = x - width // 2
#             draw.text((_x, now_height), emoji_txt_res[i], font=font, fill=color)
#             now_height += height
#     return background_image

from pilmoji import Pilmoji
def draw_text_emoji(background_image, text, font_size, pos, color="white",font_width="normal",align="leaf",max_width=10000000,is_emoji=False):
    # if is_emoji:
    #     draw = Pilmoji(background_image)
    # else:
    draw = Pilmoji(background_image)
    # 选择一个初始字体大小
    font_size = font_size
    if font_width == "normal":
        font = ImageFont.truetype("./pic/MiSans-Semibold.ttf", font_size)
    elif font_width == "":
        font = ImageFont.truetype("./pic/MiSans-Bold.ttf", font_size)
    
    now_txt = ""
    txt_res = []
    #不超出长度
    for t in text:
        text_width, text_height = font.getsize(now_txt+t)
        if text_width > max_width:
            txt_res.append(now_txt)
            now_txt = t
        else:
            now_txt += t
    if now_txt != "":
        txt_res.append(now_txt)

    x = pos[0]
    y = pos[1]
    if align == "leaf":
        text = "\n".join(txt_res)
        draw.text((x, y), text, font=font, fill=color)
    elif align == "center":
        now_height = y
        for row in txt_res:
            width, height = font.getsize(row)
            _x = x - width // 2
            draw.text((_x, now_height), row, font=font, fill=color)
            now_height += height
    return background_image

def draw_text(background_image, text, font_size, pos, color="white",font_width="normal",align="leaf",max_width=10000000,is_emoji=False):
    draw = ImageDraw.Draw(background_image)
    # 选择一个初始字体大小
    font_size = font_size
    if font_width == "normal":
        font = ImageFont.truetype("./pic/MiSans-Semibold.ttf", font_size)
    elif font_width == "":
        font = ImageFont.truetype("./pic/MiSans-Bold.ttf", font_size)
    
    now_txt = ""
    txt_res = []
    #不超出长度
    for t in text:
        text_width, text_height = font.getsize(now_txt+t)
        if text_width > max_width:
            txt_res.append(now_txt)
            now_txt = t
        else:
            now_txt += t
    if now_txt != "":
        txt_res.append(now_txt)

    x = pos[0]
    y = pos[1]
    if align == "leaf":
        text = "\n".join(txt_res)
        draw.text((x, y), text, font=font, fill=color)
    elif align == "center":
        now_height = y
        for row in txt_res:
            width, height = font.getsize(row)
            _x = x - width // 2
            draw.text((_x, now_height), row, font=font, fill=color)
            now_height += height
    return background_image

def draw_text_rank(background_image, text, font_size, pos, color="white",font_width="normal",align="leaf",v_align="center",max_width=10000000):
    draw = Pilmoji(background_image)
    # 选择一个初始字体大小
    font_size = font_size
    if font_width == "normal":
        font = ImageFont.truetype("./pic/MiSans-Semibold.ttf", font_size)
    elif font_width == "bold":
        font = ImageFont.truetype("./pic/MiSans-Bold.ttf", font_size)
    
    now_txt = ""
    
    #不超出长度
    for t in text:
        text_width, text_height = font.getsize(now_txt+t)
        if text_width > max_width:
            now_txt = now_txt[:-1]+"..."
            break
        else:
            now_txt += t
    
    text = now_txt
    x = pos[0]
    y = pos[1]
    width, height = font.getsize(text)
    if v_align == "center":
        _y = y - height // 2
    if align == "leaf":
        draw.text((x, _y), text, font=font, fill=color)
    elif align == "center":
        _x = x - width // 2
        draw.text((_x, _y), text, font=font, fill=color)
    elif align == "right":
        _x = x - width
        draw.text((_x, _y), text, font=font, fill=color)
    return background_image, width, height


def draw_multi_text_rank(background_image, text_list, font_size_list, pos, color_list=["white"], font_width_list=["normal"],
                    space=[],
                    ):
    # text ="123123\nsdf\nsdf"
    # 加载图片
    draw = ImageDraw.Draw(background_image)
    x = pos[0]
    y = pos[1]
    height_list = []
    for i in range(len(text_list)):
        text = text_list[i]
        font_size = font_size_list[i]
        font_width = font_width_list[i]
        if font_width == "normal":
            font = ImageFont.truetype("./pic/MiSans-Semibold.ttf", font_size)
        elif font_width == "bold":
            font = ImageFont.truetype("./pic/MiSans-Bold.ttf", font_size)
        # draw.text((x, y), text, font=font, fill=color_list[i])
        width, height = font.getsize(text)
        height_list.append(height)
        # x += width
    max_height = max(height_list)
    min_height = min(height_list)
    total_width = 0
    _x = x
    _y = y - max_height//2
    for i in range(len(text_list)-1, -1, -1):
        text = text_list[i]
        font_size = font_size_list[i]
        font_width = font_width_list[i]
        if font_width == "normal":
            font = ImageFont.truetype("./pic/MiSans-Semibold.ttf", font_size)
        elif font_width == "bold":
            font = ImageFont.truetype("./pic/MiSans-Bold.ttf", font_size)
        width, height = font.getsize(text)
        if font_width == "normal":
            height = min_height
        elif font_width == "bold":
            height = max_height
        _x -= width + space[i]
        draw.text((_x, _y+max_height-height), text, font=font, fill=color_list[i])
        # x += width + space[i]
    return background_image, x - _x,max_height


def draw_multi_text(background_image, text_list, font_size_list, pos, color_list=["white"], font_width_list=["normal"],
                    space=[], #每个段后面的间隔
                    top_margin=None):
    # text ="123123\nsdf\nsdf"
    # 加载图片
    draw = ImageDraw.Draw(background_image)
    x = pos[0]
    y = pos[1]
    height_list = []
    for i in range(len(text_list)):
        text = text_list[i]
        font_size = font_size_list[i]
        font_width = font_width_list[i]
        if font_width == "normal":
            font = ImageFont.truetype("./pic/MiSans-Semibold.ttf", font_size)
        elif font_width == "bold":
            font = ImageFont.truetype("./pic/MiSans-Bold.ttf", font_size)
        # draw.text((x, y), text, font=font, fill=color_list[i])
        width, height = font.getsize(text)
        height_list.append(height)
        # x += width
    max_height = max(height_list)
    min_height = min(height_list)
    for i in range(len(text_list)):
        text = text_list[i]
        font_size = font_size_list[i]
        font_width = font_width_list[i]
        if font_width == "normal":
            font = ImageFont.truetype("./pic/MiSans-Semibold.ttf", font_size)
        elif font_width == "bold":
            font = ImageFont.truetype("./pic/MiSans-Bold.ttf", font_size)
        width, height = font.getsize(text)
        if font_width == "normal":
            height = min_height
        elif font_width == "bold":
            height = max_height
        top_margin_ = 0
        if top_margin is not None:
            top_margin_ = top_margin[i]
        draw.text((x, y+max_height-height+top_margin_), text, font=font, fill=color_list[i])
        
        x += width + space[i]
    return background_image, max_height


from wordcloud import WordCloud
from PIL import Image
import jieba

def get_word_cloud(text):
    text=jieba.lcut(text)
    #进行格式转换，将ls列表转换成一个以空格分隔的字符串。
    text=" ".join(text)
    stopwords = []
    with open("pic/cn_stopwords.txt", 'r', encoding='utf-8') as file:
        for line in file:
            # 移除每行末尾的换行符并存入数组
            stopwords.append(line.strip())

    # 创建词云对象，设置背景为透明
    wordcloud = WordCloud(font_path='pic/MiSans-Semibold.ttf', width=int(540*1.3), height=int(600*1.3), 
                        background_color='rgba(255, 255, 255, 0)', colormap='inferno',stopwords=stopwords,mode='RGBA', min_font_size=10).generate(text)

    # 将词云转换为 NumPy 数组
    wordcloud_array = wordcloud.to_array()
    
    frequencies = wordcloud.process_text(text)
    # 找出频次最高的词语
    most_common_word = max(frequencies, key=frequencies.get)

    # 将 NumPy 数组转换为 PIL Image 对象
    wordcloud_image = Image.fromarray(wordcloud_array)
    return wordcloud_image, most_common_word

import requests
from io import BytesIO
def download_image(url):
    print("下载图片",url)
    # 发送 HTTP GET 请求下载图片
    try:
        response = requests.get(url, verify=False)
    except:
        return None
    # 检查请求是否成功
    if response.status_code == 200:
        # 使用 BytesIO 从下载的数据中读取图像
        image_data = BytesIO(response.content)

        # 打开图像
        image = Image.open(image_data)
        
        # # 如果是 GIF 图片，只取第一帧
        # if image.format == 'GIF':
        image = image.convert('RGBA')
        return image
    else:
        return None

def get_bimg_from_hash(conn, hash):
    cursor = conn.cursor()
    cursor.execute(f"SELECT thumbUrl,cdnUrl FROM EmojiInfo WHERE md5='{hash}'")
    # 不包含企业微信号的人可以添加username NOT LIKE '%@openim%'
    table_data = cursor.fetchall()
    cursor.close()
    if len(table_data) == 0:
        return None
    thumbUrl = table_data[0][0]
    cdnUrl = table_data[0][1]
    if cdnUrl != "":
        img = download_image(cdnUrl)
        if img is not None:
            return img
    if thumbUrl != "":
        img = download_image(thumbUrl)
        if img is not None:
            return img
    return None


def vertical_concat(images):
    # 计算合并后的总高度和宽度
    total_height = sum(img.size[1] for img in images)
    max_width = max(img.size[0] for img in images)

    # 创建一个新的图像，大小为最大宽度和总高度
    new_img = Image.new('RGBA', (max_width, total_height))

    # 将图像依次粘贴到新图像上
    y_offset = 0
    for img in images:
        new_img.paste(img, (0, y_offset))
        y_offset += img.height

    return new_img
    
    