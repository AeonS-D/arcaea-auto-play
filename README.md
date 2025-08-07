ARCAEA自动游玩项目，代码源于arcaea-sap
可以在arcaea的全量安装包中提取aff文件

Click here to switch English
https://github.com/AeonS-D/arcaea-auto-play/blob/main/README_EN.md

## 免责声明：

该项目仅供学习交流，关于恶意使用引起的纠纷与该项目无关



## 关于修改项目：

   + 1.加入对谱面文件中timinggroup()的支持（实际就是创建临时的谱面文件用正则表达式删去timinggroup()及空格，简单粗暴）
   + 1.5 在2.0版本新增了timinggroup的支持，我们不需要用第一条了
  
   + 2.修改操作模式，手动开始模拟触控，即在note下落的一瞬间开始模拟，请不要调整此处延迟，脚本会自动调节，用于爬梯

   + 3.记忆功能，现在不需要每次重启脚本后重复进行输入坐标，但请不要删去目录下配置文件，会闪退（懒得修）

   + 4.快捷修改各个参数，也可以在配置文件中修改

   + 5.加入一堆屎山代码（别喷）

   

## 关于注意事项

   + 1.建议使用python3.11，用3.11往后版本可能报错（经测试，3.13会报）

   + 2.安装目录下requirements依赖包

    pip install -r requirements.txt

   + 3.下载scrcpy-server置放到根目录

    https://github.com/Genymobile/scrcpy/releases/

   + 4，安装Android debug bridge，并配置好相应环境

   + 5.配置文件中为小米平板5的各项参数，理论上来说为11寸平板通用

   + 6.关于各个点的坐标可能如下：
   ![413854432-ea62cdad-0c67-4c66-b3fc-aaebe0772622](https://github.com/user-attachments/assets/b1c6e676-9016-4349-a4bf-f14583dae300)

   

## 关于将要加入的功能：

  + 计划加入在执行触控的时候通过调整延迟来修复由于触控开始时机不对导致的误差（计划而已）

  + 计划将其做成gui（打算而已）
  

  


不会真的有人想用这个理论ttf吧？又没啥用，拿来爬爬梯子得（笑

## 日志
25年8月8日凌晨1点28分，奥托先生成功理论byd风暴，可喜可贺，可喜可贺


![Screenshot_2025-08-08-01-28-57-496_moe inf arc 1](https://github.com/user-attachments/assets/d2f0e3dc-563f-410f-9f3a-28dcc7f93256)
