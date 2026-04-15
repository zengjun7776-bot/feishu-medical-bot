from flask import Flask, request, jsonify
import requests
import json
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 飞书开放平台配置 - 从环境变量读取
FEISHU_APP_ID = os.getenv('FEISHU_APP_ID', '')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET', '')

# 打印配置信息（验证用）
logger.info(f"🔑 飞书应用配置 - App ID: {FEISHU_APP_ID}")
logger.info(f"🔒 App Secret 已设置: {'是' if FEISHU_APP_SECRET else '否'}")

# 全局存储 access_token
tenant_access_token = None
token_expire_time = 0

def get_tenant_access_token():
    """获取租户访问令牌"""
    global tenant_access_token, token_expire_time
    
    # 检查token是否还有效（提前5分钟刷新）
    if tenant_access_token and time.time() < token_expire_time - 300:
        return tenant_access_token
    
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        logger.info(f"🔐 获取token状态: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 0:
                tenant_access_token = data.get('tenant_access_token')
                # token有效期为2小时，记录过期时间
                token_expire_time = time.time() + 7200
                logger.info("✅ 获取access_token成功")
                return tenant_access_token
            else:
                logger.error(f"❌ 获取token失败: {data}")
        else:
            logger.error(f"❌ HTTP错误: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ 获取token异常: {e}")
    
    return None

def send_message(receive_id, message_type, content):
    """发送消息到飞书"""
    token = get_tenant_access_token()
    if not token:
        logger.error("❌ 无法获取access_token，发送消息失败")
        return False
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "receive_id": receive_id,
        "msg_type": message_type,
        "content": content
    }
    
    # 根据receive_id的类型设置参数
    receive_id_type = "open_id"  # 也可以是user_id, chat_id, email等
    
    try:
        response = requests.post(
            url, 
            headers=headers, 
            params={"receive_id_type": receive_id_type},
            json=payload,
            timeout=10
        )
        
        logger.info(f"📤 发送消息状态: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 0:
                logger.info("✅ 消息发送成功")
                return True
            else:
                logger.error(f"❌ 消息发送失败: {result}")
        else:
            logger.error(f"❌ HTTP错误: {response.status_code}, {response.text}")
            
    except Exception as e:
        logger.error(f"❌ 发送消息异常: {e}")
    
    return False

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """处理飞书开放平台的事件订阅"""
    try:
        data = request.json
        logger.info("🎯 收到飞书事件订阅请求")
        
        # 1. URL 验证（飞书校验用）
        if data.get('type') == 'url_verification':
            challenge = data.get('challenge')
            logger.info(f"✅ URL验证通过, challenge: {challenge}")
            return jsonify({'challenge': challenge})
        
        # 2. 处理消息事件
        if data.get('header', {}).get('event_type') == 'im.message.receive_v1':
            event = data.get('event', {})
            sender = event.get('sender', {})
            message = event.get('message', {})
            
            # 获取发送者ID和消息内容
            sender_id = sender.get('sender_id', {})
            open_id = sender_id.get('open_id')
            message_type = message.get('message_type')
            
            logger.info(f"👤 发送者OpenID: {open_id}")
            logger.info(f"💬 消息类型: {message_type}")
            
            if message_type == 'text':
                content = json.loads(message.get('content', '{}'))
                user_message = content.get('text', '').strip()
                
                logger.info(f"📝 用户消息内容: {user_message}")
                
                # 生成回复
                bot_reply = generate_reply(user_message)
                logger.info(f"🤖 生成回复: {bot_reply}")
                
                # 发送回复
                if open_id:
                    success = send_message(open_id, "text", json.dumps({"text": bot_reply}))
                    if success:
                        logger.info("✅ 回复发送成功")
                    else:
                        logger.error("❌ 回复发送失败")
                else:
                    logger.error("❌ 无法获取发送者OpenID")
            
        return jsonify({'code': 0, 'msg': 'success'})
        
    except Exception as e:
        logger.error(f"❌ 处理webhook异常: {e}")
        return jsonify({'code': 1, 'msg': str(e)}), 500

def generate_reply(message):
    """生成智能回复"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['你好', 'hello', 'hi', '嗨']):
        return "👋 你好！我是体检推荐助手，可以帮你推荐合适的体检项目。"
    
    elif any(word in message_lower for word in ['体检', '检查', '体检项目', '体检验']):
        return """🧬 我可以根据您的信息推荐体检项目！

请告诉我：
1. 您的年龄？
2. 您的性别？
3. 近期有什么不适症状吗？

例如：我30岁，男性，最近经常疲劳"""
    
    elif any(word in message_lower for word in ['年龄', '岁', '多大']):
        return "📝 请问您的具体年龄是多少？这有助于我推荐更合适的体检项目。"
    
    elif any(word in message_lower for word in ['男', '女', '性别']):
        return "👥 请告诉我您的性别（男/女），不同性别的体检重点有所不同。"
    
    elif '重置' in message_lower or '重新开始' in message_lower:
        return "🔄 对话已重置，请重新告诉我您的需求。"
    
    elif '帮助' in message_lower or '功能' in message_lower:
        return """📋 我可以帮助您：
• 推荐适合的体检项目
• 根据不同年龄、性别定制方案
• 解答体检相关问题

请告诉我您的需求！"""
    
    else:
        return "🤔 我主要擅长体检推荐咨询。您可以问我关于体检项目、年龄建议、性别差异等问题，或者发送'帮助'查看功能。"

@app.route('/')
def home():
    return """
    <h1>🏥 飞书开放平台体检机器人</h1>
    <p>✅ 服务状态：<strong>正常运行</strong></p>
    <p>🔗 事件订阅URL: /webhook</p>
    <p>📱 应用类型：开放平台应用</p>
    <p>🕐 启动时间：正常</p>
    <p><a href="/health">健康检查</a></p>
    """

@app.route('/health')
def health_check():
    """健康检查端点"""
    return jsonify({
        'status': 'healthy',
        'service': 'feishu-medical-bot',
        'timestamp': time.time()
    })

@app.route('/test')
def test():
    """测试页面"""
    return jsonify({
        'message': '测试成功！服务正常运行。',
        'app_id': FEISHU_APP_ID,
        'has_secret': bool(FEISHU_APP_SECRET)
    })

if __name__ == '__main__':
    import time
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 启动飞书开放平台机器人服务...")
    logger.info(f"🌐 服务地址: http://0.0.0.0:{port}")
    logger.info(f"🔧 调试模式: {app.debug}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
