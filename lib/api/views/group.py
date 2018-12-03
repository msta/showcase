from archii.api.exceptions import APIError
from archii.api.schemas.group import GroupSchema
from archii.api.views.base import BaseView
from archii.database import UniqueKeyError


class View(BaseView):
    def __init__(self, controllers=None, services=None):
        self.controllers = controllers
        self.services = services

    def create_group(self, schema: GroupSchema):
        try:
            return GroupSchema().dump_data(
                self.controllers.create_group(
                    schema.name, schema.categories, schema.users
                )
            )
        except UniqueKeyError:
            raise APIError('Duplicated group name', status_code=403)

    def get_company_groups(self, compact):
        res = self.controllers.get_company_groups(compact)
        return GroupSchema(many=True).dump_data(res)

    def update_group(self, group_id, group_name, users, categories):
        return GroupSchema().dump_data(
            self.controllers.update_group(
                group_id, group_name, users, categories)
        )
