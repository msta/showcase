from archii.api.schemas.notification import NotificationSchema
from .utils import success_response


class View:

    def __init__(self, controllers=None):
        self.controllers = controllers

    def get_all_categories_view(self, compact=False):
        all_categories = self.controllers.all_categories(compact)

        def category_repr(category):
            return {
                "id": category.index,
                "name": category.name,
                "parent": (category.parent_category.index
                           if category.parent_category
                           else category.index),
                "depth": category.depth
            }

        return success_response([
            category_repr(category) for category in all_categories
        ])

    def set_user_notification_id_view(self, notification_id):
        self.controllers.set_user_notification_id(notification_id)
        return success_response("ok")

    def get_notifications(self):
        rv = NotificationSchema(many=True).dump_data(
            self.controllers.get_notifications()
        )
        return rv

    def update_notification(self):
        self.controllers.update_notification()
        return success_response("ok")
