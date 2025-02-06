import requests
import re
import os
import json
import subprocess


class BilibiliVideoDownloader:
    def __init__(self, headers):
        self.headers = headers
    
    def get_response(self, url):
        print(f"Fetching URL: {url}")
        response = requests.get(url=url, headers=self.headers)
        print(f"Response status code: {response.status_code}")
        return response

    def get_video_info(self, html_url):
        print(f"Getting video info for URL: {html_url}")
        response = self.get_response(html_url)
        ex = '</script> <title data-vue-meta="true">(.*?)</title>'
        title = re.findall(ex, response.text)[0].replace(' ', '')
        title = re.sub(r'[<>:"/\\|?*]', '', title)
        video_info = [title]
        print(f"Video title: {title}")
        return video_info

    def get_video_content(self, BV_ID, params):
        index_url = f'https://www.bilibili.com/video/{BV_ID}/'
        print(f"Getting video content for URL: {index_url} with params: {params}")
        page_text = requests.get(url=index_url, params=params, headers=self.headers).text
        ex = 'window\\.__playinfo__=({.*?})\\s*</script>'
        json_data = re.findall(ex, page_text)[0]
        data = json.loads(json_data)
        audio_url = data['data']['dash']['audio'][0]['baseUrl']
        video_url = data['data']['dash']['video'][0]['baseUrl']
        video_content = [audio_url, video_url]
        print(f"Audio URL: {audio_url}")
        print(f"Video URL: {video_url}")
        return video_content
    
    # @staticmethod
    def save_audio(self, title, audio_url):
        print(f"Saving audio data for title: {title}")
        audio_content = self.get_response(audio_url).content
        with open(f"./b_video/{title}.mp3", "wb") as fp:
            fp.write(audio_content)
        print(f"audio {title} 保存完成")

    # @staticmethod
    def save_video(self, title, video_url):
        print(f"Saving video data for title: {title}")
        video_content = self.get_response(video_url).content
        with open(f"./b_video/{title}.mp4", "ab") as fp:
            fp.write(video_content)
        print(f"{title} 保存完成")

    def save(self, title, audio_url, video_url):
        print(f"Saving data for title: {title}")
        audio_content = self.get_response(audio_url).content
        video_content = self.get_response(video_url).content
        with open(f"./b_video/{title}.mp3", "wb") as fp:
            fp.write(audio_content)
        with open(f"./b_video/{title}.mp4", "ab") as fp:
            fp.write(video_content)
        print(f"{title} 保存完成")

    def merge_data(self, video_name):
        print(f"Merging data for video: {video_name}")
        input_video_path = f"./b_video/{video_name}.mp4"
        input_audio_path = f"./b_video/{video_name}.mp3"
        output_path = f"./b_video/bili_output.mp4"

        # 使用 AMD 显卡加速进行视频编解码
        cmd = (
            f"ffmpeg -i {input_video_path} -i {input_audio_path} "
            f"-c:v h264_amf -c:a aac -strict experimental -y {output_path}"
        )
        subprocess.run(cmd, shell=True)

        # 删除输入文件，保留合并后的文件
        # os.remove(input_video_path)
        # os.remove(input_audio_path)

        print(f"Merging completed for video: {video_name}")

