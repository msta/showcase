from archii.api.controllers.user import OldPasswordWrong
from archii.api.exceptions import APIError
from archii.api.schemas.login import LoginSchema
from archii.api.schemas.user import (UserAndQuestionnaireSchema,
                                     ChangePasswordSchema,
                                     UserSchema,
                                     ActivateUserSchema,
                                     InviteInfoSchema)
from archii.services.user import KeyExpired
from archii.database import ResourceNotFound


class View:
    def __init__(self, controllers=None):
        self.controllers = controllers

    def login_view(self, username, password, track_login=True):

        user_state = self.controllers.login(username, password,
                                            track_login=track_login)

        return LoginSchema().dump_data(
            user_state
        )

    def activate_user(self,
                      schema: ActivateUserSchema):
        try:
            retval = self.controllers.activate_user(schema.invite_key,
                                                    schema.password, schema.name,
                                                    schema.position,
                                                    schema.daily_tasks,
                                                    schema.other_daily_task)
            return LoginSchema().dump_data(
                retval
            )
        except (KeyExpired, ResourceNotFound):
            raise APIError('Key has expired', status_code=403)

    def change_password_view(self, schema: ChangePasswordSchema):
        try:
            user = self.controllers.change_password(
                schema.old_password,
                schema.new_password
            )
        except OldPasswordWrong:
            raise APIError('Wrong old password', status_code=403)
        return UserSchema().dump_data(user)

    def get_user(self):
        user = self.controllers.get_current_user()
        return UserAndQuestionnaireSchema().dump_data(
            user
        )

    def update_user(self, schema: UserAndQuestionnaireSchema):

        user = self.controllers.update_user(
            schema.name,
            schema.position,
            schema.daily_tasks,
            schema.other_daily_task)

        return UserAndQuestionnaireSchema().dump_data(
            user
        )

    def invite_info(self, invite_key):
        try:
            return InviteInfoSchema().dump_data(
                self.controllers.invite_info(invite_key)
            )
        except (KeyExpired, ResourceNotFound):
            raise APIError('Key has expired', status_code=403)
