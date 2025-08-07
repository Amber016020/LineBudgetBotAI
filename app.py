from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
import os

# Import event handlers
from apps.handlers.follow_handler import handle_follow
from apps.handlers.message_handler import handle_message
from apps.handlers.postback_handler import handle_postback

from linebot.v3.messaging import Configuration
from linebot.v3.webhooks import (
    MessageEvent,
    FollowEvent,
    PostbackEvent,
    TextMessageContent,
)

# Initialize LINE bot configuration
configuration = Configuration(access_token=os.getenv("CHANNEL_ACCESS_TOKEN"))
line_handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))

# Initialize Flask app
app = Flask(__name__)

# === Webhook Endpoint ===
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    except Exception as e:
        app.logger.error(f"Webhook error: {e}")
        abort(400)

    return 'OK'

# === Register Event Handlers ===
line_handler.add(FollowEvent)(handle_follow)
line_handler.add(PostbackEvent)(handle_postback)
line_handler.add(MessageEvent, message=TextMessageContent)(handle_message)

# === Local Dev Entry Point ===
if __name__ == "__main__":
    app.run()