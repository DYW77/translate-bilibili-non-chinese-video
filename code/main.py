import os
import subprocess
from urllib.parse import urlparse, parse_qs
from multiprocessing import Process, Manager
from utils.BiliVD import BilibiliVideoDownloader
from utils.utils import whisper_faster, translate, merge

# 创建目录
if not os.path.exists("./b_video"):
    os.mkdir("./b_video")

# HTTP Headers
headers = {
    # 需要自行设置Cookie
    'Cookie': "buvid3=4169A956-029D-9CA-C220-03534CED9D0730351infoc; i-wanna-go-back=-1; b_ut=7; _uuid=C5101B9CA-1010B3-F1C9-10F105-7C93C9310D84E31244infoc; DedeUserID=22019356; DedeUserID__ckMd5=f01e34cf922e09ca; header_theme_version=CLOSE; hit-new-style-dyn=1; hit-dyn-v2=1; rpdid=|(k|k)RumR))0J'uYm|Rku)uR; LIVE_BUVID=AUTO2416904604298356; buvid_fp_plain=undefined; home_feed_column=5; b_nut=1696857643; buvid4=73B2770C-7948-87F7-50D6-A697FD6770C531684-023072709-Vp25bGcbK8biUmg9WgJLvA%3D%3D; enable_web_push=DISABLE; go-back-dyn=1; FEED_LIVE_VERSION=V_WATCHLATER_PIP_WINDOW3; CURRENT_QUALITY=80; SESSDATA=df5a817b%2C1728297896%2C2c6c4%2A42CjBV6WwTTQlq9Cn07hlLbJd4pDlef5EOHVGayJY8wBtcwtfyrbKYZOZ1Od-zfnOPk_oSVnNUODlKak51SVFXbnVCQjdqbEZJREhmcjJEdHZTOWlRcW15N2dVTTROVFJlUmNZSVJqb1BVY0VPeDJXSW9idlI1OTVmMnFYOEczVjhiRzhVVXllaXZ3IIEC; bili_jct=bd99d9bb71b2f8bd265a8cd23061544f; sid=75qb4k89; CURRENT_FNVAL=16; browser_resolution=1915-974; fingerprint=da1029e4adb38ec5e64e5632a7459441; buvid_fp=3fe9d6b84d14f220f303f4099af2161b; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MTgxODMwNTAsImlhdCI6MTcxNzkyMzc5MCwicGx0IjotMX0.jXcX4Ni43naq1LL272JzC303rlLUv3H1Pd8VqeVFhxY; bili_ticket_expires=1718182990; PVID=1; bp_t_offset_22019356=940971521718878338; b_lsid=10D631C45_18FFC9F3149",
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    'referer': 'https://t.bilibili.com/'
}

def process_audio(video_name, result_dict):
    result = whisper_faster(f"./b_video/{video_name}.mp3", 
                            "tiny", 
                            "cpu",
                            vad=True,
                            srt=True,
                            output_path="./srt")
    result_dict['result'] = result

def process_video(video_name, BiliVedioDown,video_info,video_content, BV_ID):
    BiliVedioDown.save_video(video_info[0], video_content[1])
    BiliVedioDown.merge_data(video_name)
    print(f"Main process completed for BV_ID: {BV_ID}")

def main_process(b_url, mode):
    """
    mode选项：
        1 - 单纯爬虫：仅保存视频和音频文件，不生成字幕
        2 - 单纯字幕生成：仅生成原语音的字幕，不进行翻译
        3 - 生成字幕与翻译：生成字幕并调用API对字幕进行翻译，然后合并
    """
    parsed_url = urlparse(b_url)
    query_params = parse_qs(parsed_url.query)

    BV_ID = parsed_url.path.split("/")[2]
    spm_id_from = query_params.get("spm_id_from", [None])[0]
    vd_source = query_params.get("vd_source", [None])[0]

    params = {}
    if spm_id_from:
        params["spm_id_from"] = spm_id_from
    if vd_source:
        params["vd_source"] = vd_source

    print(f"提取到的 BV_ID: {BV_ID}")
    print(f"提取到的参数: {params}")
    print(f"开始处理 BV_ID: {BV_ID}，操作选项: {mode}")

    html_url = f"https://www.bilibili.com/video/{BV_ID}/"
    BiliVedioDown = BilibiliVideoDownloader(headers)

    # 得到视频及音频信息
    video_info = BiliVedioDown.get_video_info(html_url)
    video_content = BiliVedioDown.get_video_content(BV_ID, params)

    # 不论哪种模式，先保存音频文件
    BiliVedioDown.save_audio(video_info[0], video_content[0])

    if mode == '1':
        # 单纯爬虫：保存视频和音频，不生成字幕和翻译
        BiliVedioDown.save_video(video_info[0], video_content[1])
        BiliVedioDown.merge_data(video_info[0])
        print("爬虫任务完成：视频和音频已保存。")

    elif mode == '2':
        # 单纯字幕生成：仅对音频进行转写生成内部字幕文件，无翻译处理
        manager = Manager()
        result_dict = manager.dict()
        audio_process = Process(target=process_audio, args=(video_info[0], result_dict))
        audio_process.start()
        audio_process.join()
        print("字幕生成完成，生成的字幕存放在 ./srt 文件夹中。")
        
    elif mode == '3':
        # 生成字幕与翻译：生成字幕，再调用API进行翻译，最后合并字幕到视频中
        # 同时，视频也会被下载和合并
        manager = Manager()
        result_dict = manager.dict()
        audio_process = Process(target=process_audio, args=(video_info[0], result_dict))
        video_process = Process(target=process_video, args=(video_info[0], BiliVedioDown, video_info, video_content, BV_ID))
        audio_process.start()
        video_process.start()
        audio_process.join()
        video_process.join()
        result = result_dict['result']
        translate(result=result, 
                  # 请自行设置API
                  api_key="sk-rvFxko4f3pRTbngBRJduR8bDZVVKZ9mT3l59sHya1FaTdqCX", 
                  base_url="https://api.moonshot.cn/v1",
                  model="moonshot-v1-128k",
                  language="Chinese",
                  srt=True,
                  output_path="./srt",
                  context_window=3,
                  )
        merge("./b_video/bili_output.mp4", "./srt/translated_output.srt")
        print("字幕生成与翻译任务完成，生成了带翻译字幕的视频文件。")
    else:
        print("无效的操作选项，请选择 1、2 或 3。")

if __name__ == "__main__":
    print("请选择操作选项：")
    print("1 - 单纯爬虫（仅爬取视频与音频）")
    print("2 - 单纯字幕生成（仅生成原语音字幕）")
    print("3 - 生成字幕与翻译（生成原语音字幕并进行翻译，最后合并到视频）")
    mode = input("请输入操作选项（1/2/3）：").strip()
    b_url = input("输入爬取视频的网址:").strip()
    main_process(b_url, mode)

# def main_process(b_url):
#     parsed_url = urlparse(b_url)
#     query_params = parse_qs(parsed_url.query)

#     BV_ID = parsed_url.path.split("/")[2]
#     spm_id_from = query_params.get("spm_id_from", [None])[0]
#     vd_source = query_params.get("vd_source", [None])[0]

#     params = {}
#     if spm_id_from:
#         params["spm_id_from"] = spm_id_from
#     if vd_source:
#         params["vd_source"] = vd_source

#     print(f"Extracted BV_ID: {BV_ID}")
#     print(f"Extracted params: {params}")
#     print(f"Starting main process for BV_ID: {BV_ID} with params: {params}")

#     html_url = f"https://www.bilibili.com/video/{BV_ID}/"

#     BiliVedioDown = BilibiliVideoDownloader(headers)

#     video_info = BiliVedioDown.get_video_info(html_url)
#     video_content = BiliVedioDown.get_video_content(BV_ID, params)

#     BiliVedioDown.save_audio(video_info[0], video_content[0])
#     # BiliVedioDown.save_video(video_info[0], video_content[1])

#     # 创建进程管理器以共享数据
#     manager = Manager()
#     result_dict = manager.dict()

#     # 创建进程
#     audio_process = Process(target=process_audio, args=(video_info[0], result_dict))
#     video_process = Process(target=process_video, args=(video_info[0], BiliVedioDown, 
#                                                         video_info, video_content, BV_ID ))

#     # 启动进程
#     audio_process.start()
#     video_process.start()

#     # 等待进程完成
#     audio_process.join()
#     video_process.join()

#     # 获取结果并传递给translate函数
#     result = result_dict['result']
#     translate(result=result, 
#               # 需要自行设置API
#               api_key="sk-rvFxko4f3pRTbngBRJduR8bDZVVKZ9mT3l59sHya1FaTdqCX", 
#               base_url="https://api.moonshot.cn/v1",
#               model="moonshot-v1-128k",
#               language="Chinese",
#               srt=True,
#               output_path="./srt",
#               context_window = 3,
#               )

#     merge("./b_video/bili_output.mp4", "./srt/translated_output.srt")

# if __name__ == "__main__":
#     b_url = input("输入爬取视频的网址:")
#     main_process(b_url)