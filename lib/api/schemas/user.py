from marshmallow import fields

class UserSchema(PonyAdapterSchema):
    user_id = fields.Integer()
    username = fields.String()
    name = fields.String()
    email = fields.String()

    def convert(self, dto, original):
        dto.user_id = original.id
        return dto


class QuestionnaireSchema(SomeCompanySchema):
    position = fields.String()
    daily_tasks = fields.List(fields.String())
    other_daily_task = fields.String()


class ActivateUserSchema(UserSchema, QuestionnaireSchema):
    invite_key = fields.String(required=True)
    password = fields.String(required=True)


class UserStatusSchema(UserSchema):
    status = fields.String()
    is_active = fields.Boolean()
    is_admin = fields.Boolean()

    def convert(self, dto, original):
        dto.status = original.status.value
        dto.is_active = original.active
        dto.is_admin = original.is_admin
        return super().convert(
            dto, original
        )


class UserAndQuestionnaireSchema(QuestionnaireSchema,
                                 UserStatusSchema):
    def convert(self, dto, original):
        questionnaire = original.questionnaire_json
        for key, value in questionnaire.items():
            setattr(dto, key, value)
        return super().convert(dto, original)


class ChangePasswordSchema(SomeCompanySchema):
    old_password = fields.String(required=True)
    new_password = fields.String(required=True)


class AccessUserSchema(PonyAdapterSchema):
    access_groups = fields.List(fields.Integer(), required=True)
    roles = fields.List(fields.Integer(), required=True)

    def convert(self, dto, original_user):
        dto.access_groups = [
            group.id for group in dto.access_groups
        ]
        dto.roles = [
            role.id for role in dto.roles
        ]
        return super().convert(dto, original_user)


class AdminUserListSchema(AccessUserSchema, UserStatusSchema):
    last_logged_in = fields.DateTime()
    date_invited = fields.DateTime()

    def convert(self, dto, original_user):
        if original_user.invite_key:
            dto.date_invited = original_user.invite_key.created
        dto.is_active = original_user.active
        dto.is_admin = original_user.is_admin
        return super().convert(dto, original_user)


class InviteUserSchema(SomeCompanySchema):
    user_emails = fields.List(fields.String(), required=True)
    message = fields.String(missing="")
    roles = fields.List(fields.Integer(), required=True)
    access_groups = fields.List(fields.Integer(), required=True)


class InviteInfoSchema(PonyAdapterSchema):
    email = fields.String(required=True)
    first_user = fields.Boolean(required=True)
    is_gdpr = fields.Boolean(required=True)

    def convert(self, dto, info):
        dto.email = info.user.email
        dto.first_user = info.user.company is None
        dto.is_gdpr = info.user.is_gdpr
        return dto
