from PIL import Image
import numpy as np

def repeat_image(image_path, repeat_x, repeat_y):
    # 打开图像
    img = Image.open(image_path)

    # 将图像转换为NumPy数组
    img_array = np.array(img)

    # 重复图像
    repeated_array = np.tile(img_array, (repeat_y, repeat_x, 1))

    # 将NumPy数组转换回图像
    new_img = Image.fromarray(repeated_array)

    img = new_img.convert("RGBA")  # 确保图像是RGBA模式

    data = img.getdata()
    new_data = []

    for item in data:
        # 将白色（或接近白色）变为透明
        if item[0] > 200 and item[1] > 200 and item[2] > 200:
            new_data.append((255, 255, 255, 0))  # 完全透明
        # 将透明变为白色
        elif item[3] == 0:
            new_data.append((255, 255, 255, 255))  # 完全不透明的白色
        else:
            new_data.append(item)

    # 更新图像数据并保存
    img.putdata(new_data)

    img.save(image_path+"new.png")
    # return new_img_path

# 示例使用
# 替换为您的PNG文件路径和希望的重复次数
image_path = './assert/pic.png'
repeat_x = 10  # 横向重复次数
repeat_y = 10  # 纵向重复次数

new_image_path = repeat_image(image_path, repeat_x, repeat_y)
# print(f'新图像已保存在: {new_image_path}')