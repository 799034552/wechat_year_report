# 手机微信年度报告生成(可无需python)
> 之前在网上看到能将微信的聊天导出，我就像可以生成一下年度报告，图片版本的，发给群友或者好友乐呵乐呵，但是电脑版的微信聊天记录根本不全，通过聊天迁移的也没有，还是从手机端生成的全

1. 先参考网上的一些教程将手机微信的数据通过备份功能导入到电脑，可以参考[这个](https://www.yaozeyuan.online/2023/06/03/2023/06/%E6%97%A0%E9%9C%80root%E7%9A%84%E5%BE%AE%E4%BF%A1%E8%81%8A%E5%A4%A9%E8%AE%B0%E5%BD%95%E5%AF%BC%E5%87%BA%E6%96%B9%E6%A1%88/),只需要把压缩包拉入到电脑就行
2. 小米手机会得到一个`微信(com.tencent.mm).bak`文件，把他改为`(com.tencent.mm).7z`然后解压就行

## 1. 解码数据库
！路径在解码的时候不支持中文
* 找到解压后`auth_info_key_prefs.xml`所在的文件夹，通常是如`E:/(com.tencent.mm)/apps/com.tencent.mm/sp`，记下这个文件夹位置为`<uid_path>
* 找到压缩后的个人数据文件夹位置，通常如`E:/(com.tencent.mm)/apps/com.tencent.mm/r/MicroMsg/67fec1410543c5ff6ea9ab25bc770ac0`，记下这个文件夹位置为<dataset_path>
执行命令
```py
python decode.py -u <uid_path> -d <dataset_path>
# 示例
python decode.py  -u "E:/(com.tencent.mm)/apps/com.tencent.mm/sp" -d "E:/(com.tencent.mm)/apps/com.tencent.mm/r/MicroMsg/67fec1410543c5ff6ea9ab25bc770ac0"
# 不想安装python可以在release中用decode.exe 替换python decode.py，
```
## 2.生成
最简单的用法：
```py
python main.py -d <dataset_path>
```
复杂一点的
```py
python main.py -d <dataset_path>
                -s 开始日期，默认2023.1.1
                -e 结束日期，默认2023.12.31
                -n 使用备注还是微信名，默认 0：0备注 1微信名 2自己输入
                -m 范围，默认 0：0单人或单群 1为所有群生成 2为所有人生成
# 示例
python main.py -d "E:/(com.tencent.mm)/apps/com.tencent.mm/r/MicroMsg/67fec1410543c5ff6ea9ab25bc770ac0" -s "2023.1.1" -e "2023.12.31" -n 0 -m 0
# 不想安装python可以在release中用main.exe 替换python main.py，
```