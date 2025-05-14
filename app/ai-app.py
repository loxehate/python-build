import os
from http import HTTPStatus
from dashscope import Application

# 设置 API Key 和私网终端节点
os.environ['DASHSCOPE_API_KEY'] = 'sk-021baf918e8e4318b528180c4c59c072'  # 替换为您的 API Key
os.environ['DASHSCOPE_HTTP_BASE_URL'] = 'https://dashscope.aliyuncs.com/api/v1/ '

# 替换为实际的应用 ID
APP_ID = 'f423063f3610424cafa32e4f5625da9b'

def chat_with_application():
    print('欢迎使用ops应用！请输入您的问题（输入 "exit" 退出对话）：')
    
    while True:
        user_input = input("您: ")
        
        if user_input.lower() == 'exit':
            print("退出对话。感谢使用！")
            break
        
        try:
            response = Application.call(
                api_key=os.getenv('DASHSCOPE_API_KEY'),
                app_id=APP_ID,
                prompt=user_input
            )

            if response.status_code != HTTPStatus.OK:
                print(f"请求失败！请参考错误信息：")
                print(f'request_id={response.request_id}')
                print(f'code={response.status_code}')
                print(f'message={response.message}')
                print(f'请查阅文档以获取更多信息：https://help.aliyun.com/zh/model-studio/developer-reference/error-code ')
            else:
                print(f"助手: {response.output.text}")
                
        except Exception as e:
            print(f"发生异常: {e}")

if __name__ == '__main__':
    chat_with_application()