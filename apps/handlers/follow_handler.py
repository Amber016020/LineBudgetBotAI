from linebot.v3.webhooks import FollowEvent
from linebot.v3.messaging import MessagingApi, ApiClient, Configuration
import apps.common.database as db
import os

configuration = Configuration(access_token=os.getenv("CHANNEL_ACCESS_TOKEN"))

# Handler function for when a user adds the LINE bot as a friend (FollowEvent)
def handle_follow(event: FollowEvent):
    user_id = event.source.user_id

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        profile = line_bot_api.get_profile(user_id)
        db.ensure_user_exists(user_id, profile.display_name)
