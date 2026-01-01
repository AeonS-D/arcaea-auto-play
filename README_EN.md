ARCAEA Auto Play Project, code originally from arcaea-sap
AFF files can be extracted from the full installation package of arcaea

Click here to switch to Chinese
https://github.com/AeonS-D/arcaea-auto-play/blob/main/README.md

## Disclaimer:

This project is for learning and communication purposes only. Any disputes arising from malicious use are not related to this project.

## About Project Modifications:

   + 1. Added support for timing groups
  
   + 2. Modified operation mode to manually start simulation, i.e., start simulation at the moment notes fall

   + 3. Memory function: no need to repeatedly input coordinates after restarting the script, but do not delete the configuration file in the directory (it will crash - too lazy to fix). If the package doesn't contain the configuration file, download it from the code and place it in the script root directory

   + 4. Quick modification of various parameters, also can be modified in the configuration file

   + 5. Added 6k touch mode

   + 6. Added a bunch of spaghetti code (don't criticize)

## About Important Notes

   + 1. Recommend using Python 3.11, later versions may cause errors (tested, 3.13 does)

   + 2. Install required dependency packages in the requirements file

    pip install -r requirements.txt

   + 3. Download scrcpy-server and place it in the root directory

    https://github.com/Genymobile/scrcpy/releases/

   + 4. Install Android debug bridge and configure the corresponding environment

   + 5. The configuration file contains parameters for Xiaomi Pad 5, theoretically universal for 11-inch tablets

   + 6. On Win11, using Windows PowerShell may cause strange bugs, please switch to the default console cmd when using the script

   + 6.5. No plans to add support for April Fools' charts, attempted but results were unsatisfactory
   
   + 7. If notes or holds appear embedded in the head of arcs (or vice versa) and cause arc breaks during execution, simply fine-tune the delay until notes are judged as pure (early)

   + 8. About coordinate points:
   ![413854432-ea62cdad-0c67-4c66-b3fc-aaebe0772622](https://github.com/user-attachments/assets/b1c6e676-9016-4349-a4bf-f14583dae300)

## About Future Features:

  + Plan to create a GUI (just planning for now)
  

## Logs
August 8, 2025, 1:28 AM, Mr. Auto successfully theoretically achieved BYD storm, congratulations, congratulations


![Screenshot_2025-08-08-01-28-57-496_moe inf arc 1](https://github.com/user-attachments/assets/d2f0e3dc-563f-410f-9f3a-28dcc7f93256)

December 13, 2025, 5:22 PM, completed 6k mode production, Mr. Auto PM BYD TTF, the final piece of this script is complete, but due to minor issues, it will take some time to achieve theoretical


![Screenshot_2025-12-13-16-30-36-228_moe inf arc](https://github.com/user-attachments/assets/200884e2-ede9-4c0b-8e9d-83db00fc46b9)
