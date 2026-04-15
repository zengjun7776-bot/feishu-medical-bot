from flask import Flask, request, jsonify
import requests
import json
import os

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """处理飞书发送过来的消息"""
    try:
        data = request.json
        print("🎯 收到飞书消息:", json.dumps(data, indent=2))
        
        # 1. 如果是飞书的验证请求
        if data.get('type') == 'url_verification':
            challenge = data.get('challenge')
            print(f"✅ 验证通过，challenge: {challenge}")
            return jsonify({'challenge': challenge})
        
        # 2. 处理文本消息
        if data.get('event', {}).get('message', {}).get('message_type') == 'text':
            event = data['event']
            content = json.loads(event['message']['content'])
            user_message = content.get('text', '').strip()
            
            print(f"💬 用户消息: {user_message}")
            
            # 3. 调用智能回复逻辑
            bot_reply = generate_reply(user_message)
            
            # 4. 发送回复到飞书（需要先配置webhook）
            send_to_feishu(bot_reply)
            
        return jsonify({'status': 'success'})
    except Exception as e:
        print("❌ 处理错误:", e)
        return jsonify({'status': 'error'})

def generate_reply(message):
    """生成智能回复"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['你好', 'hello', 'hi']):
        return "👋 你好！我是体检推荐助手，可以帮你推荐合适的体检项目。"
    
    elif any(word in message_lower for word in ['体检', '检查', '体检项目']):
        return """🧬 我可以根据您的信息推荐体检项目！

请告诉我：
1. 您的年龄？
2. 您的性别？
3. 近期有什么不适症状吗？

例如：我30岁，男性，最近经常疲劳"""
    
    elif any(word in message_lower for word in ['年龄', '岁']):
        return "📝 请问您的具体年龄是多少？这有助于我推荐更合适的体检项目。"
    
    elif any(word in message_lower for word in ['男', '女', '性别']):
        return "👥 请告诉我您的性别（男/女），不同性别的体检重点有所不同。"
    
    else:
        return "🤔 我主要擅长体检推荐咨询。您可以问我关于体检项目、年龄建议、性别差异等问题。"

def send_to_feishu(message):
    """发送消息到飞书（需要先配置webhook）"""
    webhook_url = os.getenv('FEISHU_WEBHOOK')
    if not webhook_url:
        print("⚠️ 未配置飞书webhook，模拟发送:", message)
        return
    
    data = {
        "msg_type": "text",
        "content": {"text": message}
    }
    
    try:
        response = requests.post(webhook_url, json=data, timeout=5)
        print(f"📤 飞书回复状态: {response.status_code}")
    except Exception as e:
        print("❌ 发送到飞书失败:", e)

@app.route('/')
def home():
    return """
    <h1>🏥 飞书体检机器人运行成功！</h1>
    <p>✅ 服务状态：正常</p>
    <p>📝 功能：体检推荐咨询</p>
    <p>🔗 请配置飞书事件订阅到: /webhook</p>
    """

@app.route('/test')
def test():
    """测试页面"""
    return "测试成功！机器人正在运行。"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 启动服务在端口: {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
