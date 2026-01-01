ARCAEA自动游玩项目，代码源于arcaea-sap
可以在arcaea的全量安装包中提取aff文件

Click here to switch English
https://github.com/AeonS-D/arcaea-auto-play/blob/main/README_EN.md

## 免责声明：

该项目仅供学习交流，关于恶意使用引起的纠纷与该项目无关



## 关于修改项目：

   + 1.增加了timinggroup的支持
  
   + 2.修改操作模式，手动开始模拟触控，即在note下落的一瞬间开始模拟

   + 3.记忆功能，现在不需要每次重启脚本后重复进行输入坐标，但请不要删去目录下配置文件，会闪退（懒得修），如果包里面没有配置文件，在code处下载并放置在脚本根目录

   + 4.快捷修改各个参数，也可以在配置文件中修改

   + 5.增加6k触控模式

   + 6.加入一堆屎山代码（别喷）

   

## 关于注意事项

   + 1.建议使用python3.11，用3.11往后版本可能报错（经测试，3.13会报）

   + 2.安装目录下requirements依赖包

    pip install -r requirements.txt

   + 3.下载scrcpy-server置放到根目录

    https://github.com/Genymobile/scrcpy/releases/

   + 4.安装Android debug bridge，并配置好相应环境

   + 5.配置文件中为小米平板5的各项参数，理论上来说为11寸平板通用

   + 6.win11下，使用windows powershell可能会导致一些奇奇怪怪的bug，请更换默认控制台cmd使用脚本

   + 6.5.并不打算再增加愚人节谱面的支持，尝试过，效果不尽人意
   
   + 7.如果出现arc头部夹着note或者hold（反之亦然）并且执行操作时会使arc断触，只需要微调延迟至note判定为pure（early）即可

   + 8.关于各个点的坐标如下：
   ![413854432-ea62cdad-0c67-4c66-b3fc-aaebe0772622](https://github.com/user-attachments/assets/b1c6e676-9016-4349-a4bf-f14583dae300)

   

## 关于将要加入的功能：

  + 将其做成gui（打算而已）
  

## 日志
25年8月8日凌晨1点28分，奥托先生成功理论byd风暴，可喜可贺，可喜可贺


![Screenshot_2025-08-08-01-28-57-496_moe inf arc 1](https://github.com/user-attachments/assets/d2f0e3dc-563f-410f-9f3a-28dcc7f93256)

25年12月13日下午5点22分，完成了6k模式的制作，奥托先生pm byd ttf，这个脚本最后一块拼图接上了，但是由于一些小问题，想理论还需要一段时间

![Screenshot_2025-12-13-16-30-36-228_moe inf arc](https://github.com/user-attachments/assets/200884e2-ede9-4c0b-8e9d-83db00fc46b9)

