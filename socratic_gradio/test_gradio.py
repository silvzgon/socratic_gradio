import gradio as gr
from openai import OpenAI
import json
import prompts

key = '' # api key here
max_try = 3
client = OpenAI(api_key=key)

def agent_calling(messages):
    count = 0
    while 1:
        count += 1
        try:
            completion = client.chat.completions.create(
                model='gpt-4o',
                messages=messages
            )
            return completion.choices[0].message.content
        except Exception as e:
            if count > max_try:
                raise Exception(f'调用AI代理时出错。错误：{e}')
            else:
                print('[警告] 调用AI代理时出错，正在重试...')

def load_history():
    try:
        with open('history/history.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f'[警告] 读取历史记录时出错，自动初始化。错误: {e}')
        return []

def save_history(history):
    with open('history/history.json', 'w', encoding='utf-8') as file:
        json.dump(history, file, ensure_ascii=False, indent=4)

def load_steps():
    with open('temp/step.json', 'r', encoding='utf-8') as file:
        return json.load(file)

def chat_interface(message):
    global current_step, steps, messages, chat_history

    if not messages:

        # 开始新的步骤
        if current_step < len(steps):
            step = steps[current_step]
            response1 = agent_calling([
                {'role': 'system', 'content': prompts.subtasks_start_system},
                {'role': 'user', 'content': prompts.subtasks_start + step}
            ])
            chat_history.append(f"【老师】：{response1}")
            messages = [
                {'role': 'system', 'content': prompts.subtasks_system},
                {'role': 'user', 'content': prompts.subtasks + steps[current_step] + '\n#输出：'}
            ]
            response2 = agent_calling(messages)
            messages.append({'role': 'assistant', 'content': response2})
            chat_history.append(f"【老师】：{response2}")
            save_history(chat_history)
            return [response1, response2]
        
        # 全部步骤结束，程序自动保存
        else:
            current_step = 0
            save_history(chat_history)
            return ["所有步骤已完成。是否要重新开始？"]
    
    # 跳过当前步骤
    if message.lower() == '\\skip':
        current_step += 1
        if current_step < len(steps): return ["好的，我们跳过这个步骤。"]
        else: return ["好的，我们跳过这个步骤。", "所有步骤已完成。是否要重新开始？"]
    
    else:
        messages.append({'role': 'user', 'content': message})
        chat_history.append(f"【学生】：{message}")
        response1 = agent_calling(messages)
        messages.append({'role': 'assistant', 'content': response1})
        chat_history.append(f"【老师】：{response1}")
        
        # 添加步骤结束后的完整代码检查
        if '【结束】' in response1:
            response1 = response1.replace('【结束】', '')
            messages = [
                {'role': 'system', 'content': prompts.subtasks_end_system},
                {'role': 'user', 'content': prompts.subtasks_end + steps[current_step]}
            ]
            response2 = agent_calling(messages)
            messages.append({'role': 'assistant', 'content': response2})
            chat_history.append(f"【老师】：{response2}")
            current_step += 1
            return [response1, response2]

        # 当前步骤结束，进行下一步骤
        elif '【正确】' in response1:
            response1 = response1.replace('【正确】', '')
            messages = []
            response = chat_interface("")
            response.insert(0, response1)
            return response

        return [response1]

# 全局变量
current_step = 0
steps = []
messages = []
chat_history = []

# 创建Gradio界面
with gr.Blocks() as iface:
    
    # 初始化
    current_step = 0
    steps = load_steps()
    chat_history = load_history()

    bot_message = chat_interface("")
    history = [[None, bot_message[0]], [None, bot_message[1]]]

    chatbot = gr.Chatbot(label="对话历史", value=history)
    msg = gr.Textbox(label="输入")
    download = gr.DownloadButton(label="下载记录", value='history/history.json')
    clear = gr.Button("清除对话")

    def user(user_message, history):
        return "", history + [[user_message, None]]

    def bot(history):
        user_message = history[-1][0]
        bot_message = chat_interface(user_message)
        save_history(chat_history)
        for i in range(len(bot_message)):
            history.append([None, bot_message[i]])
        return history, gr.update(value='history/history.json')
    
    def reset():
        global current_step, messages
        current_step = 0
        messages = []
        bot_message = chat_interface("")
        history = [[None, bot_message[0]], [None, bot_message[1]]]
        return gr.update(value=history)

    msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(bot, chatbot, [chatbot, download])
    clear.click(reset, None, chatbot, queue=False)

# 运行Gradio应用
if __name__ == "__main__":
    iface.launch()
