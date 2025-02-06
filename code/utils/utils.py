import os
import time
import subprocess
from openai import OpenAI
from faster_whisper import WhisperModel
from .srt import whisper_segments_to_dict
from .srt import generate_srt_from_result, generate_bi_lan_srt_from_result
import os
import time
from typing import Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

def translate(result: Dict, api_key: str, base_url: str = None, model: str = None, local: bool = False,
              language: str = None, wait_time: float = None, srt: bool = True, output_path: str = None, context_window: int = 1) -> Dict:
    """
    使用翻译功能进行文本翻译

    -- 参数

    - **result**: 包含待翻译文本的字典。
    - **api_key**: OpenAI API KEY。
    - **base_url**: API 代理 URL，默认值为 `None`。
    - **model**: 使用的模型名称，默认值为 `None`。
    - **local**: 是否使用本地大模型翻译，默认值为 `False`。
    - **language**: 翻译目标语言，默认值为 `None`。
    - **wait_time**: 每次请求后的等待时间（秒），默认值为 `None`。
    - **srt**: 是否直接输出 SRT 字幕，默认值为 `False`。
    - **output_path**: SRT 字幕输出位置，如 `D://Chenyme-AAVT/output/`，默认值为 `None`。
    - **context_window**: 上下文窗口大小，默认值为 `1`，即前后各包含一句上下文。

    -- 返回值

    - **Dict**: 包含翻译结果的字典。
    """

    if output_path is None:
        output_path = os.getcwd().replace("\\", "/")
    if local is True:
        if base_url is None or model is None:
            raise ValueError("Local开启时，将使用本地大模型翻译，必须填写 base_url （模型本地调用端口） 和 model （模型名称）!")
        else:
            print("*** 本地大语言模型 翻译模式 ")
    else:
        print("*** API接口 翻译模式 ***")
        if base_url is None:
            base_url = "https://api.openai.com/v1"
        if model is None:
            model = "gpt-3.5-turbo"
        if language is None:
            language = "中文"
        if wait_time is None:
            wait_time = 0.01

    print(f"- 翻译引擎：{model}")
    if base_url != "https://api.openai.com/v1":
        print(f"代理已开启，URL：{base_url}\n")
    print("- 翻译内容：\n")

    client = OpenAI(api_key=api_key, base_url=base_url)
    segments = result['segments']
    num_segments = len(segments)

    for segment_id, segment in enumerate(segments):
        text = segment['text']
        start_index = max(0, segment_id - context_window)
        end_index = min(num_segments, segment_id + context_window + 1)

        context = " ".join([segments[i]['text'] for i in range(start_index, end_index) if i != segment_id])

        print(f"Translating segment {segment_id + 1}/{num_segments} with context.")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一名专业的翻译专家，擅长处理视频语音识别内容的翻译。"},
                {"role": "user", "content": f"请将以下视频语音识别内容翻译成{language},并确保翻译后的文本上下文连贯、自然流畅。注意：只需给出翻译后的句子，禁止出现其他任何内容！\n上下文: {context}\n内容: {text}"}
            ])
        
        answer = response.choices[0].message.content
        result['segments'][segment_id]['text'] = answer
        print(answer)
        time.sleep(wait_time)

    if srt is True:
        srt_content = generate_srt_from_result(result)
        # srt_content = generate_bi_lan_srt_from_result(result)
        with open(os.path.join(output_path, "translated_output.srt"), 'w', encoding='utf-8') as srt_file:
            srt_file.write(srt_content)
        print(f"\n- 翻译字幕保存目录：{output_path}\n")

    return result

def merge(video_name: str, srt_name: str, output_path: str = None, font: str = "system", font_size: int = 18,
          font_color: str = "FFFFFFF", subtitle_model: str = "硬字幕", quality: str = "medium", crf: int = 23):
    """
    将视频文件与字幕文件合并,支持多种编码器预设以调整编码速度和质量。

    -- 参数
    - **video_name**: 输入视频文件的路径。
    - **srt_name**: 输入字幕文件的路径。
    - **output_path**: 输出视频文件的路径，默认值为当前目录。
    - **font**: 字幕字体名称，默认值为 'system'。
    - **font_size**: 字幕字体大小，默认值为 18。
    - **font_color**: 字幕字体颜色，默认值为 'HFFFFFF'（白色，ASS 格式）。
    - **subtitle_model**: 字幕模式，默认值为 '硬字幕'。
    - **quality**: 编码器预设，默认值为 `medium`。可选值包括：
        - `ultrafast`: 最快的编码速度，但质量最低，文件最大。
        - `superfast`: 非常快的编码速度，质量和文件大小有所提升。
        - `veryfast`: 很快的编码速度，适用于实时编码或需要快速处理的情况。
        - `faster`: 比较快的编码速度，质量进一步提高。
        - `fast`: 快速编码速度，质量较好。
        - `medium`: 默认预设，编码速度和质量的平衡点。
        - `slow`: 较慢的编码速度，输出质量更高，文件更小。
        - `slower`: 更慢的编码速度，质量进一步提高。
        - `veryslow`: 非常慢的编码速度，质量最高，文件最小。
        - `placebo`: 极慢的编码速度，质量微小提升，不推荐使用，除非对质量有极高要求且不在意编码时间。
    - **crf**: 恒定速率因子，CRF 值的范围通常为 0 到 51，数值越低，质量越高。建议值：
        - `0`: 无损压缩，质量最高，文件最大。
        - `18`: 视觉上接近无损，非常高的质量，文件较大。
        - `23`: 默认值，质量和文件大小的平衡点。
        - `28`: 较低的质量，文件较小。
    -- 返回值

    - None
    """

    if output_path is None:
        output_path = os.getcwd().replace("\\", "/")

    def check_amf_support():
        try:
            result = subprocess.run(["ffmpeg", "-hwaccels"], capture_output=True, text=True)
            return "amf" in result.stdout
        except Exception as e:
            print(f" GPU 加速不可用，请检查 AMF 是否配置成功！")
            return False

    amf_supported = check_amf_support()

    if subtitle_model == "硬字幕":
        if amf_supported:
            command = f"""ffmpeg -hwaccel amf -i {video_name} -vf "subtitles={srt_name}:force_style='FontName={font},FontSize={font_size},PrimaryColour=&H{font_color}&,Outline=1,Shadow=0,BackColour=&H9C9C9C&,Bold=-1,Alignment=2'" -c:v h264_amf -crf {crf} -y -c:a copy final_output.mp4"""
        else:
            command = f"""ffmpeg -i {video_name} -vf "subtitles={srt_name}:force_style='FontName={font},FontSize={font_size},PrimaryColour=&H{font_color}&,Outline=1,Shadow=0,BackColour=&H9C9C9C&,Bold=-1,Alignment=2'" -preset {quality} -c:v libx264 -crf {crf} -y -c:a copy final_output.mp4"""
    else:
        if amf_supported:
            command = f"""ffmpeg -hwaccel amf -i {video_name} -i {srt_name} -c:v h264_amf -crf {crf} -y -c:a copy -c:s mov_text -preset {quality} final_output.mp4"""
        else:
            command = f"""ffmpeg -i {video_name} -i {srt_name} -c:v libx264 -crf {crf} -y -c:a copy -c:s mov_text -preset {quality} final_output.mp4"""

    subprocess.run(command, shell=True, cwd=output_path)

    return None


def whisper_faster(file_path: str, model: str, device: str = "cpu", prompt: str = None, lang: str = "auto", beam_size: int = 5,
                   vad: bool = False, min_vad: int = 500, srt: float = False, output_path: str = None) -> dict:
    """
    使用 Faster Whisper 模型进行音频转录

    -- 参数

    - **file_path**: 要识别的音频文件的路径。
    - **model**: Whisper 模型，支持 `tiny`, `tiny.en`, `base`, `base.en`, `small`, `small.en`, `medium`, `medium.en`, 
                `large-v1`, `large-v2`, `large-v3`, `large`, `distil-small.en`, `distil-medium.en`, `distil-large-v2`, `distil-large-v3`。
    - **device**: 运行设备，可以是 `cpu` 或 `cuda`，默认值为 `cpu`。
    - **prompt**: Faster Whisper 提示词，默认值为 `None`。
    - **lang**: 指定语言，`auto` 表示自动检测语言，默认值为 `auto`。
    - **beam_size**: 束搜索宽度，影响解码过程中的候选数量，默认值为 `5`。
    - **vad**: 是否使用声音活动检测，默认值为 `False`。
    - **min_vad**: 声音活动检测的最小持续时间（毫秒），默认值为 `500`。
    - **srt**: 是否直接输出 SRT 字幕，默认值为 `False`。
    - **output_path**: SRT 字幕输出位置，如 `D://Chenyme-AAVT/output/`，默认值为 `None`。

    -- 返回值

    - **Dict**: 包含转录文本和可能的其他信息的字典，或 SRT 字幕文件。

    """

    if model not in ['tiny', 'tiny.en', 'base', 'base.en', 'small', 'small.en', 'medium', 'medium.en', 
                     'large-v1', 'large-v2', 'large-v3', 'large', 
                     'distil-small.en', 'distil-medium.en', 'distil-large-v2', 'distil-large-v3']:
        print("*** Faster Whisper 本地模型加载模式 ***")
    else:
        print("*** Faster Whisper 调用模式 ***")
    print(f"- 运行模型：{model}")
    print(f"- 运行方式：{device}")
    print(f"- VAD辅助：{vad}")
    if device is None:
        device = "cpu"
    if prompt is None:
        prompt = "Don’t make each line too long."
    if output_path is None:
        output_path = os.getcwd().replace("\\", "/")
    if device not in ["cuda", "cpu"]:
        raise ValueError("device 参数只能是 ‘cuda’,'cpu' 中的一个")

    model = WhisperModel(model, device)

    if lang == "auto" and vad is False:
        segments, _ = model.transcribe(file_path,
                                       initial_prompt=prompt,
                                       beam_size=beam_size,
                                       )
    elif lang == "auto" and vad is True:
        segments, _ = model.transcribe(file_path,
                                       initial_prompt=prompt,
                                       beam_size=beam_size,
                                       vad_filter=vad,
                                       vad_parameters=dict(min_silence_duration_ms=min_vad)
                                       )
    elif vad is False:
        segments, _ = model.transcribe(file_path,
                                       initial_prompt=prompt,
                                       language=lang,
                                       beam_size=beam_size,
                                       )
    elif vad is True:
        segments, _ = model.transcribe(file_path,
                                       initial_prompt=prompt,
                                       language=lang,
                                       beam_size=beam_size,
                                       vad_filter=vad,
                                       vad_parameters=dict(min_silence_duration_ms=min_vad)
                                       )
    result = whisper_segments_to_dict(segments)

    if srt is True:
        srt_content = generate_srt_from_result(result)
        with open(output_path + "/original_output.srt", 'w', encoding='utf-8') as srt_file:
            srt_file.write(srt_content)
        print(f"- 原始字幕已保存在：{output_path}\n")

    return result
